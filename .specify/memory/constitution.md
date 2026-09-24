<!--
Sync Impact Report
- Version change: 1.0.0 -> 2.0.0
- Modified principles: None; the five core principles remain unchanged
- Modified constraints: the three-stage first-phase map requirement was replaced by the approved eight-stage delivery sequence; phase one is a local test-only skeleton, and first public release follows all eight internal acceptances
- Added sections: None
- Removed sections: None
- Follow-up documents: docs/development-plan.md added; docs/README.md, docs/product-plan.md, docs/frontend-development-standards.md, docs/backend-development-standards.md, and docs/architecture/decisions.md synchronized
- TODO: None
-->
# Harbor of Fish Constitution

## Core Principles

### I. 領域詞彙與資料可信度

- 名稱、API、資料模型與介面 **MUST** 區分魚類、漁港、漁業文化、發布狀態及資料來源所代表的概念；呈現資料時 **MUST** 保留來源、適用期間、查證或更新時間與已知限制。
- **MUST** 將代表性漁季表述為有來源支持的季節資訊，不得宣稱為某港口或月份的實際漁獲；**MUST** 將批發行情標為批發價格，不得當成零售價格；洋流內容 **MUST** 標為科普示意，不得暗示為即時海況或漁獲預測。
- 資料不足時 **MUST** 明確表示未知、待查或資料待補。沒有漁季資料不得推論「該月沒有魚」，價格缺值不得轉成零，也不得自行補造港口、魚種、月份或價格。

理由：可靠來源、期間及缺值語意是使用者解讀漁港與魚種資訊的必要條件。

### II. 可觀察行為與小切片 TDD

- 新增功能、修正錯誤、變更 API 行為或領域規則時，**MUST** 先界定使用者、API 呼叫者或外部系統可觀察的結果，並以公開介面測試一個小行為切片；**MUST** 確認測試因預期行為尚未實作而失敗，再實作使該切片通過的最小改動，之後才進入下一切片。
- 測試 **MUST** 根據需求、已知案例或明確邊界驗證情境與結果，不得用私有方法、內部呼叫次數或照抄實作公式取代行為驗證。
- 純文件變更 **MAY** 不執行程式測試，但 **MUST** 檢查連結、內容一致性與修改範圍；純視覺或機械式變更可採適用的視覺或靜態驗證。例外 **MUST** 說明驗證方式及未執行項目；若使用者行為有變，仍須採 TDD。

理由：先固定可觀察結果，能以逐步驗證降低需求誤解及回歸風險；例外仍需留下可檢查的證據。

### III. 清楚的責任與適度抽象

- 前端 **MUST** 依功能或領域組織；頁面組合流程，元件負責清楚的呈現或互動，狀態 **MUST** 由實際擁有它的頁面、功能或服務管理。具型別的 API 存取層 **MUST** 集中 HTTP 呼叫；前端 **MUST NOT** 直接連線 PostgreSQL，模板 **MUST NOT** 承載多步驟領域規則或資料轉換。
- 後端 **MUST** 依領域組織為模組化單體，模組透過明確應用介面協作，不任意讀寫其他模組內部資料或依賴其持久化實作。Controller、應用服務、領域程式與資料存取層 **MUST** 保持各自責任；DTO **MUST NOT** 直接暴露資料庫實體或內部持久化欄位。
- 元件、模組、函式與共用抽象 **MUST** 有明確責任及資料所有者。只有已出現的重複、變化點、複雜度或隔離需求足以支持時，才引入共用層、介面或框架；不得為預想需求建立通用機制，也不得僅因模組數量拆成微服務。

理由：明確所有權使修改與測試可定位；依已證實需求控制抽象，避免過早增加耦合。

### IV. API 契約、安全與資料遷移

- 前後端 **MUST** 以 `/api/v1` 版本化 REST 契約協作。路徑、請求、回應、錯誤與存取政策 **MUST** 有文件及相應測試；相容變更須維持既有語意，不相容變更須另行規劃版本。
- 公開 API **MUST** 僅提供已發布且可公開的內容。管理寫入端點與公開查詢 **MUST** 分開界定；實作管理操作時，身分與權限 **MUST** 由後端驗證，前端路由或按鈕限制不得視為安全控制。管理 CRUD、發布、下架及刪除僅能在相應需求確立後實作。
- 密碼、憑證、存取權杖及第三方私密金鑰 **MUST NOT** 提交至 repository、回傳瀏覽器或寫入一般日誌；範例設定 **MUST** 使用明確假值，必要診斷資料 **MUST** 遮蔽或去識別化。
- PostgreSQL schema 變更 **MUST** 使用可追溯且順序明確的 Flyway 版本化遷移納入版本控制，不得以手動資料庫操作取代遷移。後端 **MUST** 驗證外部輸入，並不得在錯誤回應中洩漏堆疊追蹤、SQL、憑證或內部主機資訊。

理由：明確契約與伺服器端安全界線保護公開資料；版本化遷移使結構變更可追蹤並能隨程式檢視。

### V. 手機優先與可操作的狀態

- 面向使用者的互動 **MUST** 可在手機尺寸使用，並支援鍵盤操作、可辨識標籤、焦點與選取狀態；地圖等非標準控制 **MUST** 提供可操作的替代方式，地圖標記與列表選取狀態 **MUST** 保持同步。
- 非同步畫面 **MUST** 依情境呈現載入、失敗、空結果及未知或資料待補狀態；未知不得靜默轉成空集合、零值或否定事實。錯誤訊息 **MUST** 可理解，並在適用時提供重試、返回或清除篩選等操作。
- 瀏覽器定位權限 **MUST** 只在使用者主動操作定位功能時請求。拒絕或無法定位時，手動搜尋及縣市篩選 **MUST** 仍可使用。

理由：手機是主要使用情境；可辨識且可操作的替代流程，讓資料狀態與權限拒絕不會阻斷瀏覽。

## Additional Constraints

- 目前技術方向為 Angular 21 前端、Spring Boot 模組化單體後端、PostgreSQL 與 Flyway；這些是架構預設，不代表前後端程式骨架已建立。
- 前後端骨架、應用程式測試工具與測試、lint、build 命令尚未建立或實際確認。維護者只有在骨架及工具建立後，才能依實際驗證結果補列命令；不得將 orchestrator 命令宣稱為應用程式命令。
- 部署平台、網域、CI/CD、正式環境拓樸、管理者認證提供者與管理角色細分等細節尚未定案，須待需求與環境明確後再決策並更新適用架構文件。
- 功能交付 **MUST** 依[八階段開發計畫](../../docs/development-plan.md)安排。第一階段僅建立可在本機重現的前後端與資料庫測試骨架，使用明確標示的固定測試資料；**MUST NOT** 提供地圖、真實漁港、魚種、漁季、價格或限制資料查詢，亦不得對外公開產品功能。後續階段依八階段計畫交付；全部階段完成內部驗收前 **MUST NOT** 首次公開網站。[產品規劃](../../docs/product-plan.md)描述產品方向，不取代八階段交付順序；管理介面及一般會員功能不因本次階段調整而納入。

## Development Workflow

- 開始架構或功能工作前，**MUST** 閱讀[文件索引](../../docs/README.md)及適用規範；實作前端須遵守[共同開發規範](../../docs/development-standards.md)與[前端開發規範](../../docs/frontend-development-standards.md)，實作後端須遵守共同規範與[後端開發規範](../../docs/backend-development-standards.md)，跨前後端工作須遵守兩份專項規範。
- 一般實作 **MUST** 依 [AGENTS.md](../../AGENTS.md) 的流程檢查工作區，僅在乾淨工作區啟動 runner，依序使用 implementer 與唯讀 reviewer，並保留既有修改。agent 不得自行執行 `git add`、`git commit`、`git push`、發布、部署或刪除資料；這些操作須另有使用者明確授權。
- 每次交付 **MUST** 說明可觀察驗收結果、修改範圍、已執行的測試或例外驗證、適用的 lint／build／遷移結果、文件更新及未驗證事項與風險。未執行或無法執行的驗證須註明原因。
- 純文件變更依共同開發規範檢查連結、內容一致性及修改範圍，不要求執行程式測試；交付時仍須指出實際採用的文件檢查及未驗證事項。

## Governance

- 本憲章適用於 Harbor of Fish 的產品、架構、實作與審查。提議修訂時，**MUST** 說明理由、影響的原則或章節、相容性影響及必要的遷移或文件更新；修訂 **MUST** 經專案維護者審查同意，並更新本檔版本與最後修訂日期。
- 版本採語意化版本：新增原則或章節、或實質擴充要求時增加 MINOR；不相容地移除或重新定義原則時增加 MAJOR；不改變要求的澄清、文字或錯字修正時增加 PATCH。首次採納版本為 `1.0.0`。
- 規劃、實作及審查 **MUST** 檢查與本憲章的一致性；交付審查 **MUST** 指出不符合項目、適用例外及其驗證。發現不一致時，須修正提案或依上述程序修訂憲章，不得默默忽略原則。
- [AGENTS.md](../../AGENTS.md) 所定操作流程與[共同開發規範](../../docs/development-standards.md)、[前端開發規範](../../docs/frontend-development-standards.md)、[後端開發規範](../../docs/backend-development-standards.md) 仍是具體執行細節的依據。本憲章定義治理原則，不擅自改寫上述文件；待決架構事項依[架構決策](../../docs/architecture/decisions.md)及相關架構文件更新。

**Version**: 2.0.0 | **Ratified**: 2026-09-24 | **Last Amended**: 2026-09-24
