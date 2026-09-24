# Agent 協作規則

## 角色分工

本專案採 Codex 規劃與 GPT-6 Luna 實作、Gemma 唯讀審查的流程：

- Codex 預設使用 `gpt-6-luna`，負責理解一般實作需求、檢查工作區並輸出完整計畫，不直接修改產品檔案。
- Implementer 使用 GPT-6 Luna high 與 `workspace-write` sandbox，依計畫實作；reviewer 使用 Ollama `gemma4:31b-cloud` 與 `read-only` sandbox 審查。兩個角色由 runner 以獨立 Codex CLI sessions 執行。
- 明確要求只規劃或只檢查時，只回應該要求，不啟動 runner。

## 標準協作流程

一般程式碼、設定或內容實作需求依以下順序自動執行：

1. Codex 檢查需求、修改範圍、驗收條件、合適的驗證命令及工作區狀態。
2. 只有工作區乾淨時才繼續；有任何未提交變更便停止並回報，不自行清理或改寫。
3. Codex 將計畫寫成 repository 外的暫存 JSON 檔，欄位必須是 `request`、`scope`、`acceptance_criteria`、`validation_commands`。驗證命令使用具名 argv 陣列。
4. 若尚未設定 `ollama-launch` profile，先依 Ollama 官方方式執行 `ollama launch codex --config`，並確認 profile 存在。將計畫傳給 `.codex/orchestrator/run.py --plan <暫存檔>`。runner 以 `codex --model gpt-6-luna exec --ephemeral --sandbox workspace-write` 呼叫 implementer，再以 `codex --profile ollama-launch --model gemma4:31b-cloud exec --ephemeral --sandbox read-only` 呼叫 reviewer；兩次呼叫都明確要求遵循對應的 `.codex/agents/*.toml` 指令。
5. runner 執行計畫內列出的驗證；驗證失敗或有效 JSON 審查結果包含 P0/P1 時，將證據交回 implementer 修正後重跑驗證與審查，最多五輪。P2/P3 不阻擋完成。
6. 審查輸出必須符合 runner 驗證的 JSON 合約。所有輪次都保存計畫、基準 SHA、提示與模型輸出、驗證結果、diff、審查 findings 及最終摘要。
7. 主 agent 彙整 runner 結果及仍未驗證的事項。

## 並行與工作區規則

- implementer 與 reviewer 必須依序執行；reviewer 使用唯讀 sandbox。
- 必須保留使用者原有的未提交修改；runner 遇到髒工作區即停止。

## Git 與外部操作

- agent 不得自行執行 `git add`、`git commit`、`git push`、發布、部署或刪除資料。
- 這些操作必須由使用者另外明確授權後才可執行。
- 完成後應回報修改檔案、測試或 lint/build 結果、reviewer findings，以及尚未驗證的部分。

## Runner 啟動條件

- 一般實作需求在 Codex 完成計畫且工作區乾淨後，自動啟動 `.codex/orchestrator/run.py`。
- 使用者明確要求只規劃或只檢查時，不啟動 runner。

## Spec Kit 與實作 runner 的分工

- Spec Kit 用於先整理需求與規格，再建立技術計畫和任務；Codex skills 安裝完成後，可依序使用 `$speckit-specify`、`$speckit-clarify`（需要釐清時）、`$speckit-plan`、`$speckit-tasks`。`$speckit-constitution` 僅在專案規則經確認後才填寫，不可把範本預設內容當成本專案規則。
- Spec Kit 產生的 spec、plan、tasks 是實作輸入與追蹤文件，不會取代一般程式碼需求的 runner 流程。依本文件的標準流程，由 runner 呼叫 GPT-6 Luna implementer 執行，並由 Gemma reviewer 唯讀審查；不要以 `$speckit-implement` 繞過這個流程。
- Spec Kit skills 未安裝或 `specify integration status` 尚未辨識為 Codex 前，不要假設 `$speckit-*` 已可呼叫。安裝時使用 Spec Kit 官方 CLI；保留既有 `.agents/skills`、`.codex`、文件及產品檔案。

## 架構文件入口

- 開始處理專案架構或相關功能前，先閱讀 [`docs/README.md`](docs/README.md) 的文件索引，再依需求閱讀對應文件。
- 開發者與 AI agent 在新增或修改前端、後端、API、資料庫及測試時，必須遵守[共同開發規範](docs/development-standards.md)及工作範圍對應的[前端規範](docs/frontend-development-standards.md)或[後端規範](docs/backend-development-standards.md)；跨前後端的工作須同時遵守兩份。本規範不取代本檔的 runner、reviewer、工作區保護及 Git 授權要求。
