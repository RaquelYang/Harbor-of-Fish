import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from run import (
    CommandResult,
    Orchestrator,
    ReviewError,
    RunnerError,
    _safe_argv,
    parse_review_json,
    run_process,
)


def review(status="pass", findings=None):
    return json.dumps(
        {"status": status, "findings": findings or [], "unverified": []}, ensure_ascii=False
    )


def p1_finding():
    return {
        "severity": "P1",
        "file": "README.md",
        "line": 1,
        "title": "blocking regression",
        "evidence": "test evidence",
        "impact": "users are affected",
        "reproduction": "run the test",
        "suggested_fix": "fix the implementation",
        "tests": "add a regression test",
    }


def p2_finding():
    finding = p1_finding()
    finding["severity"] = "P2"
    return finding


class FakeProcesses:
    def __init__(self, model_responses, validation_codes=None):
        self.model_responses = list(model_responses)
        self.validation_codes = list(validation_codes or [])
        self.model_calls = []

    def __call__(self, argv, cwd, timeout):
        if argv and argv[0] == "git":
            return run_process(argv, cwd, timeout)
        if argv and argv[0] == "codex":
            role = "reviewer" if "gemma4:31b-cloud" in argv else "implementer"
            self.model_calls.append((role, list(argv)))
            if not self.model_responses:
                return CommandResult(1, "", "fake response queue exhausted")
            response = self.model_responses.pop(0)
            if isinstance(response, CommandResult):
                return response
            return CommandResult(0, response, "")
        # Validation commands are represented by no-op fake commands. The
        # runner still records their argv and exit code.
        code = self.validation_codes.pop(0) if self.validation_codes else 0
        return CommandResult(code, "ok" if code == 0 else "failed", "" if code == 0 else "validation error")


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / ".codex" / "runs").mkdir(parents=True)
        (self.root / ".gitignore").write_text(".codex/runs/\n", encoding="utf-8")
        (self.root / "README.md").write_text("baseline\n", encoding="utf-8")
        self._git("init", "-q")
        self._git("config", "user.email", "runner@example.invalid")
        self._git("config", "user.name", "Runner Test")
        self._git("add", ".")
        self._git("commit", "-qm", "baseline")
        self.validation = self.root / "validation.toml"
        self.validation.write_text(
            """[validation]
required = ["test", "lint", "build"]
[commands.test]
argv = ["fake-test"]
[commands.lint]
argv = ["fake-lint"]
[commands.build]
argv = ["fake-build"]
""",
            encoding="utf-8",
        )
        self._git("add", "validation.toml")
        self._git("commit", "-qm", "validation")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True)

    def _runner(self, fake):
        return Orchestrator(
            self.root,
            validation_path=self.validation,
            max_rounds=5,
            model_retries=2,
            process_runner=fake,
        )

    def test_success_and_p2_p3_findings_do_not_trigger_fix(self):
        fake = FakeProcesses(["implemented", review("needs_fix", [p2_finding()])])
        result = self._runner(fake).run("implement a feature")
        self.assertEqual(result.status, "passed")
        self.assertEqual(result.rounds, 1)
        self.assertEqual([role for role, _ in fake.model_calls], ["implementer", "reviewer"])
        findings = json.loads((Path(result.run_dir) / "round-01" / "findings.json").read_text())
        self.assertEqual(findings["findings"][0]["severity"], "P2")

    def test_p0_p1_findings_trigger_luna_fix(self):
        fake = FakeProcesses(["first", review("needs_fix", [p1_finding()]), "fixed", review()])
        result = self._runner(fake).run("implement a feature")
        self.assertEqual(result.status, "passed")
        self.assertEqual(result.rounds, 2)
        second_prompt = fake.model_calls[2][1][-1]
        self.assertIn("Gemma P0/P1 findings", second_prompt)

    def test_validation_failure_triggers_luna_fix(self):
        fake = FakeProcesses(
            ["first", "fixed", review()], validation_codes=[1, 0, 0, 0, 0, 0]
        )
        result = self._runner(fake).run("fix failing validation")
        self.assertEqual(result.status, "passed")
        self.assertEqual(result.rounds, 2)
        self.assertEqual([role for role, _ in fake.model_calls], ["implementer", "implementer", "reviewer"])
        self.assertIn("Validation 失敗", fake.model_calls[1][1][-1])

    def test_five_round_limit_stops_after_repeated_p1(self):
        responses = []
        for _ in range(5):
            responses.extend(["implementation", review("needs_fix", [p1_finding()])])
        fake = FakeProcesses(responses)
        result = self._runner(fake).run("never finish")
        self.assertEqual(result.status, "max_rounds")
        self.assertEqual(result.rounds, 5)
        self.assertEqual(len(fake.model_calls), 10)

    def test_dirty_worktree_stops_before_model(self):
        (self.root / "uncommitted.txt").write_text("dirty\n", encoding="utf-8")
        fake = FakeProcesses([])
        result = self._runner(fake).run("do not start")
        self.assertEqual(result.status, "stopped")
        self.assertIn("not clean", result.reason)
        self.assertEqual(fake.model_calls, [])
        self.assertIsNone(result.run_dir)

    def test_model_cli_failure_retries_twice_then_stops(self):
        fake = FakeProcesses([CommandResult(1, "", "unavailable")] * 3)
        result = self._runner(fake).run("model unavailable")
        self.assertEqual(result.status, "stopped")
        self.assertEqual(len(fake.model_calls), 3)
        self.assertIn("after 2 retries", result.reason)

    def test_invalid_gemma_json_retries_twice_then_stops(self):
        fake = FakeProcesses(["implemented", "not json", "still not json", "also not json"])
        result = self._runner(fake).run("invalid review")
        self.assertEqual(result.status, "stopped")
        self.assertEqual([role for role, _ in fake.model_calls], ["implementer", "reviewer", "reviewer", "reviewer"])
        self.assertIn("valid JSON", result.reason)

    def test_missing_required_validation_never_auto_completes(self):
        missing = self.root / "missing-validation.toml"
        fake = FakeProcesses([])
        result = Orchestrator(self.root, validation_path=missing, process_runner=fake).run("no validation")
        self.assertEqual(result.status, "stopped")
        self.assertEqual(fake.model_calls, [])

    def test_forbidden_validation_operation_is_rejected(self):
        forbidden = self.root / ".codex" / "runs" / "forbidden.toml"
        forbidden.write_text(
            """[validation]
required = ["test", "lint", "build"]
[commands.test]
argv = ["git", "commit", "-am", "bad"]
[commands.lint]
argv = ["fake-lint"]
[commands.build]
argv = ["fake-build"]
""",
            encoding="utf-8",
        )
        fake = FakeProcesses([])
        result = Orchestrator(self.root, validation_path=forbidden, process_runner=fake).run("safe")
        self.assertEqual(result.status, "stopped")
        self.assertIn("forbidden Git", result.reason)
        self.assertEqual(fake.model_calls, [])

    def test_model_commands_explicitly_select_openai_and_ollama_read_only(self):
        fake = FakeProcesses([])
        runner = self._runner(fake)
        luna = runner._model_argv("implementer", "task")
        gemma = runner._model_argv("reviewer", "review")
        self.assertEqual(
            luna[:8],
            ["codex", "exec", "-c", 'model_provider="openai"', "--model", "gpt-6-luna", "--sandbox", "workspace-write"],
        )
        self.assertEqual(
            gemma[:10],
            ["codex", "--oss", "--local-provider", "ollama", "--model", "gemma4:31b-cloud", "exec", "--ephemeral", "--sandbox", "read-only"],
        )
        forbidden = {"add", "commit", "push", "publish", "deploy", "rm", "delete"}
        self.assertFalse(forbidden.intersection(" ".join(luna + gemma).split()))

    def test_constructor_cannot_raise_round_or_retry_limits(self):
        with self.assertRaises(ValueError):
            self._runner(FakeProcesses([])).__class__(self.root, max_rounds=6)
        with self.assertRaises(ValueError):
            self._runner(FakeProcesses([])).__class__(self.root, model_retries=3)

    def test_finding_with_extra_key_is_invalid_json_contract(self):
        finding = p1_finding()
        finding["extra"] = "not allowed"
        with self.assertRaises(ReviewError):
            parse_review_json(review("needs_fix", [finding]))

    def test_safe_argv_normalizes_direct_git_subcommands_without_path_false_positive(self):
        with self.assertRaises(RunnerError):
            _safe_argv(["git", "  commit  ", "-m", "no"])
        self.assertEqual(_safe_argv(["python3", "/tmp/git commit fixture.py"]), ["python3", "/tmp/git commit fixture.py"])
        self.assertEqual(_safe_argv(["/usr/bin/git", "status"]), ["/usr/bin/git", "status"])

    def test_reviewer_prompt_scopes_diff_and_untracked_files(self):
        prompt = self._runner(FakeProcesses([]))._reviewer_prompt("task", "abc123")
        self.assertIn("git diff --no-ext-diff abc123 --", prompt)
        self.assertIn("git ls-files --others --exclude-standard", prompt)


if __name__ == "__main__":
    unittest.main()
