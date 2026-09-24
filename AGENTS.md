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

## 架構文件入口

- 開始處理專案架構或相關功能前，先閱讀 [`docs/README.md`](docs/README.md) 的文件索引，再依需求閱讀對應文件。
