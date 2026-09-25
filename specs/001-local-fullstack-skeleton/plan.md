# Implementation Plan: 第一階段本機前後端骨架

**Branch**: `001-local-fullstack-skeleton` | **Date**: 2026-09-25 | **Spec**: [spec.md](spec.md)

## Summary

建立一個 monorepo 內可重現的 Angular 21 → `/api/v1` Spring Boot 模組化單體 → PostgreSQL 流程，只呈現三筆明確標記的中性固定測試資料。Flyway 只管理 schema；獨立載入命令負責驗證及冪等載入資料。API、資料庫與前端僅以 local/test 設定啟用，不建立公開產品功能。研究決策與替代方案見 [research.md](research.md)，資料欄位見 [data-model.md](data-model.md)，線上契約見 [contracts/openapi.yaml](contracts/openapi.yaml)。

## Technical Context

**Language/Version**: TypeScript 5.9.x；Java 21 LTS；SQL（PostgreSQL 18）；Node.js 22.12+（Angular 21 相容範圍內；以 repository 版本檔固定 major/minimum）。

**Primary Dependencies**: Angular 21 / Angular CLI、ESLint/@angular-eslint；Spring Boot 4.1.1；Spring Web、Validation、Spring Data JDBC、Flyway PostgreSQL support；PostgreSQL JDBC driver；Maven Checkstyle plugin；Docker Compose；npm 與 Maven Wrapper 3.9.11。

**Storage**: PostgreSQL 18，專用本機資料庫 `harbor_local`；Flyway 版本化遷移。固定資料來源採版控 JSON，獨立載入，不把可變測試資料放進 schema migration。

**Testing**: 前端採 Angular CLI 預設 Vitest、jsdom、TestBed 與 HTTP 測試工具；後端採 JUnit Jupiter、Spring Boot Test、MockMvc 及 PostgreSQL Testcontainers；API 契約檢查使用 OpenAPI 3.1；跨端以本機 HTTP 冒煙流程及瀏覽器測試頁驗收。實際套件 patch、命令和工具可用性須在骨架建立後確認。

**Target Platform**: 第一階段完整驗收須以本次明確記錄的單一目標作業系統為準；該 OS 的本機基線命令須全數實際成功。Docker Compose 提供 PostgreSQL，Node.js 與 Java 於主機執行，僅本機開發與自動化測試，不部署、不公開。macOS、Linux、Windows 其餘未實測平台須逐一標記「待驗證」，不得宣稱跨平台已驗收；未實測其他平台不否定已實測目標 OS 的階段結果。quickstart 中未實測命令仍是候選命令，狀態為「待驗證」。

**Project Type**: Web application monorepo（`frontend/`、`backend/`、`infra/`、`scripts/`）。

**Performance Goals**: 本階段不設吞吐量或延遲 SLO；一次讀取最多三筆固定資料，啟動、載入和驗收以可靠、可重現為目標。

**Constraints**: 不得匯入或呈現真實漁港、魚種、漁季、價格或限制；不得提供地圖、管理介面、會員、公開功能或外部資料來源。固定資料不得含個資或秘密。清除程序只能針對精確核准的本機資料庫刪除帶測試標記的資料列；不得使用 Flyway clean、DROP DATABASE 或通用清空指令。命令未在骨架上實際執行前一律標示「待驗證」。

**Scale/Scope**: 1 個前端工作區、1 個 Spring Boot 部署單元、1 個本機 PostgreSQL service、1 張測試資料表、3 筆固定資料、2 個唯讀 API 路徑、1 個繁體中文測試頁。

## Constitution Check

| 憲章閘門 | 計畫決策 | 結果 |
| --- | --- | --- |
| I. 領域詞彙與資料可信度 | 使用「固定測試資料」與中性 `fixture` 詞彙；不使用真實領域資料。API 每筆回應帶 `testOnly: true`，畫面固定呈現僅供測試說明。 | PASS |
| II. 可觀察行為與小切片 TDD | 先由 API 成功／錯誤、輸入驗證、載入冪等和前端狀態切片定義公開結果，再逐片紅綠重構；以 API、畫面及真實 PostgreSQL 可觀察結果測試。 | PASS |
| III. 清楚責任與適度抽象 | Angular 頁面擁有畫面狀態，型別化 API client 集中 HTTP；後端分 HTTP、application、fixture module 與 repository；不拆服務、不增加管理／領域抽象。 | PASS |
| IV. API、安全與資料遷移 | OpenAPI 3.1 文件 `/api/v1` 契約；統一 Problem Details 錯誤；Flyway 版本化遷移；本機設定採假值，錯誤不洩漏內部資訊。 | PASS |
| V. 手機優先與可操作狀態 | 測試頁在窄螢幕可讀、具標籤與鍵盤操作；明確區分載入、成功、空結果及錯誤，提供重試。 | PASS |
| 八階段交付與首次公開閘門 | 本工作只規劃第一階段本機骨架；不產生公開服務或提早公開路徑。 | PASS |

**Post-design gate**: PASS。資料格式、唯一鍵、交易載入、雙重清除保護、API profile 隔離與端別測試邊界均已在設計文件具體化。沒有未解規格澄清；工具命令的可執行性仍待骨架建立後實際驗證，不能以本計畫宣稱通過 SC-006。

## Delivery Order

遵照 [docs/development-plan.md](../../docs/development-plan.md) 的八階段順序，不改寫既有階段：

1. **前後端架構建立（本 feature）**：建立本機 Angular/API/DB 往返、測試資料與環境防護；內部驗收後才供第二階段依賴。
2. **地點資料與內容底稿**：另階段查證官方資料、來源及授權。
3. **地圖與地點探索**：依第二階段已核對的地點資料實作。
4. **魚種深度港口與月份探索**：依已查證內容實作代表性漁季呈現。
5. **批發價格與趨勢**：依可靠批發行情來源與授權實作。
6. **當季探索建議**：限制來源查核成立後才啟用。
7. **洋流故事內容與 API**：完成來源、素材與科普標示後實作。
8. **故事互動與全站驗收**：全部前階段內部驗收完成後才評估首次公開。

本階段不預先建立第二至八階段的實體、端點、功能或資料；各後續階段仍須依其規格重新做需求與架構決策。

## Project Structure

```text
mvnw / .mvn/wrapper/                    # repository-level Maven Wrapper
frontend/
├── src/app/features/local-test/       # 本機測試頁與局部狀態
├── src/app/core/api/                  # 集中、具型別的 HTTP 存取層
├── proxy.conf.json                    # 開發期間將 /api 代理至本機 API
└── package.json / package-lock.json
backend/
├── src/main/java/.../api/             # Controller、DTO、錯誤映射
├── src/main/java/.../application/     # 查詢與載入使用案例
├── src/main/java/.../fixture/         # fixture 模組及明確介面
├── src/main/resources/db/migration/   # V1__create_local_test_fixture.sql
├── src/main/resources/local-test-fixtures.v1.json
└── src/test/                          # unit、HTTP、PostgreSQL integration tests
infra/
├── compose.yaml                       # loopback 綁定的 PostgreSQL 18
└── .env.example                       # 假值，非秘密
scripts/
├── load-local-test-data.sh            # 驗證後冪等載入
├── reset-local-test-data.sh           # 嚴格檢查後只刪測試資料
└── smoke-local.sh                     # API/DB 往返冒煙檢查
specs/001-local-fullstack-skeleton/    # 本 feature 計畫與驗收契約
```

**Structure Decision**: 採 `docs/architecture/system-overview.md` 建議的前後端獨立目錄及 `infra/`，新增窄責任 `scripts/` 存放本機載入、清除和冒煙入口。後端暫用單一 local-test 模組，不為不存在的魚類、漁港或管理功能建立模組。

## Design Decisions

1. **三筆中性 JSON fixtures**：每筆用固定 UUID、唯一 `fixtureKey`、繁中中性標題與說明、固定 `datasetVersion` 和 `testOnly=true`。先檢查完整檔案、欄位、長度、唯一性、筆數和測試標記，再開單一交易 upsert；任何一筆無效時零筆寫入。重複載入以 `fixture_key` 唯一約束覆寫為版控檔的 canonical 值，筆數及內容不變。格式細節見 [data-model.md](data-model.md)。
2. **schema 與 fixture 分離、遷移不可變**：`V1__create_local_test_fixture.sql` 建立專用 schema/table、NOT NULL、長度、唯一與 `test_only = true` 限制；Flyway migration 不插入可變 fixture rows。T013-T015 須在 PostgreSQL 上測試 V1 的 schema history、必要欄位及各項限制拒絕非法列，並以有效紅燈和綠燈證據完成；此驗收必須先於 T029 首次端到端驗收及其全新本機 DB 首次套用 V1。V1 一旦套用即視為已發布遷移，不得原地修改。若後續 T036-T037 回歸發現限制缺口，須新增有序 V2 遷移，分別驗證已套用 V1 的專用本機 DB 升級 V1→V2，以及全新 DB 從 V1→V2 的完整路徑；不得清除或重建 DB 作為修正方式。整體順序是空 DB → Flyway migrate/validate → API local profile 完成啟動 → loader 驗證並載入 fixtures → 前端與 API 驗收。錯誤遷移阻止 API 正常就緒；API 在載入前若收到 list 查詢，應回空集合並保留 test metadata，不能回傳假成功資料。
3. **清除採 fail-closed**：清除命令要求明確 `APP_ENV=local` 與 `RESET_LOCAL_TEST_DATA=YES`；JDBC host、port、database、登入資料庫回報的 `current_database()` 必須分別符合 `127.0.0.1`、`5432`、`harbor_local`、`harbor_local`，並要求明確確認旗標。任一缺少、不符、解析失敗即在執行 DELETE 前退出非零。成功時僅交易刪除 fixture table 中 `test_only=true` rows，驗證刪除數量；不執行 schema/database drop 或 Flyway clean。Compose 僅將 DB port 發佈到 loopback。測試需驗證不符環境、遠端 host、正式名稱、錯誤連線與缺旗標全都在 mutation 前拒絕。
4. **local/test 專用唯讀 API**：local/test Spring profile 才註冊 `/api/v1/local-test/fixtures` 與 `/{fixtureKey}`；其他 profile 啟動時不掛載路由並拒絕 fixture loader/reset。DTO 不暴露資料庫實體。成功 envelope 提供 `testOnly`、`datasetVersion`、`count`；錯誤使用 RFC 9457 Problem Details 加穩定 `code` 和欄位錯誤，服務端日誌可記 correlation ID，但回應不帶 stack、SQL、秘密或內部 hostname。契約詳見 OpenAPI。
5. **前端狀態由頁面持有**：單一 typed API client 執行 HTTP，頁面以 discriminated state 表達 `loading | success | empty | error`；成功/空/錯誤均有固定「僅供測試」說明，不以 fixture 假資料遮蔽 API 失敗；錯誤提供重試。開發代理只轉送 `/api`，不把 DB 設定帶入前端。

## Validation Strategy

- **契約先行與 TDD**：先以 OpenAPI / HTTP 行為測試固定成功 envelope、錯誤形狀、400 格式錯誤、404 不存在項目及 local profile 外不可用；再按小切片實作。
- **資料與遷移**：T013-T015 在首次端到端流程 T029 前，使用 PostgreSQL Testcontainers 實際套用 V1，檢查 schema history、必要欄位與每項必要 CHECK/NOT NULL/唯一限制的違規寫入拒絕，以及遷移失敗時應用不就緒；T014 紅燈須由 Failsafe 報告證明是預期資料庫行為缺失，T015 綠燈須證明同一 PostgreSQL 測試通過。T036-T037 可在 US2 執行較完整限制回歸，不得修改已套用 V1；若回歸揭露缺口，新增有序 V2，測試專用 DB V1→V2 升級與全新 DB V1→V2 兩路徑，保留既有資料及 Flyway history，不清除或重建 DB。Integration tests 不以 H2 代替 PostgreSQL。
- **載入與清除**：成功載入、重複兩次、檔案缺欄/型別錯誤/重複 key/非測試標記時整批拒絕；比對 count 與每欄值。清除驗證核准本機條件下只移除測試 rows，所有錯誤 guard 案例確認資料未改變。
- **後端**：application/module 測試觀察查詢與冪等結果；MockMvc 驗證路由、輸入、成功 DTO、錯誤與 profile 邊界；PostgreSQL integration 驗證 Flyway、保存/讀取、unique/check constraints 及 transaction rollback。
- **前端**：API client HTTP 測試驗證型別映射、網路錯誤和 Problem Details；Angular component/頁面測試驗證 loading、非空 success、empty、error、retry 與測試標記可見，且不由元件私自發送 HTTP。
- **跨端與重啟**：依 [quickstart.md](quickstart.md) 從新 clone/乾淨 local DB 執行，載入、呼叫 API、看繁中頁、停掉並重啟服務；確認資料與欄位完全相同。命令須在後續實作環境逐條實際執行，結果寫入 README 或端別開發規範。
- **命令狀態**：本計畫建立時僅 `setup-plan.sh --json` 已實際執行；應用骨架、build、lint、測試、遷移及冒煙命令均尚無可驗證目標，quickstart 以「候選／待驗證」明示。不得把文件中的命令列為可用基線，亦不得宣稱 SC-006 已通過。
- **平台驗收界線**：SC-006 的完整驗收只依本次明確記錄的單一目標 OS 判定，該 OS 本機基線命令須全部實際成功。對 macOS、Linux、Windows 其餘未實測平台逐一標「待驗證」，不得宣稱跨平台驗收；這不會否定目標 OS 已實測達成的階段結果。計畫、quickstart 或任務中未實際執行的命令均維持候選／待驗證。

## Complexity Tracking

無憲章違規，無需例外或額外架構層。
