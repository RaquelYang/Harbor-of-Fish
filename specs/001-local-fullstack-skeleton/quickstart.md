# Quickstart: 第一階段本機驗收流程

本文件定義骨架完成後應可重現的分段驗收順序。**以下列出的專案命令均為候選命令，尚未在實際骨架執行，狀態均為「待驗證」，不可視為已可用指令。**實作後須依實際生成的 wrapper、script、service 和輸出修訂命令，逐條成功執行後才可標為已驗證；根目錄 `README.md` 彙整跨端與完整驗收，前後端開發規範各自記錄或直接連到端別實測證據。版本決策見 [research.md](research.md)，資料和契約見 [data-model.md](data-model.md) 與 [contracts/openapi.yaml](contracts/openapi.yaml)。

T029 是 US1 的首次端到端切片：驗收列表、三筆成功資料、根路由、DB/API/browser 逐欄一致，以及保留 DB volume 的服務重啟。T029 不包含單筆 endpoint、前端空集合／錯誤／重試、reset 或完整驗收；這些屬於 T030 以後的後續驗收。T013–T015 必須先以有效 TDD 紅燈／綠燈完成 PostgreSQL V1 schema 與必要限制測試，T019–T022 必須先完成完整來源驗證、未知欄拒絕及整檔驗證後單交易寫入測試與實作。V1 一旦套用即不可原地修改；T036–T037 若發現缺口，須新增有序 V2，分別驗證已套用 V1 的專用 DB 升級及全新 DB 依序 V1→V2。不得清除或重建既有 DB 作為遷移修正方式。

## 固定位址與執行隔離

- PostgreSQL：`127.0.0.1:5432`；Compose local DB 使用專用 `harbor_local` database/user 及獨立 named volume。
- Local API：`127.0.0.1:8080`。
- Angular 開發伺服器：`http://localhost:4200`。
- 一般遷移與載入整合測試使用各自的 Testcontainers 隔離 PostgreSQL，不占用或重用 Compose DB。reset 整合測試則使用另外建立的專用 PostgreSQL 容器，固定發布到主機 `127.0.0.1:5432`，以便保留原有 reset host/port/database/user guards；它不能和 Compose DB 或另一個 reset 容器平行占用該 port。
- 進入整合測試階段前，Compose postgres、API、Angular 均須停止，且確認 `127.0.0.1:5432` 未占用。若有占用，先確認程序／容器身分；只可停止本次驗收已知且可確認歸屬的服務。若占用者不明或屬其他專案，停止並回報，不終止、不重用、不改用其他 port，也不放寬 guards。reset 容器遇到固定 port 無法使用時，同樣停止並回報，不平行化該案例。
- 停止 Compose postgres 只釋放 port，不刪除 named volume；之後重啟仍使用原資料、schema 與 Flyway history。不得自動執行 `docker compose down -v`、volume rm、Flyway clean、`DROP` 或 `DELETE` 清理。任何可能執行 DELETE 的驗證或命令，都須事前取得使用者對具體命令與目標的另行明確授權；本機設定、allow-list、Testcontainers 隔離、測試資料標記、reset flag 或確認旗標均不能替代授權。

## 0. 版本與依賴準備

前置條件：feature 實作已完成；Node.js 22.x 且至少 22.12.0、npm、Java 21、Docker Compose v2 可用；Docker daemon 可啟動 PostgreSQL 18.6。精確版本須以實際輸出記錄。

**版本檢查候選命令，待驗證：**

```sh
nvm use
node --version
npm --version
java --version
docker compose version
```

在 repository 根目錄執行 `nvm use`，核對 Node 實際版本符合 `frontend/package.json` 的 `engines.node`（`>=22.12.0 <23`）；若選到較舊 22.x，先安裝符合範圍的 22.x 再檢查。

**依賴準備候選命令，待驗證：**

```sh
cp infra/.env.example infra/.env.local
npm --prefix frontend ci
./mvnw -f backend/pom.xml -DskipTests package
```

`infra/.env.local` 必須明確指定 `APP_ENV=local`、`DB_HOST=127.0.0.1`、`DB_PORT=5432`、`DB_NAME=harbor_local`、`DB_USER=harbor_local`，密碼使用本機自訂值；範例是假值，不可作其他環境密碼。這些命令尚未執行。

## 1. 自動整合測試

開始前確認 Compose postgres、local API 與 Angular 均已停止，並確認 `127.0.0.1:5432` 無占用。先確認占用者；只有可確認為本次已知服務時才停止該服務，不停止其他專案。一般 `*IT.java` 使用各自隔離的 Testcontainers DB；不得連到或重用 Compose DB。固定發布 `127.0.0.1:5432` 的 reset 專用容器只供 reset 整合案例，不得平行執行，也不得因 port 忙碌改埠或略過 guards。

後端測試命名與 Maven 選取方式分開如下：

- Failsafe `*IT.java` 整合測試使用 `-Dit.test=<類別名稱> verify`，例如 T013/T015 的候選命令 `./mvnw -f backend/pom.xml -Dit.test=FlywayMigrationIT verify`、T019/T022 的候選命令 `./mvnw -f backend/pom.xml -Dit.test=FixtureLoadIT verify`。
- Surefire `*Test.java` 測試使用 `-Dtest=<類別名稱> test`，例如列表契約候選命令 `./mvnw -f backend/pom.xml -Dtest=FixtureListContractTest test`。TDD 期間先記錄對應測試的有效 red，再以同一命令記錄 green。
- 以上是 T001–T029 前置／US1 可選取的非清除測試候選命令，均待驗證。實際測試類別尚未建立或執行前不得標成可用或已驗證。
- 自動化整合階段需先完成 T013–T015、T019–T022、T023–T029 涉及的非清除測試。可逐類執行上述選取命令；實際類別與結果尚未產生，持續標示待驗證。
- `./mvnw -f backend/pom.xml verify` 可能執行 T041 的允許清除 DELETE 案例；未先取得使用者對此具體命令及 reset 專用測試目標的另行明確授權，不得執行，也不得以此命令成功與否代替非清除測試證據。

前端與後端品質命令各自記錄，不互相替代。以下候選命令全部待驗證：

```sh
npm --prefix frontend test -- --watch=false
npm --prefix frontend run lint
npm --prefix frontend run build
./mvnw -f backend/pom.xml checkstyle:check
```

`npm test`、`npm lint`、`npm build` 與 backend Checkstyle 是不同驗收證據。Backend `verify` 亦須和 `checkstyle:check` 分開記錄；不得只因單一 Maven lifecycle 成功，就宣稱每個前端命令或 Checkstyle 已執行。

## 2. Compose 與 Flyway／loader

確認自動測試已結束，其 Testcontainers 已釋放 `127.0.0.1:5432`，且 port 無其他占用後，啟動專用 Compose PostgreSQL。**候選命令待驗證：**

```sh
docker compose --env-file infra/.env.local -f infra/compose.yaml up -d postgres
```

確認服務健康，並確認 host port 只發布至 loopback。T029 首次驗收使用全新、專用且空白的 local DB，不可重用其他專案或個人 PostgreSQL 資料目錄。V1 migration 不插入 fixture rows；local API 啟動時 Flyway 套用 `V1__create_local_test_fixture.sql`，migration 失敗時 API 不得就緒。V1 套用後只能透過新增版本遷移升級。

後續 Compose／Flyway、API 與 loader 候選命令仍待驗證：

```sh
set -a
. infra/.env.local
set +a
./mvnw -f backend/pom.xml spring-boot:run -Dspring-boot.run.profiles=local
```

在另一個終端，以同一 local 設定執行 loader：

```sh
set -a
. infra/.env.local
set +a
./scripts/load-local-test-data.sh
```

Loader 須先驗證完整 JSON（恰三筆、欄位型別與必填、長度與 pattern、固定 ID/key 唯一、同一 datasetVersion、`testOnly=true`），全部有效後才在單一交易 canonical upsert。成功輸出版本和筆數，不輸出密碼。T029 只要求載入 canonical 三筆並逐欄驗證；「同一來源載入兩次」及「來源 canonical 值覆寫既有相同 `fixtureKey`」是 T033 以後的新切片。檔案無效時拒絕且零部分寫入沿用 T019 的案例作既有綠燈回歸；除非指出具體尚未涵蓋的邊界，不重複安排相同行為的新紅燈。

## 3. API

API 只在 Flyway 成功後就緒。固定 API 位址為 `http://127.0.0.1:8080`。T029 先驗列表、三筆成功資料與逐欄 DB/API 相符；單筆 endpoint 與 400/404 錯誤屬 T045 以後驗收。

**列表 API 候選命令，待驗證：**

```sh
curl --fail-with-body http://127.0.0.1:8080/api/v1/local-test/fixtures
```

回應應有三筆，list 欄位符合 OpenAPI，records 與 metadata 均有 `testOnly: true`。前端 proxy 使用 `/api` 轉送 API，不連資料庫。API 實際回應、資料庫逐欄對照及 loopback 綁定位址均尚未實測。

## 4. Angular 瀏覽器

**Angular 開發伺服器候選命令，待驗證：**

```sh
npm --prefix frontend start
```

在瀏覽器開 `http://localhost:4200`。T029 僅驗收根路由、固定繁中測試提醒、三筆成功列表、逐欄 DB/API/browser 可見內容及測試標記；需記錄 API 列表和畫面欄位一致。真實 API 載入前空集合契約已屬 T016；T028 已要求成功頁面在窄螢幕基本可讀。單筆 endpoint、前端 loading/empty/error/retry 狀態與詳細鍵盤／焦點驗收依 T030 以後的對應任務進行，不把受控瀏覽器空集合回應算作真實 DB/API 證據。

前端空集合後續可用受控瀏覽器回應驗收：只攔截 `GET /api/v1/local-test/fixtures`，回覆符合契約的 `data=[]`、`meta.testOnly=true`、`meta.datasetVersion=1.0.0`、`meta.count=0`，無須清除 DB。記錄攔截方式、受控回應及資料來源；解除攔截後另確認真實 API 三筆成功。這只證明前端空集合呈現；真實 API 在載入前的空集合契約由 T016 HTTP 測試證明，不能把受控回應當成資料庫端到端證據。API 不可用時不可顯示假成功 fixtures。

## 5. 保留 volume 的服務重啟

記錄列表 API 與 browser 顯示的三筆資料、所有可見欄位及 `testOnly` 標記。停止本次驗收啟動的 API、Angular 與 Compose postgres；停止 Compose postgres 只釋放 `127.0.0.1:5432`，保留 named volume、schema、fixture rows 與 Flyway history。確認 port 由本次流程釋放後，以同一 Compose 設定重啟 postgres，再啟動 API 與 Angular，重讀列表並重新開啟測試頁，逐欄比對重啟前後完全相同。不得使用 `down -v`、volume rm、Flyway clean、`DROP` 或 `DELETE` 清理來達成重啟驗收。所有重啟命令及結果目前待驗證；T029 的此流程與重啟後證據記錄於 `README.md`。

## 另行授權階段：reset 與完整驗收

以下 reset 命令只供參考，尚未實作或執行，狀態為「待驗證」；列出命令不構成執行授權。任何可能觸發 DELETE 的 reset 命令、`ResetLocalFixtureIT` 允許清除案例，以及可能納入該案例的完整 `verify`，都必須先列出具體命令及目標資料庫／測試容器，並取得使用者另行明確授權。未獲授權不得執行或宣稱驗收通過。

reset 預期須保留並同時通過以下所有既有 guards：`APP_ENV=local`、`RESET_LOCAL_TEST_DATA=YES`、`--confirm-local-fixture-delete`、啟動 profile 為 local/test、JDBC host=`127.0.0.1`、port=`5432`、database=`harbor_local`、user=`harbor_local`、連線後 `current_database()`=`harbor_local`，以及 URL／環境設定解析與連線成功。DELETE 前，必須由待清除 JDBC URL 與同組環境變數之外、repository 管理的專用 Compose PostgreSQL 獨立管理通道取得預期 `pg_control_system().system_identifier`；實際 identifier 由待清除 JDBC 連線讀取。整合測試則以明確建立並持有管理資訊的專用隔離 PostgreSQL 容器作預期值來源。必須確認受管理容器與 JDBC 目標確實對應且 identifier 相同；不得從待清除連線或可任意覆寫參數提供預期值。identifier 相同不能取代任何上述 guards，也不能證明本機性。

若預期或實際 identifier 無法取得、讀取權限不足、受管理容器與 JDBC 目標的對應無法確認、identifier 不符，或任何原有 guard 缺漏／不符／解析失敗，必須在任何 DELETE 前以可辨識原因拒絕、非零退出、零 DELETE 並保留所有資料；不得降級只檢查設定或加 bypass。Reset 容器固定使用 `127.0.0.1:5432`，不可平行；port 已占用時先查明占用者，只停止本次已知服務，否則停止驗收，不重用占用者、不改埠、不放寬 guards。完整 verify 若包含此 DELETE 測試，也受相同授權閘門限制。

**Reset 候選命令，待驗證且未授權不得執行：**

```sh
set -a
. infra/.env.local
set +a
APP_ENV=local RESET_LOCAL_TEST_DATA=YES ./scripts/reset-local-test-data.sh --confirm-local-fixture-delete
```

獲得具體授權且全部 guards 通過後，才可驗證只刪除 `local_test_fixture` 中 `test_only=true` rows，schema、Flyway history 及其他 table 不變；之後重載並逐欄確認恢復三筆 canonical rows。這是 reset／後續完整驗收，不屬 T029。本文件任何階段都不得自動執行 `docker compose down -v`、volume rm、Flyway clean、`DROP` 或資料清理 `DELETE`。

## 驗收證據與尚未驗證項目

TDD red/green 應逐個新行為記錄選取測試、失敗斷言及原因，再記錄同一案例轉綠；已通過的 T019 無效來源零部分寫入只記既有綠燈回歸。T029 必須分開保存自動測試、Flyway／資料庫、真實 API、受控瀏覽器（若後續使用）及服務重啟證據。受控瀏覽器空集合只代表 UI 證據，不代表真實 API／DB。不可變 V1 的 PostgreSQL 限制紅綠證據及任何 V2 升級證據需另列。T030 以後的單筆 endpoint、前端 empty/error/retry、reset、lint/build 以外的全量驗收皆依其任務階段完成。

每項候選命令須記錄執行目錄、必要服務、實際版本、命令、報告位置及結果；未執行、未成功或未獲授權的項目一律標示「待驗證」。README 彙整單一目標 OS 的跨端與完整驗收；前後端開發規範各自記錄或直接連到實測證據。不得把文件命令、orchestrator 測試或受控瀏覽器回應宣稱為產品端已驗證。

## 後續冒煙與完整驗收（T057–T064）

T057 建立 `scripts/smoke-local.sh` 後，依 T058 執行並記錄跨端冒煙；本候選命令尚未實作或執行，維持「待驗證」：

```sh
./scripts/smoke-local.sh
```

US2／US3 完成後，再依 T058–T064 驗收單筆 API、錯誤契約、profile 邊界、前端狀態與鍵盤操作、reset、冒煙及重啟；任何可能觸發 DELETE 的命令或測試仍須事先取得對具體命令及目標的另行明確授權。T059–T062 引用相同程式狀態與目標 OS 的既有有效證據，只補缺漏或受修改影響項目，不重複計數。

SC-006 與第一階段完整驗收須以本次明確記錄的單一目標 OS 為準，其全部本機基線命令均須實際成功；README 彙整完整結果，前後端開發規範記錄或直接連到對應端證據。未執行、未成功、未獲授權或受環境阻擋的命令均保留「待驗證」，且不得宣稱該 OS 完整驗收完成。macOS、Linux、Windows 其餘未實測平台逐一標「待驗證」，不宣稱跨平台通過，也不否定已實測目標 OS 的階段結果。
