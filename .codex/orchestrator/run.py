#!/usr/bin/env python3
"""Run the Ollama implementation / review loop from a Codex-authored plan.

The runner deliberately keeps all subprocesses in argv form (never a shell
string).  It only performs read-only Git queries itself; model prompts carry
the project rule that models must not commit, publish, deploy, or delete data.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


DEFAULT_MAX_ROUNDS = 5
DEFAULT_MODEL_RETRIES = 2
DEFAULT_TIMEOUT_SECONDS = 1_200
REQUIRED_PLAN_FIELDS = {"request", "scope", "acceptance_criteria", "validation_commands"}
REVIEW_FIELDS = {
    "severity",
    "file",
    "line",
    "title",
    "evidence",
    "impact",
    "reproduction",
    "suggested_fix",
    "tests",
}
SEVERITIES = {"P0", "P1", "P2", "P3"}
FORBIDDEN_GIT_ACTIONS = {
    "add",
    "clean",
    "checkout",
    "commit",
    "push",
    "reset",
    "restore",
}
FORBIDDEN_PROGRAMS = {"del", "rm", "rmdir", "unlink"}


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class ValidationResult:
    name: str
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class RunResult:
    status: str
    reason: str
    rounds: int
    baseline_sha: str | None
    run_dir: str | None


class RunnerError(RuntimeError):
    """A safe, user-actionable runner failure."""


class DirtyWorktreeError(RunnerError):
    pass


class ModelError(RunnerError):
    pass


class ReviewError(RunnerError):
    pass


ProcessRunner = Callable[[Sequence[str], Path, int], CommandResult]


def run_process(argv: Sequence[str], cwd: Path, timeout: int) -> CommandResult:
    """Execute one argv command without a shell and normalize OS failures."""

    try:
        completed = subprocess.run(
            list(argv),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or f"command timed out after {timeout} seconds"
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        return CommandResult(124, stdout, stderr)
    except OSError as exc:
        return CommandResult(127, "", str(exc))
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _safe_argv(argv: Sequence[str]) -> list[str]:
    values = [str(value) for value in argv]
    if not values or not values[0].strip():
        raise RunnerError("validation command must contain a non-empty argv")
    program = Path(values[0].strip()).name.strip().lower()
    normalized = [value.strip().lower() for value in values]
    if program == "git" and any(token in FORBIDDEN_GIT_ACTIONS for token in normalized[1:]):
        raise RunnerError("forbidden Git write operation in validation command")
    if program in FORBIDDEN_PROGRAMS:
        raise RunnerError(f"forbidden deletion command in validation: {program}")
    if any(token in {"publish", "deploy"} for token in normalized[1:]):
        raise RunnerError("publish/deploy commands are not allowed in validation")
    return values


def load_validation_allowlist(path: Path) -> dict[str, list[str]]:
    """Load exact executable validation argv values from trusted repo config."""

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise RunnerError(f"invalid validation allowlist {path}: {exc}") from exc
    commands = data.get("commands")
    if not isinstance(commands, dict) or not commands:
        raise RunnerError("validation allowlist must define a non-empty [commands] table")
    allowlist: dict[str, list[str]] = {}
    for name, specification in commands.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(specification, dict):
            raise RunnerError("validation allowlist entries must be named tables")
        argv = specification.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) and arg.strip() for arg in argv):
            raise RunnerError(f"validation allowlist command {name!r} must have a non-empty string argv")
        allowlist[name] = _safe_argv(argv)
    validation = data.get("validation", {})
    if not isinstance(validation, dict):
        raise RunnerError("validation allowlist [validation] entry must be a table")
    required = validation.get("required", [])
    if not isinstance(required, list) or not all(isinstance(name, str) for name in required):
        raise RunnerError("validation.required must be a string array")
    missing = set(required) - allowlist.keys()
    if missing:
        raise RunnerError("validation.required has no allowlist command: " + ", ".join(sorted(missing)))
    return allowlist


def parse_plan(raw: str, allowed_commands: dict[str, list[str]]) -> dict[str, Any]:
    """Validate a Codex plan against exact command argv values from repo config."""

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RunnerError(f"plan is not valid JSON: {exc}") from exc
    if not isinstance(plan, dict) or set(plan) != REQUIRED_PLAN_FIELDS:
        raise RunnerError("plan must contain exactly request, scope, acceptance_criteria, and validation_commands")
    if not isinstance(plan["request"], str) or not plan["request"].strip():
        raise RunnerError("plan.request must be a non-empty string")
    for field in ("scope", "acceptance_criteria"):
        values = plan[field]
        if not isinstance(values, list) or not values or not all(isinstance(item, str) and item.strip() for item in values):
            raise RunnerError(f"plan.{field} must be a non-empty string array")
    commands = plan["validation_commands"]
    if not isinstance(commands, dict) or not commands:
        raise RunnerError("plan.validation_commands must be a non-empty object")
    validated: dict[str, list[str]] = {}
    for name, argv in commands.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(argv, list) or not all(
            isinstance(value, str) and value.strip() for value in argv
        ):
            raise RunnerError("each validation command must map a name to a non-empty argv array")
        allowed_argv = allowed_commands.get(name)
        if allowed_argv is None or argv != allowed_argv:
            raise RunnerError(f"validation command is not allowlisted exactly: {name}")
        validated[name] = list(allowed_argv)
    plan["validation_commands"] = validated
    return plan


def parse_review_json(raw: str) -> dict[str, Any]:
    """Validate Gemma's review JSON, optionally wrapped in one complete JSON fence."""

    normalized = raw.strip()
    if normalized.startswith("```") or normalized.endswith("```"):
        match = re.fullmatch(r"```json[ \t]*\r?\n(.*?)\r?\n```", normalized, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            raise ReviewError("review output must be bare JSON or one complete ```json fenced block")
        normalized = match.group(1).strip()

    try:
        value = json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise ReviewError(f"review output is not valid JSON: {exc}") from exc
    if not isinstance(value, dict) or set(value) != {"status", "findings", "unverified"}:
        raise ReviewError("review JSON must contain exactly status, findings, and unverified")
    if value["status"] not in {"pass", "needs_fix"}:
        raise ReviewError("review status must be pass or needs_fix")
    findings = value["findings"]
    if not isinstance(findings, list):
        raise ReviewError("review findings must be an array")
    for finding in findings:
        if not isinstance(finding, dict) or set(finding) != REVIEW_FIELDS:
            raise ReviewError("each finding must contain exactly the contract fields")
        if finding["severity"] not in SEVERITIES:
            raise ReviewError("finding severity must be P0, P1, P2, or P3")
        if not isinstance(finding["line"], int) or isinstance(finding["line"], bool) or finding["line"] < 1:
            raise ReviewError("finding line must be a positive integer")
        for field in REVIEW_FIELDS - {"line"}:
            if not isinstance(finding[field], str):
                raise ReviewError(f"finding field must be a string: {field}")
    has_blocking = any(finding["severity"] in {"P0", "P1"} for finding in findings)
    if (value["status"] == "needs_fix") != has_blocking:
        raise ReviewError("review status must be needs_fix exactly when P0/P1 findings are present")
    if not isinstance(value["unverified"], list) or not all(
        isinstance(item, str) for item in value["unverified"]
    ):
        raise ReviewError("review unverified must be a string array")
    return value


class Orchestrator:
    def __init__(
        self,
        repo_root: Path,
        *,
        validation_path: Path | None = None,
        runs_path: Path | None = None,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
        model_retries: int = DEFAULT_MODEL_RETRIES,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        process_runner: ProcessRunner = run_process,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.validation_path = validation_path or Path(".codex/validation.toml")
        if not self.validation_path.is_absolute():
            self.validation_path = self.repo_root / self.validation_path
        self.runs_path = runs_path or (self.repo_root / ".codex/runs")
        if not self.runs_path.is_absolute():
            self.runs_path = self.repo_root / self.runs_path
        if not 1 <= max_rounds <= DEFAULT_MAX_ROUNDS:
            raise ValueError(f"max_rounds must be between 1 and {DEFAULT_MAX_ROUNDS}")
        if not 0 <= model_retries <= DEFAULT_MODEL_RETRIES:
            raise ValueError(f"model_retries must be between 0 and {DEFAULT_MODEL_RETRIES}")
        self.max_rounds = max_rounds
        self.model_retries = model_retries
        self.timeout_seconds = timeout_seconds
        self.process_runner = process_runner

    def _git(self, *args: str) -> CommandResult:
        return self.process_runner(["git", *args], self.repo_root, self.timeout_seconds)

    def _baseline(self) -> str:
        status = self._git("status", "--porcelain=v1")
        if status.returncode != 0:
            raise RunnerError(f"unable to inspect Git worktree: {status.stderr.strip()}")
        if status.stdout.strip():
            raise DirtyWorktreeError("working tree is not clean; stop before starting and preserve existing changes")
        sha = self._git("rev-parse", "HEAD")
        if sha.returncode != 0 or not sha.stdout.strip():
            raise RunnerError(f"unable to determine baseline SHA: {sha.stderr.strip()}")
        return sha.stdout.strip()

    def _new_run_dir(self) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = self.runs_path / f"{timestamp}-{uuid.uuid4().hex[:8]}"
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir

    @staticmethod
    def _write(path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _model_argv(self, role: str, prompt: str) -> list[str]:
        if role == "implementer":
            return [
                "codex",
                "--model",
                "gpt-6-luna",
                "exec",
                "--ephemeral",
                "--sandbox",
                "workspace-write",
                prompt,
            ]
        if role == "reviewer":
            return [
                "codex",
                "--profile",
                "ollama-launch",
                "--model",
                "gemma4:31b-cloud",
                "exec",
                "--ephemeral",
                "--sandbox",
                "read-only",
                prompt,
            ]
        raise ValueError(f"unknown model role: {role}")

    def _invoke_model(self, role: str, prompt: str, artifact_dir: Path) -> str:
        last_error = ""
        for attempt in range(1, self.model_retries + 2):
            argv = self._model_argv(role, prompt)
            result = self.process_runner(argv, self.repo_root, self.timeout_seconds)
            self._write(artifact_dir / f"{role}-attempt-{attempt}.stdout.txt", result.stdout)
            self._write(artifact_dir / f"{role}-attempt-{attempt}.stderr.txt", result.stderr)
            if result.returncode == 0:
                if role == "reviewer":
                    try:
                        parse_review_json(result.stdout.strip())
                    except ReviewError as exc:
                        last_error = str(exc)
                        continue
                return result.stdout
            last_error = result.stderr.strip() or f"exit code {result.returncode}"
        raise ModelError(f"{role} failed after {self.model_retries} retries: {last_error}")

    def _validation(self, commands: dict[str, list[str]]) -> list[ValidationResult]:
        results = []
        for name, argv in commands.items():
            result = self.process_runner(argv, self.repo_root, self.timeout_seconds)
            results.append(ValidationResult(name, argv, result.returncode, result.stdout, result.stderr))
        return results

    @staticmethod
    def _validation_ok(results: list[ValidationResult]) -> bool:
        return bool(results) and all(result.returncode == 0 for result in results)

    def _implementer_prompt(
        self,
        plan: dict[str, Any],
        baseline_sha: str,
        *,
        correction: str | None = None,
    ) -> str:
        extra = f"\n修正背景：\n{correction}\n" if correction else ""
        return f"""請先閱讀 `.codex/agents/implementer.toml` 並遵循其 developer_instructions。你是本次工作的 implementer，請依 Codex 計畫在目前 repository 完成需求：

{json.dumps(plan, ensure_ascii=False, indent=2)}

基準 SHA：{baseline_sha}。請只修改與需求相關的檔案，保留任何既有使用者變更。
完成後請自行檢查實作。禁止執行 git add、commit、push、發布、部署或刪除資料；不要修改基準之外的無關內容。
{extra}"""

    def _reviewer_prompt(self, plan: dict[str, Any], baseline_sha: str) -> str:
        return f"""請先閱讀 `.codex/agents/reviewer.toml` 並遵循其 developer_instructions。你是唯讀 reviewer。審查本次 Codex 計畫在基準 SHA {baseline_sha} 之後的變更：
{json.dumps(plan, ensure_ascii=False, indent=2)}
變更範圍嚴格限定為基準 SHA 到目前工作樹：執行並檢查 `git diff --no-ext-diff {baseline_sha} --`，並執行 `git ls-files --others --exclude-standard` 找出基準後新增的未追蹤檔案，再只讀取那些未追蹤檔案。不要檢查或修改範圍外的檔案。
你必須只回傳一個嚴格 JSON 物件，不要 Markdown code fence 或其他文字，格式如下：
{{"status":"pass|needs_fix","findings":[{{"severity":"P0|P1|P2|P3","file":"path","line":1,"title":"問題標題","evidence":"證據","impact":"影響","reproduction":"重現方式","suggested_fix":"建議修正","tests":"相關測試"}}],"unverified":[]}}
只有確實需要修改的 P0/P1 才應使用 needs_fix；P2/P3 要保留在 findings 但不阻擋通過。禁止任何檔案修改、Git 寫入、發布、部署或刪除操作。"""

    def _capture_round_diff(self, baseline_sha: str, round_dir: Path) -> str | None:
        tracked = self._git("diff", "--no-ext-diff", "--binary", baseline_sha, "--")
        untracked = self._git("ls-files", "--others", "--exclude-standard")
        errors = []
        if tracked.returncode != 0:
            errors.append(f"git diff exited {tracked.returncode}: {tracked.stderr.strip()}")
        if untracked.returncode != 0:
            errors.append(f"git ls-files exited {untracked.returncode}: {untracked.stderr.strip()}")
        chunks = [tracked.stdout]
        if untracked.returncode == 0:
            for relative_path in untracked.stdout.splitlines():
                result = self._git("diff", "--no-index", "--binary", "--", "/dev/null", relative_path)
                if result.returncode in (0, 1):
                    chunks.append(result.stdout)
                else:
                    errors.append(
                        f"git diff --no-index failed for {relative_path!r} "
                        f"with exit {result.returncode}: {result.stderr.strip()}"
                    )
        if errors:
            message = "; ".join(errors)
            self._write(round_dir / "diff-error.txt", message + "\n")
            return message
        self._write(round_dir / "diff.patch", "\n".join(chunk for chunk in chunks if chunk))
        return None

    def _diff_failure_result(
        self,
        message: str,
        run_dir: Path,
        round_number: int,
        baseline_sha: str,
    ) -> RunResult:
        reason = f"unable to capture round diff: {message}"
        self._write_json(
            run_dir / "summary.json",
            {"status": "stopped", "reason": reason, "rounds": round_number},
        )
        return RunResult("stopped", reason, round_number, baseline_sha, str(run_dir))

    def run(self, plan_input: str | dict[str, Any]) -> RunResult:
        try:
            baseline_sha = self._baseline()
        except RunnerError as exc:
            return RunResult("stopped", str(exc), 0, None, None)

        try:
            allowlist = load_validation_allowlist(self.validation_path)
            plan_raw = plan_input if isinstance(plan_input, str) else json.dumps(plan_input, ensure_ascii=False)
            plan = parse_plan(plan_raw, allowlist)
        except RunnerError as exc:
            return RunResult("stopped", str(exc), 0, baseline_sha, None)

        try:
            run_dir = self._new_run_dir()
        except (OSError, RunnerError) as exc:
            return RunResult("stopped", str(exc), 0, baseline_sha, None)
        self._write_json(run_dir / "plan.json", plan)
        self._write_json(run_dir / "metadata.json", {"baseline_sha": baseline_sha, "plan": "plan.json"})
        commands = plan["validation_commands"]

        correction: str | None = None
        for round_number in range(1, self.max_rounds + 1):
            round_dir = run_dir / f"round-{round_number:02d}"
            round_dir.mkdir()
            implementer_prompt = self._implementer_prompt(
                plan, baseline_sha, correction=correction
            )
            self._write(round_dir / "implementer-prompt.txt", implementer_prompt)
            try:
                implementer_output = self._invoke_model("implementer", implementer_prompt, round_dir)
            except ModelError as exc:
                diff_error = self._capture_round_diff(baseline_sha, round_dir)
                if diff_error:
                    reason = f"{exc}; unable to capture diff: {diff_error}"
                    self._write_json(run_dir / "summary.json", {"status": "stopped", "reason": reason, "rounds": round_number})
                    return RunResult("stopped", reason, round_number, baseline_sha, str(run_dir))
                self._write_json(run_dir / "summary.json", {"status": "stopped", "reason": str(exc), "rounds": round_number})
                return RunResult("stopped", str(exc), round_number, baseline_sha, str(run_dir))
            self._write(round_dir / "implementer-output.txt", implementer_output)

            validation_results = self._validation(commands)
            self._write_json(round_dir / "validation.json", [asdict(result) for result in validation_results])
            diff_error = self._capture_round_diff(baseline_sha, round_dir)
            if diff_error:
                return self._diff_failure_result(diff_error, run_dir, round_number, baseline_sha)
            if not self._validation_ok(validation_results):
                self._write_json(
                    round_dir / "findings.json",
                    {"status": "needs_fix", "findings": [], "unverified": ["validation failed"]},
                )
                correction = "Validation 失敗：\n" + json.dumps(
                    [asdict(result) for result in validation_results], ensure_ascii=False, indent=2
                )
                if round_number == self.max_rounds:
                    reason = "validation failed after maximum rounds"
                    self._write_json(run_dir / "summary.json", {"status": "max_rounds", "reason": reason, "rounds": round_number})
                    return RunResult("max_rounds", reason, round_number, baseline_sha, str(run_dir))
                continue

            reviewer_prompt = self._reviewer_prompt(plan, baseline_sha)
            self._write(round_dir / "reviewer-prompt.txt", reviewer_prompt)
            try:
                reviewer_output = self._invoke_model("reviewer", reviewer_prompt, round_dir)
                review = parse_review_json(reviewer_output.strip())
            except (ModelError, ReviewError) as exc:
                self._write_json(run_dir / "summary.json", {"status": "stopped", "reason": str(exc), "rounds": round_number})
                return RunResult("stopped", str(exc), round_number, baseline_sha, str(run_dir))
            self._write(round_dir / "reviewer-output.txt", reviewer_output)
            self._write_json(round_dir / "findings.json", review)

            blocking = [finding for finding in review["findings"] if finding["severity"] in {"P0", "P1"}]
            if blocking:
                correction = "Gemma P0/P1 findings：\n" + json.dumps(blocking, ensure_ascii=False, indent=2)
                if round_number == self.max_rounds:
                    reason = "P0/P1 findings remain after maximum rounds"
                    self._write_json(run_dir / "summary.json", {"status": "max_rounds", "reason": reason, "rounds": round_number})
                    return RunResult("max_rounds", reason, round_number, baseline_sha, str(run_dir))
                continue

            reason = "validation passed and no P0/P1 findings"
            self._write_json(run_dir / "summary.json", {"status": "passed", "reason": reason, "rounds": round_number})
            return RunResult("passed", reason, round_number, baseline_sha, str(run_dir))

        reason = "maximum rounds exhausted"
        return RunResult("max_rounds", reason, self.max_rounds, baseline_sha, str(run_dir))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument("--plan", type=Path, required=True, help="Codex 計畫 JSON 檔案，需放在 repository 外")
    parser.add_argument("--runs", type=Path, default=None, help="artifact directory")
    parser.add_argument("--max-rounds", type=int, default=DEFAULT_MAX_ROUNDS)
    parser.add_argument("--model-retries", type=int, default=DEFAULT_MODEL_RETRIES)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 1 <= args.max_rounds <= DEFAULT_MAX_ROUNDS or not 0 <= args.model_retries <= DEFAULT_MODEL_RETRIES:
        print(
            f"--max-rounds must be 1..{DEFAULT_MAX_ROUNDS} and "
            f"--model-retries must be 0..{DEFAULT_MODEL_RETRIES}",
            file=sys.stderr,
        )
        return 2
    runner = Orchestrator(
        args.repo,
        runs_path=args.runs,
        max_rounds=args.max_rounds,
        model_retries=args.model_retries,
    )
    try:
        repo_root = args.repo.resolve()
        plan_path = args.plan.resolve()
        if plan_path == repo_root or repo_root in plan_path.parents:
            raise RunnerError("plan JSON must be stored outside the repository")
        plan = plan_path.read_text(encoding="utf-8")
    except (OSError, RunnerError) as exc:
        print(json.dumps({"status": "stopped", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    result = runner.run(plan)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
