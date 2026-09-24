# Harbor of Fish｜台灣漁港與魚類知識資料庫

從漁港出發，認識台灣的魚類與漁業文化。

## 專案介紹

Harbor of Fish 致力於整理台灣漁港、常見魚類與漁業相關知識，將分散的資訊轉化為清楚、易讀的內容，讓對海洋有興趣的人，都能找到認識台灣漁業的起點。

從各地漁港的特色、魚類的名稱與辨識，到漁獲和在地生活的連結，希望透過持續累積的知識，讓讀者不只認識魚，也理解魚與港口、海洋及人的關係。

## 內容方向

- **台灣漁港**：認識各地漁港的位置、特色與在地漁業背景。
- **魚類知識**：整理常見魚類的名稱、俗名、外觀特徵與棲地資訊。
- **漁業與文化**：介紹漁法、季節性漁獲，以及漁港周邊的生活與文化。

## 適合誰閱讀

無論是想認識常見魚類、了解台灣漁港，或探索在地漁業文化的讀者，都可以透過這個專案建立基礎認識，延伸自己的海洋知識。

## 目前進度

專案目前處於初期建置階段，將依上述方向逐步整理與補充內容。

## 需求規格與 AI 協作

GitHub Spec Kit 用於把需求整理成規格、技術計畫與任務清單。Codex skills 安裝完成後，建議依序使用 `$speckit-specify`、視需要使用 `$speckit-clarify`，再使用 `$speckit-plan` 與 `$speckit-tasks`；只有在專案規則經確認後才填寫 `$speckit-constitution`。此流程先產生規劃文件，不代表已開始實作產品功能。

產品程式碼的一般實作仍依 [`AGENTS.md`](AGENTS.md) 的既有流程交由 `.codex/orchestrator/run.py` 執行：GPT-6 Luna implementer 負責實作，Gemma reviewer 以唯讀方式審查。Spec Kit 的規格、計畫與任務可作為該流程的輸入，不取代 runner 的實作與審查邊界。

此 repository 已初始化 Spec Kit 的 Codex 整合，skills 位於 `.agents/skills/speckit-*`。可用 `specify integration status` 確認整合狀態；在專案目錄啟動新的 Codex 對話後，即可呼叫對應的 `$speckit-*` skill。
