# Tasks: 第一階段本機前後端骨架

**Input**: [spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/openapi.yaml](contracts/openapi.yaml)、[quickstart.md](quickstart.md)、[八階段開發計畫](../../docs/development-plan.md)與共同、前端、後端開發規範。

**範圍**: 僅八階段交付順序的第一階段；只建立本機／測試用 Angular 21 → `/api/v1` Spring Boot 4.1.1 模組化單體 → PostgreSQL 18 往返。三筆中性固定資料不是產品資料。本清單不安排第二至八階段的資料、地圖、查詢、管理、會員、部署或公開功能。

**命令狀態**: [quickstart.md](quickstart.md) 的安裝、啟動、測試、lint、build、資料庫、冒煙與重啟命令目前全部**待驗證**。以下要求執行命令的任務是未來實作與驗收步驟，不表示本次產生清單時已執行或已通過。實作時若生成工具改變命令，先修正候選命令，再以實際輸出記錄結果。

**TDD 執行規則**: 每個切片依「寫公開行為測試 → 用當時可用的最小測試命令確認因缺少該行為而紅燈 → 最小實作 → 同一測試綠燈 → 必要重構與受影響測試」順序進行。編譯、環境或測試本身錯誤不算有效紅燈。不得先批量寫完所有測試才開始實作；測試以 HTTP、資料庫持久化、命令退出碼及使用者可見畫面為觀察邊界。

**路徑約定**: 後端 Java 根套件採 `org.harboroffish`，本階段只設 `localtest` 模組，內部分 `api`、`application`、`fixture`，不預設其他領域模組。`[P]` 僅表示目標檔案與未完成任務沒有相依，可同時處理；其餘按 ID 順序執行。

## Phase 1: Setup（第一階段共用骨架）

**目標**: 建立可執行工具與本機目錄；版本、命令仍待實際驗證。

- [ ] T001 建立 repository 根目錄 `.nvmrc`，固定 Node 22 線及 22.12 以上最低版本，並在 `frontend/package.json` 使用 Angular 21、TypeScript 5.9.x、CLI 預設 Vitest/jsdom 相容版本。
- [ ] T002 建立 `frontend/angular.json`、`frontend/package-lock.json` 與 `frontend/src/main.ts` 的單一 Angular 工作區，提供 `start`、`test`、`lint`、`build` 腳本；實際 patch 由 lockfile 固定。
- [ ] T003 [P] 建立 repository 根目錄 POSIX `mvnw` 與 Windows `mvnw.cmd`、`.mvn/wrapper/maven-wrapper.properties` 及 `backend/pom.xml`，固定 Maven Wrapper 3.9.11、Java 21、Spring Boot 4.1.1，加入 Web、Validation、Data JDBC、Flyway PostgreSQL、PostgreSQL driver、JUnit/MockMvc/Testcontainers、OpenAPI 3.1 parser/validator 與 Checkstyle 所需依賴；明確設定 Surefire 執行一般測試、Failsafe 將 `**/*IT.java` 納入 `integration-test` 與 `verify` 生命週期，`./mvnw -f backend/pom.xml verify` 與 `./mvnw.cmd -f backend/pom.xml verify` 均須能執行並產生可查核報告。
- [ ] T004 在 `backend/src/main/java/org/harboroffish/HarborOfFishApplication.java` 建立單一 Spring Boot 進入點，並以 `backend/pom.xml` 確認套件掃描只服務此部署單元。
- [ ] T005 [P] 在 `infra/compose.yaml` 建立 PostgreSQL 18.6 `postgres` service、專用 `harbor_local` 資料庫與 healthcheck；host port 只綁 `127.0.0.1:5432`，使用獨立 local volume。
- [ ] T006 在 `infra/.env.example` 放入明確假值與 `APP_ENV=local`、`DB_HOST=127.0.0.1`、`DB_PORT=5432`、`DB_NAME=harbor_local`、`DB_USER=harbor_local`，並在根目錄 `.gitignore` 排除 `infra/.env.local` 與本機秘密。
- [ ] T007 在 `frontend/eslint.config.js` 與 `backend/pom.xml` 設定前端 lint、後端 Checkstyle；不以尚未執行的命令宣稱規則已通過。
- [ ] T008 在 `frontend/proxy.conf.json` 與 `frontend/angular.json` 設定開發期間只代理 `/api` 至本機 API；前端設定不得含資料庫連線或密碼。

## Phase 2: Foundational（阻擋所有故事的設定與測試底座）

**目標**: 建立 local/test 邊界與可運行的測試環境；不在此階段偷做故事功能。

- [ ] T009 在 `backend/src/main/resources/application.yaml`、`application-local.yaml` 與 `application-test.yaml` 建立環境變數驅動的資料庫、Flyway、local/test profile 設定；local/test API server 明確只監聽 `127.0.0.1` 或作業系統等價的 loopback 位址，不得綁定 `0.0.0.0` 或外部介面；缺少必要設定時指出設定種類但遮蔽值，且非 local/test profile 不啟用 fixture 操作。
- [ ] T010 在 `backend/src/test/java/org/harboroffish/support/PostgresIntegrationTest.java` 建立 PostgreSQL 18 Testcontainers 測試底座，讓後續遷移與持久化測試使用真實 PostgreSQL，不以 H2 代替。
- [ ] T011 在 `frontend/src/app/app.config.ts`、`frontend/src/app/app.routes.ts` 與 `frontend/src/app/app.ts` 建立 Angular 啟動與本機測試頁路由容器，HTTP provider 只供集中 API client 使用。
- [ ] T012 在 `backend/src/main/java/org/harboroffish/localtest/` 建立 `api`、`application`、`fixture` 套件邊界；HTTP 只轉換契約、application 協調使用案例／交易、fixture 封裝資料存取，DTO 不直接使用持久化實體。

## Phase 3: US1 啟動並查看本機測試流程（P1，MVP）

**Goal**: 空白本機 DB 套用 V1，載入三筆中性 fixture；繁中測試頁經 typed API client 顯示資料與固定「僅供測試」提醒，重啟後內容不變。

**Independent Test**: 在獨立空白 PostgreSQL 18 上啟動 local API，先驗證完整來源拒絕矩陣及無效檔零寫入，再載入三筆 canonical 來源、呼叫列表並打開測試頁；確認三筆固定欄位、資料與 metadata 的 `testOnly=true`，重啟 API／前端後逐欄相同。US2 另驗收相同來源冪等 upsert 與 reset guards。

- [ ] T013 [US1] 先在 `backend/src/test/java/org/harboroffish/localtest/fixture/FlywayMigrationIT.java` 寫空白 PostgreSQL 啟動會套用 V1、建立 `local_test_fixture` 與 schema history，以及失敗遷移不得就緒的測試。
- [ ] T014 [US1] 以 `./mvnw -f backend/pom.xml -Dit.test=FlywayMigrationIT verify` 選取並執行 T013，確認缺遷移案例有效紅燈；先排除阻擋 Surefire 的其他失敗，並確認 Failsafe `integration-test`/`verify` 報告列出該測試及執行數，記錄實際命令、報告位置與結果於實作紀錄（尚未實測前維持待驗證）。
- [ ] T015 [US1] 在 `backend/src/main/resources/db/migration/V1__create_local_test_fixture.sql` 建表：`id uuid` 主鍵、唯一 `fixture_key varchar(64)`、`title varchar(100)`、`description varchar(500)`、`dataset_version varchar(16)`、`test_only boolean`；加入 NOT NULL、key/version pattern、非空文字與 `test_only=true` CHECK，不插入 fixture rows；以 `./mvnw -f backend/pom.xml -Dit.test=FlywayMigrationIT verify` 重跑 T013 轉綠。
- [ ] T016 [US1] 先在 `backend/src/test/java/org/harboroffish/localtest/api/FixtureListContractTest.java` 寫載入前 `GET /api/v1/local-test/fixtures` 回 200、`application/json`、`data=[]`、`meta.testOnly=true`、`meta.datasetVersion=1.0.0`、`meta.count=0` 的 HTTP 契約測試；測試須解析 `contracts/openapi.yaml` 為 OpenAPI 3.1，依 schema 核對路徑成功回應的狀態碼、content type、必要欄位、型別及 envelope 欄位。
- [ ] T017 [US1] 執行 `./mvnw -f backend/pom.xml -Dtest=FixtureListContractTest test` 並確認因列表行為未實作而有效紅燈；記錄實際選取的測試數與失敗原因，編譯或環境失敗不算有效紅燈，命令尚未實測前維持待驗證。
- [ ] T018 [US1] 在 `backend/src/main/java/org/harboroffish/localtest/fixture/LocalTestFixtureRepository.java`、`application/ListLocalTestFixtures.java`、`api/LocalTestFixtureController.java` 與 `api/FixtureResponse.java` 實作唯讀列表與分離 DTO，僅 local/test profile 註冊路由；依 OpenAPI 回 `data`/`meta`，以 `./mvnw -f backend/pom.xml -Dtest=FixtureListContractTest test` 重跑 T016 轉綠。
- [ ] T019 [US1] 在 `backend/src/test/java/org/harboroffish/localtest/fixture/FixtureLoadIT.java` 先寫 PostgreSQL 整合測試，使用測試內建立的 JSON 案例（不依賴 T021 尚未建立的 canonical 檔案）驗證：根物件只含 `datasetVersion` 與 `fixtures`，且 `fixtures` 為陣列；每個 row 只含 `id`、`fixtureKey`、`title`、`description`、`datasetVersion`、`testOnly`，不得有未知欄位；逐欄斷言型別、trim 規則（`title` 修剪前後不可有差異）、非空值、長度及 key/version pattern；恰三筆、UUID/key 唯一、根與 row 版本一致且符合 `1.0.0`、每筆 `testOnly=true`。任何無效 row 必須在任何寫入前拒絕。另驗證有效來源載入後經 SQL 與列表 HTTP 逐欄讀回固定 UUID、key、title、description、`datasetVersion=1.0.0`、`testOnly=true`，以及完整驗證先於單一交易、失敗時零部分寫入；上述驗證和原子寫入須先於 T029 首次端到端驗收。
- [ ] T020 [US1] 以 `./mvnw -f backend/pom.xml -Dit.test=FixtureLoadIT verify` 選取 T019 整合測試並確認缺少完整來源驗證或載入/交易行為時有效紅燈；記錄實際命令、Failsafe 報告位置、測試名稱/執行數與失敗原因，編譯或環境失敗不算有效紅燈，命令尚未實測前不得標示已驗證。
- [ ] T021 [US1] 在 `backend/src/main/resources/local-test-fixtures.v1.json` 建立恰三筆 UTF-8 中性資料：固定 UUID `00000000-0000-4000-8000-000000000001` 至 `00000000-0000-4000-8000-000000000003`、`sample-one/two/three`、對應「本機測試樣本一/二/三」、每筆說明含「僅供本機測試，非真實產品資料」、全檔 `datasetVersion=1.0.0`、每筆 `testOnly=true`；確認此 canonical 檔案符合 T019 完整驗證條件。
- [ ] T022 [US1] 在 `backend/src/main/java/org/harboroffish/localtest/fixture/FixtureSourceValidator.java`、`application/LoadLocalTestFixtures.java` 與 `scripts/load-local-test-data.sh`、`scripts/load-local-test-data.ps1` 實作 local/test 專用載入：先讀取並完整驗證整份 JSON（根物件、允許欄位、型別、trim/長度/pattern、恰三筆、UUID/key 唯一、版本一致、`testOnly=true`、未知欄拒絕），全部有效後才以單一交易寫入，並回報版本與筆數、不輸出秘密。PowerShell 與 POSIX 入口必須呼叫相同後端驗證及載入流程，不得另行略過檢查；以 `./mvnw -f backend/pom.xml -Dit.test=FixtureLoadIT verify` 重跑 T019，確認無效檔零寫入及有效檔逐欄載入皆轉綠。
- [ ] T023 [US1] 先在 `frontend/src/app/core/api/local-test-fixtures.api.spec.ts` 寫 HTTP 測試，要求 client 只呼叫 `/api/v1/local-test/fixtures`、把 `data` 與 `meta` 保持為 OpenAPI 對應型別，且不連資料庫。
- [ ] T024 [US1] 執行 `npm --prefix frontend test -- --watch=false --include=src/app/core/api/local-test-fixtures.api.spec.ts` 選取對應測試並確認因 typed API client 缺失而有效紅燈；記錄實際選取數與失敗原因，命令尚未實測前維持待驗證。
- [ ] T025 [US1] 在 `frontend/src/app/core/api/local-test-fixtures.api.ts` 建立單一具型別 HTTP 邊界與 `Fixture`、list response 型別，頁面不得直接呼叫 HttpClient；以 `npm --prefix frontend test -- --watch=false --include=src/app/core/api/local-test-fixtures.api.spec.ts` 重跑 T023 轉綠。
- [ ] T026 [US1] 先在 `frontend/src/app/features/local-test/local-test.page.spec.ts` 寫由 API 成功回傳三筆時，繁中頁面顯示固定測試提醒、三個標題與每筆測試標記的可見行為測試。
- [ ] T027 [US1] 執行 `npm --prefix frontend test -- --watch=false --include=src/app/features/local-test/local-test.page.spec.ts` 選取對應測試並確認因頁面行為缺失而有效紅燈；記錄實際選取數與失敗原因，命令尚未實測前維持待驗證。
- [ ] T028 [US1] 在 `frontend/src/app/features/local-test/local-test.page.ts` 與 `.html` 實作測試頁，固定顯示「僅供本機測試，非真實漁港、魚種、漁季、價格或限制資料」，以頁面持有狀態讀取 typed client、顯示三筆資料；窄螢幕可讀且標籤清楚，以 `npm --prefix frontend test -- --watch=false --include=src/app/features/local-test/local-test.page.spec.ts` 重跑 T026 轉綠。
- [ ] T029 [US1] 僅在 T019-T022 的完整來源驗證、未知欄拒絕、先驗證整檔再單交易寫入測試與實作均通過後，才在 `frontend/src/app/app.routes.ts` 接上測試頁並依 `specs/001-local-fullstack-skeleton/quickstart.md` 的待驗證流程以全新本機 DB 驗證「DB → Flyway → local API → loader → Angular 頁面」；記錄首次結果與重啟後三筆 API 可見欄位逐欄相同於 `README.md`，前置項目或流程失敗時維持待驗證。

## Phase 4: US2 重複載入並安全重設測試資料（P2）

**Goal**: 嚴格驗證整份來源、交易式 canonical upsert、兩次載入相同、明確 allow-list 下只刪本機測試 rows。

**Independent Test**: 連續載入兩次比較三筆所有 API 可見欄位；缺欄、錯型別、未知欄、重複 ID/key、版本不一致、`testOnly=false` 均拒絕且零部分寫入；拒絕條件下清除命令非零退出且資料不變，通過條件下僅測試 rows 被清除並可重載。

- [ ] T030 [US2] 擴充 `backend/src/test/java/org/harboroffish/localtest/fixture/FixtureSourceValidationTest.java` 的資料驅動回歸矩陣，依 [data-model.md](data-model.md) 精確欄位、trim 規則、長度及 pattern 覆蓋缺欄、未知欄、錯型別、空白/超長值、非法 key/version、重複 UUID/key、版本不一致、非三筆及 `testOnly=false`；這些 T019 已涵蓋的驗證不得假設在 US2 再次故意失敗。
- [ ] T031 [US2] 執行 `./mvnw -f backend/pom.xml -Dtest=FixtureSourceValidationTest test` 及 `./mvnw -f backend/pom.xml -Dit.test=FixtureLoadIT verify`，確認 T030 完整回歸矩陣與 T019 PostgreSQL 驗證/原子載入測試通過；記錄 Surefire/Failsafe 實際選取數及結果，尚未實測前維持待驗證。只有新增回歸案例揭露缺陷才修正，不能把已在 US1 完成的驗證功能當成本切片必須再次紅燈的行為。
- [ ] T032 [US2] 檢查 `FixtureSourceValidator.java` 的規則與整檔驗證先於交易之邊界，修正 T030/T031 實際揭露的回歸缺陷並重跑回歸測試；若無缺陷，只記錄通過證據，不重複安排或假設首次驗證功能尚未實作。US2 後續工作專注於下列載入冪等性與清除 guards。
- [ ] T033 [US2] 先在 `backend/src/test/java/org/harboroffish/localtest/fixture/FixtureLoadIT.java` 加入無效檔零部分寫入、相同來源載入兩次無重複、來源 canonical 值覆寫既有相同 `fixtureKey` 與全部欄位比對案例。
- [ ] T034 [US2] 執行 `./mvnw -f backend/pom.xml -Dit.test=FixtureLoadIT verify` 選取新增整合案例，確認因冪等／canonical upsert 語意缺失而有效紅燈；不得將 US1 已完成且通過的完整來源驗證或原子寫入當成此處必須再紅燈的原因。記錄實際 Failsafe 報告、選取數與結果，命令尚未實測前維持待驗證。
- [ ] T035 [US2] 在 `backend/src/main/java/org/harboroffish/localtest/application/LoadLocalTestFixtures.java` 與 `fixture/LocalTestFixtureRepository.java` 完成以 `fixture_key` 唯一鍵的單交易 `INSERT ... ON CONFLICT DO UPDATE`，對齊固定 `id/title/description/dataset_version/test_only`，提交前確認恰三筆與來源逐欄相等；以 `./mvnw -f backend/pom.xml -Dit.test=FixtureLoadIT verify` 重跑 T033 轉綠。
- [ ] T036 [US2] 先在 `backend/src/test/java/org/harboroffish/localtest/fixture/LocalFixtureConstraintsIT.java` 寫 PostgreSQL 真實持久化測試，驗證 UUID/key 唯一、必要欄位、key/version pattern、非空文字與 `test_only=true` 限制確實拒絕非法列。
- [ ] T037 [US2] 執行 `./mvnw -f backend/pom.xml -Dit.test=LocalFixtureConstraintsIT verify`；若發現預期限制失敗，僅在 `backend/src/main/resources/db/migration/V1__create_local_test_fixture.sql` 修正尚未發布的初始 V1，直到 T036 轉綠；記錄 Failsafe 報告、實際執行數與結果，尚未實測前維持待驗證。
- [ ] T038 [US2] 先在 `backend/src/test/java/org/harboroffish/localtest/application/ResetLocalFixtureIT.java` 寫清除拒絕矩陣：缺少或非 `APP_ENV=local`、缺少或非 `RESET_LOCAL_TEST_DATA=YES`、缺 `--confirm-local-fixture-delete`、host 非 `127.0.0.1`、port 非 `5432`、DB 名或登入 user 非 `harbor_local`、實際 `current_database()` 不符、URL/環境解析失敗或連線失敗，全部須在 DELETE 前非零退出且資料未變。
- [ ] T039 [US2] 以 `./mvnw -f backend/pom.xml -Dit.test=ResetLocalFixtureIT verify` 選取 T038 拒絕案例，確認缺少 fail-closed 保護時有效紅燈；記錄 Failsafe 報告、實際執行數及失敗原因，命令尚未實測前維持待驗證。
- [ ] T040 [US2] 在 `scripts/reset-local-test-data.sh`、`scripts/reset-local-test-data.ps1` 與 `backend/src/main/java/org/harboroffish/localtest/application/ResetLocalTestFixtures.java` 建立明確確認旗標及雙重防護：POSIX/PowerShell 入口與後端均檢查相同 env、JDBC host/port/database/user 及連線後 `current_database()`；任何缺漏、不符或解析失敗先退出，禁止 Flyway clean、DROP DATABASE 或通用清空；PowerShell 只呼叫同一受保護後端流程，不可略過 guards；以 `./mvnw -f backend/pom.xml -Dit.test=ResetLocalFixtureIT verify` 重跑 T038 轉綠。
- [ ] T041 [US2] 先在 `backend/src/test/java/org/harboroffish/localtest/application/ResetLocalFixtureIT.java` 寫通過 allow-list 時僅以交易刪 `local_test_fixture` 中 `test_only=true` rows、驗證刪除筆數、保留 schema/`flyway_schema_history`/其他表，重載後恢復相同三筆的案例。
- [ ] T042 [US2] 以 `./mvnw -f backend/pom.xml -Dit.test=ResetLocalFixtureIT verify` 選取 T041 允許清除案例，確認缺少限定刪除或交易結果驗證而有效紅燈；記錄 Failsafe 報告、實際執行數及失敗原因，命令尚未實測前維持待驗證。
- [ ] T043 [US2] 在 `backend/src/main/java/org/harboroffish/localtest/application/ResetLocalTestFixtures.java` 實作通過保護後的限定 DELETE 與筆數檢查，`scripts/reset-local-test-data.sh` 與 `.ps1` 只作受保護入口；以 `./mvnw -f backend/pom.xml -Dit.test=ResetLocalFixtureIT verify` 重跑 T041 轉綠。
- [ ] T044 [US2] 在 `README.md` 記錄 fixture 格式、六欄規則、三筆固定 ID/key、載入與重載、清除命令的所有 allow-list 條件及拒絕效果；命令尚未實際通過者標「待驗證」，並檢查 `backend/src/main/resources/local-test-fixtures.v1.json`、`infra/.env.example` 不含真實個資、秘密或未授權內容。

## Phase 5: US3 確認錯誤狀態與各端驗收命令（P3）

**Goal**: 完整 OpenAPI list/get 成功與錯誤、profile 隔離、前端 loading/success/empty/error/retry、各端與跨端可重現驗收。

**Independent Test**: local/test 下以 HTTP 驗證 list、item、400、404、500 Problem Details；其他 profile 無路由且不能載入／清除；API 可用、空集與不可用時頁面分別顯示對應狀態；逐條執行記錄的本機命令，重啟後結果一致。

- [ ] T045 [US3] 先在 `backend/src/test/java/org/harboroffish/localtest/api/FixtureItemContractTest.java` 寫 `GET /api/v1/local-test/fixtures/{fixtureKey}` 的 200 item envelope、合法不存在 key 的 404 `FIXTURE_NOT_FOUND`、非法 key 的 400 `INVALID_FIXTURE_KEY` 與 `errors[]` 測試；解析 `contracts/openapi.yaml` 為 OpenAPI 3.1，逐項比對各狀態碼、content type、必要欄位、欄位型別及成功/Problem Details schema，並驗證實際 HTTP 回應符合該 schema。
- [ ] T046 [US3] 執行 `./mvnw -f backend/pom.xml -Dtest=FixtureItemContractTest test` 選取對應測試，確認因 item 路由／驗證／錯誤尚缺而有效紅燈；記錄實際選取數與失敗原因，編譯或環境失敗不算有效紅燈，命令尚未實測前維持待驗證。
- [ ] T047 [US3] 在 `backend/src/main/java/org/harboroffish/localtest/api/LocalTestFixtureController.java` 與 `api/LocalTestProblemHandler.java` 實作單筆查詢、`fixtureKey` pattern 驗證及 RFC 9457 `application/problem+json`，含穩定 `code` 與安全繁中欄位錯誤；以 `./mvnw -f backend/pom.xml -Dtest=FixtureItemContractTest test` 重跑 T045 轉綠。
- [ ] T048 [US3] 先在 `backend/src/test/java/org/harboroffish/localtest/api/FixtureErrorAndProfileTest.java` 寫 list 與 item 路徑在資料庫／服務錯誤時均回 500 `INTERNAL_ERROR`、`application/problem+json` 且不洩漏 stack、SQL、憑證或內部 host 的契約測試；並驗證錯誤回應符合解析後 OpenAPI 3.1 Problem Details schema，以及非 local/test profile 沒有兩條 fixture 路由並拒絕 loader/reset。
- [ ] T049 [US3] 執行 `./mvnw -f backend/pom.xml -Dtest=FixtureErrorAndProfileTest test` 選取對應測試，確認安全錯誤或 profile 邊界未完成而有效紅燈；記錄實際選取數與失敗原因，命令尚未實測前維持待驗證。
- [ ] T050 [US3] 在 `backend/src/main/java/org/harboroffish/localtest/api/LocalTestProblemHandler.java`、`application/LoadLocalTestFixtures.java` 與 `application/ResetLocalTestFixtures.java` 收束 500 安全錯誤映射及非 local/test 拒絕；API DTO 不暴露 entity，以 `./mvnw -f backend/pom.xml -Dtest=FixtureErrorAndProfileTest test` 重跑 T048 轉綠。
- [ ] T051 [US3] 先在 `frontend/src/app/core/api/local-test-fixtures.api.spec.ts` 加入網路錯誤、非成功 HTTP 與 RFC 9457 Problem Details 的 client 可觀察結果測試。
- [ ] T052 [US3] 執行 `npm --prefix frontend test -- --watch=false --include=src/app/core/api/local-test-fixtures.api.spec.ts` 新增案例，確認因錯誤映射缺失而有效紅燈；記錄實際選取數及失敗原因，命令尚未實測前維持待驗證。
- [ ] T053 [US3] 在 `frontend/src/app/core/api/local-test-fixtures.api.ts` 完成錯誤映射，不把失敗轉成假成功 fixture 或空集合；以 `npm --prefix frontend test -- --watch=false --include=src/app/core/api/local-test-fixtures.api.spec.ts` 重跑 T051 轉綠。
- [ ] T054 [US3] 先在 `frontend/src/app/features/local-test/local-test.page.spec.ts` 加入 loading、空集合、API 不可用／失敗、重試恢復、每種狀態固定測試提醒及鍵盤可操作的使用者可見測試。
- [ ] T055 [US3] 執行 `npm --prefix frontend test -- --watch=false --include=src/app/features/local-test/local-test.page.spec.ts` 新增案例，確認因缺少狀態／重試行為而有效紅燈；記錄實際選取數及失敗原因，命令尚未實測前維持待驗證。
- [ ] T056 [US3] 在 `frontend/src/app/features/local-test/local-test.page.ts` 與 `.html` 實作頁面擁有的 `loading | success | empty | error` 狀態與重試，失敗時清除舊成功資料、顯示易懂訊息，所有狀態保留固定「僅供測試」提醒；以 `npm --prefix frontend test -- --watch=false --include=src/app/features/local-test/local-test.page.spec.ts` 重跑 T054 轉綠。
- [ ] T057 [US3] 在 `scripts/smoke-local.sh` 與 `scripts/smoke-local.ps1` 建立 local-only 冒煙入口，檢查 `/api/v1/local-test/fixtures` 三筆、單筆路徑、`testOnly`、版本與欄位內容；兩入口只呼叫同一 API 並檢查 HTTP 位址確為 loopback，不以 `localhost` URL 推斷網路監聽綁定；以 T016、T045 契約測試作為先行依據，實際執行與結果留待 T058，不以 curl 成功取代前端畫面驗收。
- [ ] T058 [US3] 依 `specs/001-local-fullstack-skeleton/quickstart.md` 實際核對並執行前端 test/lint/build、`./mvnw -f backend/pom.xml verify`、Checkstyle、OpenAPI 3.1 契約、空白 DB Flyway 啟動與本機 HTTP 冒煙。OpenAPI 檢查須執行可解析 `contracts/openapi.yaml` 的 3.1 parser/validator，並以 `FixtureListContractTest`、`FixtureItemContractTest`、`FixtureErrorAndProfileTest` 實際請求兩條路徑，逐項比對成功與錯誤狀態碼、回應 content type、必要欄位與 schema（含 list/item envelope 及 Problem Details）；執行命令至少包含 `./mvnw -f backend/pom.xml -Dtest=FixtureListContractTest,FixtureItemContractTest,FixtureErrorAndProfileTest test` 與 `./mvnw -f backend/pom.xml verify`，單純 curl 得到 200 不構成契約驗證。查核 Surefire 與 Failsafe 報告檔，記錄 `*IT.java` 實際執行測試名稱/數量及成功失敗數；Maven 命令成功但報告未證明 IT 有執行，不得宣稱 SC-003。另以作業系統 socket/process 實際檢查 API 監聽位址為 `127.0.0.1` 或等價 loopback，將檢查命令與觀察到的綁定位址記錄於 `README.md`，不得以 profile 名稱或 `localhost` URL 代替。每項均在 `README.md` 記錄執行目錄、必要服務、版本、實際命令、報告位置、測試數與結果，未成功者保留「待驗證」。

## Phase 6: Cross-cutting polish 與第一階段內部驗收

**目標**: 核對範圍、文件與完整重現證據；不得把本階段驗收當作首次公開。

- [ ] T059 在 `README.md` 依實際結果記錄 Node/Java/Docker/PostgreSQL 版本、安裝與啟動順序、`infra/.env.local` 假值範例用法、DB 與 API 的實際 loopback 監聽位址及檢查命令，並核對 `specs/001-local-fullstack-skeleton/quickstart.md` 的候選命令；在 Windows PowerShell 實測適用的 Node/Java/Docker 先決條件安裝或版本檢查、Maven Wrapper 首次下載/啟動、測試、載入、清除拒絕與允許、冒煙及完整驗收命令，確認其使用相同來源驗證與 reset guards；逐項記錄實際命令和結果。若無 Windows 環境或任何命令未實際執行，清楚標「待驗證」，不可宣稱 Windows/跨平台已驗收；只將實際成功者標已驗證。
- [ ] T060 在 `README.md` 記錄全新專用 DB 的完整驗收：Flyway history、載入兩次逐欄一致、清除拒絕矩陣與允許清除、重新載入，以及 local/test 外路由／loader/reset 不可用的實際結果。
- [ ] T061 在 `README.md` 記錄繁中測試頁的瀏覽器驗收：窄螢幕、鍵盤、載入／三筆成功／空集合／API 失敗／重試、瀏覽器只呼叫 API 而不連資料庫；無實際觀察的項目保留待驗證。
- [ ] T062 在 `README.md` 記錄停止並重啟 API 與前端後，列表與畫面再次顯示相同三筆、全部欄位及標記一致的結果；若任何命令或重啟情境受環境限制，明列限制，不能宣稱 SC-006 或第一階段完整通過。
- [ ] T063 核對 `backend/src/main/resources/local-test-fixtures.v1.json`、`infra/.env.example`、`frontend/src/app/features/local-test/local-test.page.html` 與 `README.md`：只有中性假資料與明確測試標記，沒有真實領域資料、地圖／管理／公開入口、個資、秘密或未授權來源內容。
- [ ] T064 依 `specs/001-local-fullstack-skeleton/spec.md` 的 FR-001～FR-016、SC-001～SC-006 與 `docs/development-plan.md` 第一階段逐項比對 `README.md` 的實際證據；未驗證項目維持未完成，不安排第二至八階段功能或首次公開。

## Dependencies & Execution Order

- **Setup → Foundational → US1 → US2 → US3 → Cross-cutting polish**。US1 先建立可觀察的端到端往返，US2 在同一 fixture 上加強載入與清除，US3 完成錯誤與各端驗收；不得把後續故事的未完成測試算作前一故事已通過。
- **每個 TDD/回歸切片**：US1 為 T013→T014→T015、T016→T017→T018、T019→T020→T021→T022、T023→T024→T025、T026→T027→T028；一般 `*Test.java` 使用 Surefire 的 `-Dtest=<測試類> test` 選擇器，`*IT.java` 使用 Failsafe 的 `-Dit.test=<測試類> verify` 選擇器；IT 的有效紅綠須由 Failsafe 報告及實際執行數佐證，避免把編譯/環境錯誤當紅燈。US2 的 T030→T031→T032 是 US1 完整驗證功能的綠燈回歸檢查，不要求相同行為再次紅燈；T033→T034→T035 專注載入冪等性/canonical upsert，T038→T039→T040、T041→T042→T043 為 reset 拒絕及允許清除切片，T036→T037 為 V1 限制回歸檢查；US3 為 T045→T046→T047、T048→T049→T050、T051→T052→T053、T054→T055→T056。每個新增行為切片依紅燈、最小實作、綠燈；已完成行為的回歸切片記錄實際通過結果。
- **資料順序**：空白 DB → V1 migration/validate → local API 啟動 → 完整 JSON 驗證 → 單交易載入 → API／頁面讀取。清除只在全部 allow-list 條件通過後執行，保留 schema 與 Flyway history。
- **首次載入前置**：T019/T020/T022 在任何 US1 首次端到端寫入前完成並證明整份 fixture 通過完整 schema/欄位/型別/trim/長度/pattern/筆數/唯一性/版本/標記驗證；完整驗證成功後才允許一筆交易寫入。US2 不重複把這項既有行為列作預期紅燈，僅作綠燈回歸；其新增紅燈留給冪等 upsert 與 reset guards。
- **故事完成點**：US1 見 T029；US2 見 T044；US3 見 T058。T059～T064 是第一階段完整驗收，依所有三個故事完成後才執行。

### 可平行的工作例子

- T003 的 Maven Wrapper／後端依賴與 T005 的 Compose 可在 T001～T002 進行時分檔處理；T007 的 lint 設定須等對應專案腳本存在。
- 完成 Phase 2 後，可分檔準備 US1 的 Flyway 測試檔 T013 與前端 typed client 測試檔 T023，但實際紅燈、最小實作與綠燈仍依上列切片順序執行。
- US2 的資料來源驗證測試 T030 與清除拒絕矩陣 T038 使用不同測試檔，可分工撰寫；不得跳過各自的紅燈確認或提前執行清除。

## Implementation Strategy

1. 先完成 Setup、Foundational 與 US1 MVP；用空白本機資料庫、API 與瀏覽器獨立驗收資料往返。
2. 完成 US2，讓載入可重跑、無效檔零部分寫入，且清除在所有不符條件下拒絕。
3. 完成 US3 與跨端重啟驗收；只有實際成功的命令可記為已驗證。此 feature 到第一階段內部驗收為止。
