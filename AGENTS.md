# Agent 協作規則

## 角色分工

本專案使用兩個 project agents：

- `implementer`：負責需求實作、問題修正，以及執行與修改範圍相符的驗證。
- `reviewer`：負責唯讀檢查實作結果、回歸風險、安全性與測試缺口。
- 主 agent：負責拆解需求、依序派工、傳遞審查結果，並決定是否完成或要求修正。

## 標準協作流程

涉及程式碼、設定或內容修改的任務，原則上依以下順序執行：

1. 主 agent 先確認需求、驗收條件、相關檔案與目前工作區狀態。
2. 先啟動 `implementer`。它必須先檢查相關程式碼、`AGENTS.md`、`git status` 與現有測試，再進行最小必要修改。
3. 等 `implementer` 完成修改與驗證後，才啟動 `reviewer`。
   - 僅在直接派送 reviewer 時，ChatGPT account 回報 Gemma 不支援，才使用以下 fallback；這不是一般 delegation 的替代流程。
   - 在 repository root 直接啟動 Gemma 唯讀 Codex session，要求它讀取 `.codex/agents/reviewer.toml`，並遵守其中的 `developer_instructions`，審查目前的 git diff、相關程式碼、測試與設定：
     ```sh
     codex --oss --local-provider ollama --model gemma4:31b-cloud exec --ephemeral --sandbox read-only "Read .codex/agents/reviewer.toml and follow its developer_instructions to review the current git diff, relevant code, tests, and configuration. Do not modify files or change workspace state. Return findings and any unverified areas."
     ```
4. `reviewer` 只讀檢查目前的 `git diff`、相關程式碼、測試與設定，不得修改檔案或改變工作區狀態。
5. 主 agent 彙整實作與審查結果：
   - 沒有實質問題時，回報修改檔案、驗證結果與未解決風險。
   - 發現 P0/P1 問題時，將具體 findings 傳回 `implementer` 修正，重新驗證後再讓 `reviewer` 複查一次。
6. 最多執行五輪「審查 → 修正 → 複查」循環；若五輪後仍有問題，明確回報並交由使用者決定下一步。

## 並行與工作區規則

- `implementer` 與 `reviewer` 不得同時執行依賴同一份工作區狀態的任務。
- 不要讓兩個 agent 同時修改同一工作區或同一批檔案。
- 只有彼此獨立且不會讀寫相同檔案的探索或分析工作，才適合平行執行。
- 必須保留使用者原有的未提交修改，不得重設、覆寫或清除無關變更。

## Git 與外部操作

- agent 不得自行執行 `git add`、`git commit`、`git push`、發布、部署或刪除資料。
- 這些操作必須由使用者另外明確授權後才可執行。
- 完成後應回報修改檔案、測試或 lint/build 結果、reviewer findings，以及尚未驗證的部分。

## Runner 啟動條件

- 主 agent 只有在使用者明確要求執行本專案 runner 時，才能啟動 `.codex/orchestrator/run.py`。
- 一般實作、檢查或審查請依本文件的 agent 分工處理，不得自行啟動多模型迴圈。
