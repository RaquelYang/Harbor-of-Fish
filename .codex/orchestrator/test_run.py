import json
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

from run import (
    CommandResult,
    Orchestrator,
    ReviewError,
    RunnerError,
    _safe_argv,
    load_validation_allowlist,
    parse_plan,
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
    def __init__(self, model_responses, validation_codes=None, create_untracked=False, git_failures=None):
        self.model_responses = list(model_responses)
        self.validation_codes = list(validation_codes or [])
        self.model_calls = []
        self.create_untracked = create_untracked
        self.git_failures = git_failures or {}

    def __call__(self, argv, cwd, timeout):
        if argv and argv[0] == "git":
            if len(argv) > 1 and argv[1] in self.git_failures:
                return CommandResult(self.git_failures[argv[1]], "", f"synthetic {argv[1]} failure")
            return run_process(argv, cwd, timeout)
        if argv and argv[0] == "codex":
            role = "reviewer" if argv[argv.index("--sandbox") + 1] == "read-only" else "implementer"
            self.model_calls.append((role, list(argv)))
            if self.create_untracked and role == "implementer":
                (Path(cwd) / "created.txt").write_text("created by implementer\n", encoding="utf-8")
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
        project_root = Path(__file__).resolve().parents[2]
        subprocess.run(["git", "clone", "-q", str(project_root), str(self.root)], check=True)
        self.validation_allowlist = load_validation_allowlist(self.root / ".codex/validation.toml")
        self.plan = {
            "request": "implement a feature",
            "scope": ["README.md"],
            "acceptance_criteria": ["the change is correct"],
            "validation_commands": self.validation_allowlist,
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def _runner(self, fake):
        return Orchestrator(self.root, max_rounds=5, model_retries=2, process_runner=fake)

    def test_success_and_p2_p3_findings_do_not_trigger_fix(self):
        fake = FakeProcesses(["implemented", review("pass", [p2_finding()])])
        result = self._runner(fake).run(self.plan)
        self.assertEqual(result.status, "passed")
        self.assertEqual(result.rounds, 1)
        self.assertEqual([role for role, _ in fake.model_calls], ["implementer", "reviewer"])
        findings = json.loads((Path(result.run_dir) / "round-01" / "findings.json").read_text())
        self.assertEqual(findings["findings"][0]["severity"], "P2")

    def test_p0_p1_findings_trigger_luna_fix(self):
        fake = FakeProcesses(["first", review("needs_fix", [p1_finding()]), "fixed", review()])
        result = self._runner(fake).run(self.plan)
        self.assertEqual(result.status, "passed")
        self.assertEqual(result.rounds, 2)
        second_prompt = fake.model_calls[2][1][-1]
        self.assertIn("Gemma P0/P1 findings", second_prompt)

    def test_validation_failure_triggers_luna_fix(self):
        fake = FakeProcesses(
            ["first", "fixed", review()], validation_codes=[1, 0, 0, 0, 0, 0]
        )
        result = self._runner(fake).run(self.plan)
        self.assertEqual(result.status, "passed")
        self.assertEqual(result.rounds, 2)
        self.assertEqual([role for role, _ in fake.model_calls], ["implementer", "implementer", "reviewer"])
        self.assertIn("Validation 失敗", fake.model_calls[1][1][-1])

    def test_five_round_limit_stops_after_repeated_p1(self):
        responses = []
        for _ in range(5):
            responses.extend(["implementation", review("needs_fix", [p1_finding()])])
        fake = FakeProcesses(responses)
        result = self._runner(fake).run(self.plan)
        self.assertEqual(result.status, "max_rounds")
        self.assertEqual(result.rounds, 5)
        self.assertEqual(len(fake.model_calls), 10)

    def test_dirty_worktree_stops_before_model(self):
        (self.root / "uncommitted.txt").write_text("dirty\n", encoding="utf-8")
        fake = FakeProcesses([])
        result = self._runner(fake).run(self.plan)
        self.assertEqual(result.status, "stopped")
        self.assertIn("not clean", result.reason)
        self.assertEqual(fake.model_calls, [])
        self.assertIsNone(result.run_dir)

    def test_model_cli_failure_retries_twice_then_stops(self):
        fake = FakeProcesses([CommandResult(1, "", "unavailable")] * 3)
        result = self._runner(fake).run(self.plan)
        self.assertEqual(result.status, "stopped")
        self.assertEqual(len(fake.model_calls), 3)
        self.assertIn("after 2 retries", result.reason)

    def test_invalid_gemma_json_retries_twice_then_stops(self):
        fake = FakeProcesses(["implemented", "not json", "still not json", "also not json"])
        result = self._runner(fake).run(self.plan)
        self.assertEqual(result.status, "stopped")
        self.assertEqual([role for role, _ in fake.model_calls], ["implementer", "reviewer", "reviewer", "reviewer"])
        self.assertIn("valid JSON", result.reason)

    def test_single_json_fence_is_accepted_but_partial_or_extra_text_is_rejected(self):
        fenced = f"```json\n{review()}\n```"
        self.assertEqual(parse_review_json(fenced)["status"], "pass")
        for malformed in (
            f"before\n{fenced}",
            f"{fenced}\nafter",
            "```json\n{" + "\n```",
            f"```json\n{review()}\n```\n```json\n{review()}\n```",
            f"```text\n{review()}\n```",
        ):
            with self.subTest(malformed=malformed), self.assertRaises(ReviewError):
                parse_review_json(malformed)

    def test_validation_commands_must_match_trusted_allowlist_exactly(self):
        for argv in (
            ["bash", "-c", "git commit -am bad"],
            ["python3", "-c", "import pathlib; pathlib.Path('x').unlink()"],
            ["git", "commit", "-am", "bad"],
        ):
            unsafe = dict(self.plan)
            unsafe["validation_commands"] = {"test": argv}
            with self.assertRaisesRegex(RunnerError, "not allowlisted exactly"):
                parse_plan(json.dumps(unsafe), self.validation_allowlist)

    def test_plan_can_select_a_legal_subset_of_trusted_validations(self):
        subset = dict(self.plan)
        subset["validation_commands"] = {"test": self.validation_allowlist["test"]}
        parsed = parse_plan(json.dumps(subset), self.validation_allowlist)
        self.assertEqual(parsed["validation_commands"], subset["validation_commands"])

    def test_diff_capture_failures_stop_and_record_the_reason(self):
        for git_subcommand in ("diff", "ls-files"):
            with self.subTest(git_subcommand=git_subcommand):
                fake = FakeProcesses(["implemented"], git_failures={git_subcommand: 2})
                result = self._runner(fake).run(self.plan)
                self.assertEqual(result.status, "stopped")
                self.assertIn("unable to capture round diff", result.reason)
                self.assertEqual([role for role, _ in fake.model_calls], ["implementer"])
                round_dir = Path(result.run_dir) / "round-01"
                self.assertIn(git_subcommand, (round_dir / "diff-error.txt").read_text())
                self.assertEqual(json.loads((Path(result.run_dir) / "summary.json").read_text())["status"], "stopped")

    def test_model_commands_route_luna_implementer_and_ollama_reviewer_separately(self):
        fake = FakeProcesses([])
        runner = self._runner(fake)
        luna = runner._model_argv("implementer", "task")
        gemma = runner._model_argv("reviewer", "review")
        self.assertEqual(luna[:4], ["codex", "--model", "gpt-6-luna", "exec"])
        self.assertNotIn("--profile", luna)
        self.assertIn("--ephemeral", luna)
        self.assertEqual(luna[luna.index("--sandbox") + 1], "workspace-write")

        self.assertEqual(gemma[:6], ["codex", "--profile", "ollama-launch", "--model", "gemma4:31b-cloud", "exec"])
        self.assertIn("--ephemeral", gemma)
        self.assertEqual(gemma[gemma.index("--sandbox") + 1], "read-only")

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

    def test_review_status_must_match_blocking_findings(self):
        with self.assertRaises(ReviewError):
            parse_review_json(review("pass", [p1_finding()]))
        with self.assertRaises(ReviewError):
            parse_review_json(review("needs_fix", [p2_finding()]))

    def test_safe_argv_normalizes_direct_git_subcommands_without_path_false_positive(self):
        with self.assertRaises(RunnerError):
            _safe_argv(["git", "  commit  ", "-m", "no"])
        self.assertEqual(_safe_argv(["python3", "/tmp/git commit fixture.py"]), ["python3", "/tmp/git commit fixture.py"])
        self.assertEqual(_safe_argv(["/usr/bin/git", "status"]), ["/usr/bin/git", "status"])

    def test_reviewer_prompt_scopes_diff_and_untracked_files(self):
        prompt = self._runner(FakeProcesses([]))._reviewer_prompt(self.plan, "abc123")
        self.assertIn("git diff --no-ext-diff abc123 --", prompt)
        self.assertIn("git ls-files --others --exclude-standard", prompt)
        self.assertIn("P0|P1|P2|P3", prompt)

    def test_plan_schema_requires_scope_acceptance_and_named_validation_commands(self):
        parsed = parse_plan(json.dumps(self.plan), self.validation_allowlist)
        self.assertEqual(parsed["validation_commands"]["test"], self.validation_allowlist["test"])
        for field in ("scope", "acceptance_criteria", "validation_commands"):
            malformed = dict(self.plan)
            malformed[field] = []
            with self.assertRaises(RunnerError):
                parse_plan(json.dumps(malformed), self.validation_allowlist)

    def test_run_persists_plan_baseline_round_diff_validation_and_summary(self):
        fenced_review = f"```json\n{review()}\n```"
        fake = FakeProcesses(["implemented", fenced_review], create_untracked=True)
        result = self._runner(fake).run(self.plan)
        run_dir = Path(result.run_dir)
        self.assertEqual(json.loads((run_dir / "plan.json").read_text()), self.plan)
        metadata = json.loads((run_dir / "metadata.json").read_text())
        self.assertTrue(metadata["baseline_sha"])
        round_dir = run_dir / "round-01"
        self.assertTrue((round_dir / "diff.patch").is_file())
        self.assertIn("created.txt", (round_dir / "diff.patch").read_text())
        self.assertTrue((round_dir / "implementer-output.txt").is_file())
        self.assertEqual((round_dir / "reviewer-output.txt").read_text(), fenced_review)
        self.assertIn("acceptance_criteria", (round_dir / "reviewer-prompt.txt").read_text())
        self.assertEqual(len(json.loads((round_dir / "validation.json").read_text())), 3)
        self.assertEqual(json.loads((run_dir / "summary.json").read_text())["status"], "passed")

    def test_project_default_model_is_luna(self):
        config_path = Path(__file__).resolve().parents[1] / "config.toml"
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(config["model"], "gpt-6-luna")


if __name__ == "__main__":
    unittest.main()
