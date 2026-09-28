# Implementation Plan: 第一階段本機前後端骨架

**Branch**: `001-local-fullstack-skeleton` | **Date**: 2026-09-25 | **Spec**: [spec.md](spec.md)

## Summary

建立一個 monorepo 內可重現的 Angular 21 → `/api/v1` Spring Boot 模組化單體 → PostgreSQL 流程，只呈現三筆明確標記的中性固定測試資料。Flyway 只管理 schema；獨立載入命令負責驗證及冪等載入資料。API、資料庫與前端僅以 local/test 設定啟用，不建立公開產品功能。研究決策與替代方案見 [research.md](research.md)，資料欄位見 [data-model.md](data-model.md)，線上契約見 [contracts/openapi.yaml](contracts/openapi.yaml)。

## Technical Context

**Language/Version**: TypeScript 5.9.x；Java 21 LTS；SQL（PostgreSQL 18）；Node.js 22.x 且最低 22.12.0。根目錄 `.nvmrc` 寫 `22` 以選擇 22 線；`frontend/package.json` 的 `engines.node` 寫 `>=22.12.0 <23` 以表達最低版本與 major 上限。實作後執行 `nvm use`、`node --version` 並核對 `engines.node`，記錄實際選到的版本與結果；這些命令目前待驗證。

**Primary Dependencies**: Angular 21 / Angular CLI、ESLint/@angular-eslint；Spring Boot 4.1.1；Spring Web、Validation、Spring Data JDBC、Flyway PostgreSQL support；PostgreSQL JDBC driver；Maven Checkstyle plugin；Docker Compose；npm 與 Maven Wrapper 3.9.11。

**Storage**: PostgreSQL 18，專用本機資料庫 `harbor_local`；Flyway 版本化遷移。固定資料來源採版控 JSON，獨立載入，不把可變測試資料放進 schema migration。

**Testing**: 前端採 Angular CLI 預設 Vitest、jsdom、TestBed 與 HTTP 測試工具；後端採 JUnit Jupiter、Spring Boot Test、MockMvc 及 PostgreSQL Testcontainers；API 契約檢查使用 OpenAPI 3.1；跨端以本機 HTTP 冒煙流程及瀏覽器測試頁驗收。實際套件 patch、命令和工具可用性須在骨架建立後確認。

**Target Platform**: 第一階段完整驗收須以本次明確記錄的單一目標作業系統為準；該 OS 的本機基線命令須全數實際成功。Docker Compose 提供 PostgreSQL，Node.js 與 Java 於主機執行，僅本機開發與自動化測試，不部署、不公開。macOS、Linux、Windows 其餘未實測平台須逐一標記「待驗證」，不得宣稱跨平台已驗收；未實測其他平台不否定已實測目標 OS 的階段結果。quickstart 中未實測命令仍是候選命令，狀態為「待驗證」。

**Project Type**: Web application monorepo（`frontend/`、`backend/`、`infra/`、`scripts/`）。

**Performance Goals**: 本階段不設吞吐量或延遲 SLO；一次讀取最多三筆固定資料，啟動、載入和驗收以可靠、可重現為目標。

**Constraints**: 不得匯入或呈現真實漁港、魚種、漁季、價格或限制；不得提供地圖、管理介面、會員、公開功能或外部資料來源。固定資料不得含個資或秘密。清除程序只能針對精確核准的本機資料庫刪除帶測試標記的資料列；不得使用 Flyway clean、DROP DATABASE 或通用清空指令。agent 在執行任何可能刪除資料的命令或測試前，另須取得使用者對具體命令與目標的明確授權；allow-list 與確認旗標不能取代此授權。命令未在骨架上實際執行前一律標示「待驗證」。

**Scale/Scope**: 1 個前端工作區、1 個 Spring Boot 部署單元、1 個本機 PostgreSQL service、1 張測試資料表、3 筆固定資料、2 個唯讀 API 路徑、1 個繁體中文測試頁。

## Constitution Check

| 憲章閘門 | 計畫決策 | 結果 |
| --- | --- | --- |
| I. 領域詞彙與資料可信度 | 使用「固定測試資料」與中性 `fixture` 詞彙；不使用真實領域資料。API 每筆回應帶 `testOnly: true`，畫面固定呈現僅供測試說明。 | PASS |
| II. 可觀察行為與小切片 TDD | 先由 API 成功／錯誤、輸入驗證、載入冪等和前端狀態切片定義公開結果，再逐片紅綠重構；以 API、畫面及真實 PostgreSQL 可觀察結果測試。 | PASS |
| III. 清楚責任與適度抽象 | Angular 頁面擁有畫面狀態，型別化 API client 集中 HTTP；後端分 HTTP、application、fixture module 與 repository；不拆服務、不增加管理／領域抽象。 | PASS |
| IV. API、安全與資料遷移 | OpenAPI 3.1 文件 `/api/v1` 契約；統一 Problem Details 錯誤；Flyway 版本化遷移；本機設定採假值，錯誤不洩漏內部資訊；實際刪除資料另設使用者明確授權閘門。 | PASS |
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
2. **schema 與 fixture 分離、遷移不可變**：`V1__create_local_test_fixture.sql` 建立專用 schema/table、NOT NULL、長度、唯一與 `test_only = true` 限制；Flyway migration 不插入可變 fixture rows。T013-T015 須在 PostgreSQL 上測試 V1 的 schema history、必要欄位及各項限制拒絕非法列，並以有效紅燈和綠燈證據完成；此驗收必須先於 T029 首次端到端驗收及其全新本機 DB 首次套用 V1。V1 一旦套用即視為已發布遷移，不得原地修改。T036-T037 重跑 T013 的既有 `FlywayMigrationIT` 作 V1 限制回歸，不另建重複的限制矩陣；若回歸發現限制缺口，須新增有序 V2 遷移，分別驗證已套用 V1 的專用本機 DB 升級 V1→V2，以及全新 DB 從 V1→V2 的完整路徑；不得清除或重建 DB 作為修正方式。整體順序是空 DB → Flyway migrate/validate → API local profile 完成啟動 → loader 驗證並載入 fixtures → 前端與 API 驗收。錯誤遷移阻止 API 正常就緒；API 在載入前若收到 list 查詢，應回空集合並保留 test metadata，不能回傳假成功資料。
3. **清除採 fail-closed**：清除命令要求明確 `APP_ENV=local` 與 `RESET_LOCAL_TEST_DATA=YES`，且啟動 profile 必須為 local/test；JDBC host、port、database、登入資料庫回報的 `current_database()` 必須分別符合 `127.0.0.1`、`5432`、`harbor_local`、`harbor_local`，並要求明確確認旗標。DELETE 前另以 PostgreSQL `pg_control_system().system_identifier` 作叢集識別值：預期值須由待清除 JDBC URL 與同組環境變數之外、repository 管理的專用 Compose PostgreSQL 透過獨立管理通道取得（整合測試則使用明確建立的隔離測試容器）；實際值由待清除 JDBC 連線讀取，並比對以確認受管理容器與目標連線的對應。單獨的 `system_identifier` 不證明本機性，仍須保留前述 loopback、port、database、user、profile、環境設定及 `current_database()` guards。不得從待清除連線或可任意覆寫的參數提供預期值，也不得新增繞過旗標。預期或實際值無法取得、讀取權限不足、受管理容器與目標連線的對應無法確認或身分不符，均須在任何 DELETE 前以可辨識原因拒絕且零 DELETE；不可降級成只檢查設定。若 PostgreSQL 權限模型要求額外讀取權限，僅規劃提供讀取此識別值所需的最小權限，以專用本機／測試身分及可追溯的 Compose／測試容器設定步驟提供，不改動已套用的 V1 migration。任一 guard 缺少、不符或解析失敗即退出非零。成功時僅交易刪除 fixture table 中 `test_only=true` rows，驗證刪除數量；不執行 schema/database drop 或 Flyway clean。Compose 僅將 DB port 發佈到 loopback。T038 的拒絕矩陣須包含 profile 拒絕及執行個體身分拒絕案例；T039 證明有效紅燈，T040 實作 guards 並轉綠，仍不得執行 DELETE。agent 執行任何可能觸發 DELETE 的驗證或實際清除前，另須呈明具體命令與目標並取得使用者明確授權；未獲授權的允許清除測試與本機重設保留待驗證，不得因 guard 通過就自行執行。
4. **local/test 專用唯讀 API 與 fixture 操作**：local/test Spring profile 才註冊 `/api/v1/local-test/fixtures` 與 `/{fixtureKey}`，其他 profile 不掛載路由並拒絕 fixture loader/reset。T009 只建立 profile 設定；T016/T018 與 T045/T047 分別讓列表、單筆路由先測後做。T012 建立可編譯、可呼叫且不寫入的 loader 佔位入口；T019/T020 以有效 fixture、其餘合法設定先驗 loader 的非 local/test profile 拒絕與零寫入，T022 才完成拒絕和載入。Reset 的 profile 拒絕依 T038–T040 先測後做。T048 只回歸四個既有 profile 邊界；T049 的新紅燈僅限安全 500 錯誤映射，T050 僅完成該映射。DTO 不暴露資料庫實體。成功 envelope 提供 `testOnly`、`datasetVersion`、`count`；錯誤使用 RFC 9457 Problem Details 加穩定 `code` 和欄位錯誤，服務端日誌可記 correlation ID，但回應不帶 stack、SQL、秘密或內部 hostname。契約詳見 OpenAPI。
5. **前端狀態由頁面持有**：單一 typed API client 執行應用資料 HTTP 呼叫，頁面以 discriminated state 表達 `loading | success | empty | error`；成功/空/錯誤均有固定「僅供測試」說明，不以 fixture 假資料遮蔽 API 失敗；錯誤提供重試。開發代理只轉送 `/api` 應用資料請求，不把 DB 設定帶入前端；瀏覽器載入 HTML、JavaScript、CSS 等靜態資源不屬於 SC-004 的應用資料請求。

T011 先提供可編譯、可呼叫的 typed API client、可渲染頁面佔位型別／元件及尚未接上測試頁的根路由容器；client 可回傳型別正確的空結果，但不預先發 HTTP 讀取或呈現三筆畫面，也不在此任務把根路由導向測試頁。T023/T024 以 HTTP 測試工具未觀察到預期 `/api/v1` 請求為紅燈；T026/T027 以已渲染頁面缺少預期標題與測試標記為紅燈；T025/T028 分別完成既有佔位入口。根路由另於 T029 切片：先在 `frontend/src/app/app.routes.spec.ts` 寫公開行為測試，從實際根路由導覽至 `/` 並斷言繁中提醒、三筆標題及逐筆測試標記；以候選 `npm --prefix frontend test -- --watch=false --include=src/app/app.routes.spec.ts` 確認因尚未接線而有效紅燈，再修改 `app.routes.ts` 導向頁面並重跑同一測試轉綠。候選命令尚未實際執行，狀態標「待驗證」；T029 仍須完成 quickstart 的 DB/API/瀏覽器首次與重啟驗收，不能以路由測試取代。每項紅燈記錄實際選取測試、失敗斷言與原因，不以 `NOT_IMPLEMENTED`、編譯失敗、依賴或環境故障充數。

## Validation Strategy

- **契約先行與 TDD**：先以 OpenAPI / HTTP 行為測試固定成功 envelope、錯誤形狀、400 格式錯誤、404 不存在項目及 local/test profile 外不可用；列表的非 local/test 測試納入 T016，先於 T018，單筆的非 local/test 測試納入 T045，先於 T047。Loader 的 profile 拒絕先在 T019/T020 測試，T022 才實作；reset 的 profile 拒絕先在 T038/T039 測試，T040 才實作。T048 回歸既有路由與 loader/reset 邊界，T049/T050 只讓安全 500 錯誤映射紅綠。每項有效紅燈記錄實際選取測試、失敗斷言與原因，不能以 `NOT_IMPLEMENTED`、編譯／依賴／環境故障代替。
- **資料與遷移**：T013-T015 在首次端到端流程 T029 前，使用 PostgreSQL Testcontainers 實際套用 V1，檢查 schema history、必要欄位與每項必要 CHECK/NOT NULL/唯一限制的違規寫入拒絕，以及遷移失敗時應用不就緒；T014 紅燈須由 Failsafe 報告證明是預期資料庫行為缺失，T015 綠燈須證明同一 PostgreSQL 測試通過。T036-T037 在 US2 重跑既有 `FlywayMigrationIT` 的 V1 限制案例並檢查報告，不建立內容重複的 `LocalFixtureConstraintsIT`；若回歸揭露缺口，新增有序 V2 與針對缺口的升級驗證，測試專用 DB V1→V2 升級與全新 DB V1→V2 兩路徑，保留既有資料及 Flyway history，不清除或重建 DB。Integration tests 不以 H2 代替 PostgreSQL。
- **載入與清除**：T012 先提供可編譯、可呼叫、零寫入且回傳可斷言空結果的 loader 佔位入口；T019/T020 的有效來源案例須因缺少預期資料與載入結果紅燈，非 local/test profile 案例須以有效 fixture、其餘合法設定證明缺少可辨識的 profile 拒絕且零寫入，T022 讓兩者轉綠。成功載入、重複兩次、檔案缺欄/型別錯誤/重複 key/非測試標記時整批拒絕；比對 count 與每欄值。T012 另提供不含 DELETE、只回 `NOT_IMPLEMENTED` 的可呼叫 reset 佔位入口；T038-T040 的 guard 拒絕矩陣包含 `APP_ENV=local`、DB 條件全合法但啟動 profile 非 local/test、合法連線條件但實際 `system_identifier` 不同、預期或實際身分無法讀取／權限不足，以及受管理 Compose／隔離測試容器與 JDBC 目標的對應無法確認；每案須有具體可辨識拒絕原因且零 DELETE，不能以入口不存在或固定 `NOT_IMPLEMENTED` 回應充數。T040 的 POSIX/PowerShell 入口與後端都須從獨立受管理來源取得預期 `system_identifier`，並與待清除 JDBC 連線實際讀值比對；無法取得最小讀取權限時 fail closed。T040 轉綠時仍零 DELETE。允許清除案例須在身分一致及其他 guards 通過後才驗證核准本機條件下只移除測試 rows，所有錯誤 guard 案例確認資料未改變。agent 在執行任何可能刪除資料的測試或命令前，須另取得使用者對命令與目標的明確授權；未獲授權時只保留測試設計與未執行狀態，相關結果標為待驗證。
- **後端**：application/module 測試觀察查詢與冪等結果；MockMvc 驗證路由、輸入、成功 DTO、錯誤與 profile 邊界；PostgreSQL integration 驗證 Flyway、保存/讀取、unique/check constraints 及 transaction rollback。
- **前端**：T011 建立尚未接線的根路由容器及可編譯 typed API client／頁面佔位元件，讓 T023/T024 以 HTTP 測試工具斷言缺少預期 `/api/v1` 請求，T026/T027 以渲染頁面缺少預期標題與逐筆測試標記形成有效紅燈；T025/T028 完成既有入口。T029 在編輯 `frontend/src/app/app.routes.ts` 前，先以 `frontend/src/app/app.routes.spec.ts` 驗證實際根路由 `/` 的繁中提醒、三筆標題和逐筆測試標記，再執行候選 `npm --prefix frontend test -- --watch=false --include=src/app/app.routes.spec.ts` 記錄因尚未接線造成的有效紅燈；接線後重跑同一測試驗綠燈。該命令尚未實際執行，維持「待驗證」。T029 仍須保留 DB/API/瀏覽器及重啟驗收。API client HTTP 測試驗證型別映射、網路錯誤和 Problem Details；Angular component/頁面測試驗證 loading、非空 success、empty、error、retry 與測試標記可見，且不由元件私自發送應用資料 HTTP 呼叫。瀏覽器空集合驗收以瀏覽器對列表 GET 的受控回應提供符合契約的 `data=[]` 與 `meta`，不清除既有資料；記錄攔截方式、回應內容與資料來源，恢復實際請求後另驗三筆成功。此項只證明畫面空狀態，真實 API 載入前的空集合契約由 T016 獨立驗證，受控回應不得稱為資料庫端到端證據。瀏覽器驗收只檢查應用資料請求透過 `/api/v1`，不把頁面靜態資源請求誤判為資料請求。
- **跨端與重啟**：依 [quickstart.md](quickstart.md) 從新 clone/乾淨 local DB 執行，載入、呼叫 API、看繁中頁、停掉並重啟服務；確認資料與欄位完全相同。quickstart 列出的 reset 候選命令不構成資料刪除授權，仍須先完成本計畫的另行明確授權閘門。命令須在後續實作環境逐條實際執行；根目錄 `README.md` 彙整目標 OS、跨端冒煙、重啟與完整驗收，前後端開發規範各自記錄或直接連到對應端的實測命令、報告及結果。未執行者維持「待驗證」。
- **原始證據與補驗**：T058 各保存一次 US3 的測試、lint、build、OpenAPI／HTTP、socket 與瀏覽器狀態原始結果，含命令、單一目標 OS、執行環境、版本、報告位置、觀察及結果，並保留資料刪除的另行授權閘門。T059 逐條核對 T058 與 quickstart，補執行目標 OS 尚未驗證的基線命令；相同程式狀態與目標 OS 的有效證據直接引用，後續修改影響的項目須重驗。T060 保留資料庫／清除驗收；T061 聚焦 T058 尚未證明的窄螢幕、鍵盤及 `:focus-visible` 等瀏覽器細節，對載入、成功、空集合、失敗、重試已有的有效觀察直接引用，缺漏才補驗；T062 保留最終重啟驗收。T059–T062 的引用不能算新的實測或重複計數；未執行、未授權者仍標「待驗證」。
- **命令狀態**：本計畫建立時僅 `setup-plan.sh --json` 已實際執行；應用骨架、build、lint、測試、遷移及冒煙命令均尚無可驗證目標，quickstart 以「候選／待驗證」明示。不得把文件中的命令列為可用基線，亦不得宣稱 SC-006 已通過。
- **平台驗收界線**：SC-006 的完整驗收只依本次明確記錄的單一目標 OS 判定，該 OS 本機基線命令須全部實際成功。T003 須建立 POSIX 與 Windows Maven Wrapper；只要求本次目標 OS 對應的 wrapper 命令實際執行並有報告，其他 OS 的 wrapper 執行結果逐一標「待驗證」，不以未實測平台阻擋目標 OS 的階段判定。對 macOS、Linux、Windows 其餘未實測平台逐一標「待驗證」，不得宣稱跨平台驗收；這不會否定目標 OS 已實測達成的階段結果。計畫、quickstart 或任務中未實際執行的命令均維持候選／待驗證。

## Complexity Tracking

無憲章違規，無需例外或額外架構層。
