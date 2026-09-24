# Harbor of Fish 文件

此索引提供專案文件入口。開始處理架構或相關功能前，先閱讀本頁，再依工作範圍查看對應文件。

## 產品

- [手機版網站產品規劃](product-plan.md)：產品定位、三階段功能、資料流、完成條件與驗收情境。

## 架構

- [系統總覽](architecture/system-overview.md)：前後端責任、系統邊界、主要資料流、建議 monorepo 目錄及本機開發方式。
- [API 與領域模型](architecture/api-and-domain.md)：公開查詢與管理端 API 方向、發布及存取界線、核心領域關係。
- [架構決策](architecture/decisions.md)：目前採用的預設、未納入範圍及待決事項。

## 開發

- [共同開發規範](development-standards.md)：TDD、API 契約、資料語意、安全與交付要求。
- [前端開發規範](frontend-development-standards.md)：Angular 元件與狀態、手機介面及前端測試邊界。
- [後端開發規範](backend-development-standards.md)：Spring Boot 領域模組、資料庫與授權及後端測試邊界。

開發者與 AI agent 必須遵守共同規範及工作範圍對應的前端或後端規範；實際工具與命令待程式骨架建立後補定。
