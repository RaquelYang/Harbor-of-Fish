---
name: "speckit-implement"
description: "Route Spec Kit implementation tasks through the Harbor of Fish runner after prerequisite and checklist checks"
metadata:
  author: "github-spec-kit"
  source: "templates/commands/implement.md"
  local_integration: "harbor-runner"
---

# Spec Kit implementation through the project runner

Treat `$ARGUMENTS` as the user's requested feature and scope. This skill is the entry point for Spec Kit task implementation. The primary agent performs read-only preparation and starts the project runner; only the runner's GPT-6 Luna implementer changes repository files. The runner then validates and invokes the Gemma reviewer in read-only mode. Do not directly implement tasks, create ignore files, or mark tasks `[X]` in the primary session. Do not invoke this skill recursively from the implementer.

## 1. Stop gates before hooks or writes

1. Read `AGENTS.md`. From the repository root run `git status --porcelain=v1`. If it is nonempty or Git status fails, stop and report the current state without changing it or invoking hooks or the runner. Run the same check again immediately before runner dispatch.
2. Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from the repository root. Resolve `FEATURE_DIR` and `AVAILABLE_DOCS` to absolute paths. If required artifacts are missing, stop and suggest `$speckit-tasks` when the task list is absent.
3. If `FEATURE_DIR/checklists/` exists, count all `- [ ]`, `- [X]`, and `- [x]` items in every checklist and display total, completed, and incomplete counts. If any item is incomplete, stop and ask whether to proceed; continue only after an explicit affirmative reply. A prior explicit reply for this same feature may be reused.
4. Read `.specify/extensions.yml` if present. Skip disabled hooks. Never execute or suggest automatic `git add`, `git commit`, `git push`, publish, deploy, or data deletion through a pre- or post-implementation hook. If an enabled mandatory hook needs one of these operations, stop and report the conflict. An invalid hooks file does not grant permission to run hooks. The project normally disables its optional `speckit.git.commit` hooks for `before_implement` and `after_implement`.

## 2. Build the runner plan

Read `spec.md`, `plan.md`, and the full `tasks.md`. Read the available `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`, plus `.specify/memory/constitution.md`, `docs/README.md`, and the applicable development standards. Parse task IDs, phases, dependencies, `[P]` markers, target files, TDD order, validation checkpoints, and acceptance requirements. Preserve the feature's safety constraints and the user's requested scope.

Write a JSON plan **outside the repository** with exactly these four fields, as required by `.codex/orchestrator/run.py`:

- `request`: a nonempty string naming the feature and requested task range.
- `scope`: a nonempty string array describing included task IDs, dependencies, permitted files, phase order, TDD sequence, and exclusions.
- `acceptance_criteria`: a nonempty string array mapping task and specification outcomes to observable evidence. Require the implementer to mark a task `[X]` only after its implementation and relevant validation have actually succeeded; unchecked or unverified tasks remain `[ ]`.
- `validation_commands`: a nonempty object mapping command names to **argv arrays exactly matching** `.codex/validation.toml`. Include every name in `[validation].required` and all applicable application test, lint, build, and backend checks for the requested scope. Do not use orchestrator self-tests as the sole validation for product implementation.

For a full `001-local-fullstack-skeleton` implementation, include `frontend_test`, `frontend_lint`, `frontend_build`, `backend_checkstyle`, and `backend_verify` along with the required commands. These application entries are candidates until their generated projects and scripts exist and the commands actually run. Verify their expected scripts against `quickstart.md` and the task plan before dispatch. If an argv needs to change, update the allowlist and plan through the normal clean-worktree workflow before starting this runner. Record database, HTTP, OpenAPI, browser, keyboard, and restart acceptance separately where tasks require them; automated runner success is not evidence that those checks occurred.

The implementer, not the primary agent, performs project setup, ignore-file changes, tests-before-code, phase-by-phase implementation, validation, and evidence-backed task marking. The Gemma reviewer checks the resulting diff, task markings, and evidence against the plan. Tasks sharing files run sequentially; `[P]` permits parallel work only when dependencies and files do not conflict.

## 3. Dispatch once and inspect the result

After the final clean-worktree check, run `python3 .codex/orchestrator/run.py --plan <absolute-plan-path>` from the repository root. If `.codex/runs` is not writable, pass `--runs <absolute-writable-directory-outside-the-repository>` so the runner can retain its artifacts. Do not launch a second runner over a dirty worktree. The runner owns the Luna implementer, validation loop, and read-only Gemma review, up to its configured five-round limit.

Read the runner summary, validation results, diff, reviewer findings, and final `tasks.md`. A `passed` status is insufficient if the requested changes are absent, required application checks were omitted, or task markings lack evidence; report that mismatch as incomplete. If the runner stops or reaches maximum rounds, report the remaining unchecked tasks and cause. Do not silently complete them in the primary session.

When the requested scope covers only part of `tasks.md`, report the remaining task IDs and that another runner invocation requires a clean worktree. Do not commit or discard this run's changes to make the next invocation possible.

Report changed files, command outcomes, P0–P3 findings, completed and remaining task IDs, and any DB/API/browser/OS checks still unverified. Do not execute post-implementation commit hooks or any Git write, publish, deploy, or data deletion without the user's separate explicit authorization.
