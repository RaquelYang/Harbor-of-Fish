#!/usr/bin/env python3
"""Run the Luna implementation / Gemma review loop for this repository.

The runner deliberately keeps all subprocesses in argv form (never a shell
string).  It only performs read-only Git queries itself; model prompts carry
the project rule that models must not commit, publish, deploy, or delete data.
"""

from __future__ import annotations

import argparse
import json
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
REQUIRED_VALIDATIONS = ("test", "lint", "build")
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


def parse_validation_config(path: Path) -> dict[str, list[str]]:
    """Load required validation commands from TOML argv arrays."""

    if not path.is_file():
        raise RunnerError(f"validation configuration does not exist: {path}")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise RunnerError(f"invalid validation configuration: {exc}") from exc

    validation = data.get("validation", {})
    required = validation.get("required", list(REQUIRED_VALIDATIONS))
    if not isinstance(required, list) or not required or not all(isinstance(x, str) for x in required):
        raise RunnerError("validation.required must be a non-empty string array")
    missing = set(REQUIRED_VALIDATIONS) - set(required)
    if missing:
        raise RunnerError("validation.required is missing: " + ", ".join(sorted(missing)))
    command_table = data.get("commands", {})
    if not isinstance(command_table, dict):
        raise RunnerError("validation.commands must be a TOML table")

    result: dict[str, list[str]] = {}
    for name in required:
        specification: Any = command_table.get(name, data.get(name))
        if isinstance(specification, dict):
            specification = specification.get("argv")
        if not isinstance(specification, list) or not specification or not all(
            isinstance(value, str) and value.strip() for value in specification
        ):
            raise RunnerError(f"required validation command is not configured: {name}")
        result[name] = _safe_argv(specification)
    return result


def parse_review_json(raw: str) -> dict[str, Any]:
    """Validate Gemma's exact machine-readable review contract."""

    try:
        value = json.loads(raw)
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
        self.validation_path = (validation_path or Path(".codex/validation.toml"))
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
            raise DirtyWorktreeError("working tree is not clean; commit or stash changes before starting")
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
                "exec",
                "-c",
                'model_provider="openai"',
                "--model",
                "gpt-5.6-luna",
                "--sandbox",
                "workspace-write",
                prompt,
            ]
        if role == "reviewer":
            return [
                "codex",
                "--oss",
                "--local-provider",
                "ollama",
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
        task: str,
        baseline_sha: str,
        *,
        correction: str | None = None,
    ) -> str:
        extra = f"\n修正背景：\n{correction}\n" if correction else ""
        return f"""你是本次工作的 implementer。請在目前 repository 完成以下需求：

{task}

基準 SHA：{baseline_sha}。請只修改與需求相關的檔案，保留任何既有使用者變更。
完成後請自行檢查實作。禁止執行 git add、commit、push、發布、部署或刪除資料；不要修改基準之外的無關內容。
{extra}"""

    def _reviewer_prompt(self, task: str, baseline_sha: str) -> str:
        return f"""你是唯讀 reviewer。審查本次需求「{task}」在基準 SHA {baseline_sha} 之後的變更。
變更範圍嚴格限定為基準 SHA 到目前工作樹：執行並檢查 `git diff --no-ext-diff {baseline_sha} --`，並執行 `git ls-files --others --exclude-standard` 找出基準後新增的未追蹤檔案，再只讀取那些未追蹤檔案。不要檢查或修改範圍外的檔案。
你必須只回傳一個嚴格 JSON 物件，不要 Markdown code fence 或其他文字，格式如下：
{{"status":"pass|needs_fix","findings":[{{"severity":"P0|P1|P2|P3","file":"path","line":1,"title":"問題標題","evidence":"證據","impact":"影響","reproduction":"重現方式","suggested_fix":"建議修正","tests":"相關測試"}}],"unverified":[]}}
只有確實需要修改的 P0/P1 才應使用 needs_fix；P2/P3 要保留在 findings 但不阻擋通過。禁止任何檔案修改、Git 寫入、發布、部署或刪除操作。"""

    def run(self, task: str) -> RunResult:
        try:
            baseline_sha = self._baseline()
        except RunnerError as exc:
            return RunResult("stopped", str(exc), 0, None, None)

        try:
            run_dir = self._new_run_dir()
        except (OSError, RunnerError) as exc:
            return RunResult("stopped", str(exc), 0, baseline_sha, None)
        self._write_json(run_dir / "metadata.json", {"baseline_sha": baseline_sha, "task": task})
        try:
            commands = parse_validation_config(self.validation_path)
        except RunnerError as exc:
            self._write_json(run_dir / "summary.json", {"status": "stopped", "reason": str(exc), "rounds": 0})
            return RunResult("stopped", str(exc), 0, baseline_sha, str(run_dir))

        correction: str | None = None
        for round_number in range(1, self.max_rounds + 1):
            round_dir = run_dir / f"round-{round_number:02d}"
            round_dir.mkdir()
            implementer_prompt = self._implementer_prompt(
                task, baseline_sha, correction=correction
            )
            self._write(round_dir / "implementer-prompt.txt", implementer_prompt)
            try:
                implementer_output = self._invoke_model("implementer", implementer_prompt, round_dir)
            except ModelError as exc:
                self._write_json(run_dir / "summary.json", {"status": "stopped", "reason": str(exc), "rounds": round_number})
                return RunResult("stopped", str(exc), round_number, baseline_sha, str(run_dir))
            self._write(round_dir / "implementer-output.txt", implementer_output)

            validation_results = self._validation(commands)
            self._write_json(round_dir / "validation.json", [asdict(result) for result in validation_results])
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

            reviewer_prompt = self._reviewer_prompt(task, baseline_sha)
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
    parser.add_argument("--task", required=True, help="需求描述")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument("--validation", type=Path, default=Path(".codex/validation.toml"))
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
        validation_path=args.validation,
        runs_path=args.runs,
        max_rounds=args.max_rounds,
        model_retries=args.model_retries,
    )
    result = runner.run(args.task)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
