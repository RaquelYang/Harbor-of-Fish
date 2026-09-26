# Quickstart: 第一階段本機驗收流程

本文件定義骨架完成後應可重現的驗收順序。**以下全是計畫中的候選命令，尚未在實際骨架執行，狀態均為「待驗證」，目前不可視為已可用的專案指令。**實作後須依產生的 wrapper、script、service 和實際輸出修訂命令，逐條成功執行後才可標為已驗證；根目錄 `README.md` 彙整跨端與完整驗收，前後端開發規範各自記錄或直接連到對應端的實測證據。版本決策見 [research.md](research.md)，資料和契約見 [data-model.md](data-model.md) 與 [contracts/openapi.yaml](contracts/openapi.yaml)。

T029 首次以本機 DB 驗收前，必須先完成 T013-T015 的 PostgreSQL V1 schema 與必要限制測試，並記錄有效紅燈及綠燈證據。V1 一旦套用即不可原地修改；若後續 T036-T037 回歸發現缺口，新增有序 V2，分別驗證已套用 V1 的專用 DB 升級，以及全新 DB 依序 V1→V2。不得清除或重建既有 DB 作為遷移修正方式。

## Prerequisites

- Git checkout 處於 feature 實作完成狀態。
- Node.js 22.x 且最低 22.12.0 / npm、Java 21、Docker Compose v2 可用；`.nvmrc` 選擇 22 線，`frontend/package.json` 的 `engines.node` 限定 `>=22.12.0 <23`；精確版本待實作後實測。
- Docker daemon 可啟動 PostgreSQL 18.6 容器。
- 不需真實憑證、第三方 API、外部資料來源或網路產品環境。

Candidate version checks — **待驗證**：

```sh
nvm use
node --version
npm --version
java --version
docker compose version
```

於 repository 根目錄執行 `nvm use` 後，核對 `node --version` 的實際版本符合 `frontend/package.json` 的 `engines.node`；若選到低於 22.12.0 的 22.x，先安裝符合範圍的 22.x 再檢查。以上版本檢查尚未執行。

## Clean local acceptance

依序操作，任何一步失敗即停止並記錄環境、命令和錯誤；不要略過 Flyway、欄位驗證或環境清除 guard。

### 1. Install dependencies

預期先複製假值範例成不納入版控的 `infra/.env.local`，再安裝依賴。**以下命令待驗證**：

```sh
cp infra/.env.example infra/.env.local
npm --prefix frontend ci
./mvnw -f backend/pom.xml -DskipTests package
```

`infra/.env.local` 必須明確指定 `APP_ENV=local`、`DB_HOST=127.0.0.1`、`DB_PORT=5432`、`DB_NAME=harbor_local`、`DB_USER=harbor_local`，密碼使用本機自訂值；範例值是假值，不能作其他環境密碼。套件安裝及包裝結果均待驗證。

### 2. Start an empty local database

**待驗證候選命令**：

```sh
docker compose --env-file infra/.env.local -f infra/compose.yaml up -d postgres
```

確認容器健康且只發佈 loopback port。T029 首次驗收使用全新、專用且空白的本機資料庫；不可重用其他專案或個人 PostgreSQL 資料目錄。部署/服務名稱、healthcheck 與 volume 行為待實作後驗證。V1 已套用的 DB 後續只能透過新增版本遷移升級，不可用清除或重建取代升級測試。

### 3. Apply migration and load fixed data

後端 local profile 啟動時先由 Flyway 套用 `V1__create_local_test_fixture.sql`；migration 失敗時 API 不得就緒。啟動 API 及執行完整驗證後才寫入 fixture。**待驗證候選命令**：

```sh
set -a
. infra/.env.local
set +a
./mvnw -f backend/pom.xml spring-boot:run -Dspring-boot.run.profiles=local
```

在另一個終端，以相同 local 設定執行 loader。**待驗證候選命令**：

```sh
set -a
. infra/.env.local
set +a
./scripts/load-local-test-data.sh
```

Loader 先檢查完整 JSON（恰三筆、欄位型別與必填、長度與 pattern、固定 ID/key 唯一、同一 datasetVersion、`testOnly=true`），完整有效才在單一交易 canonical upsert。成功輸出版本和筆數，不輸出密碼。對同一來源再執行一次並比較筆數及每個欄位值：期望仍是三筆且完全一致。檔案無效的拒絕和零部分寫入由自動測試驗證。

### 4. Verify API and front end

**待驗證候選命令**：

```sh
curl --fail-with-body http://127.0.0.1:8080/api/v1/local-test/fixtures
curl --fail-with-body http://127.0.0.1:8080/api/v1/local-test/fixtures/sample-one
npm --prefix frontend start
```

列表回應應有三筆，item/list 欄位符合 OpenAPI，所有 records 與 metadata 都有 `testOnly: true`。有效但不存在 key 預期為 404 `FIXTURE_NOT_FOUND`；格式無效 key 預期為 400 `INVALID_FIXTURE_KEY` 和欄位錯誤；任何 error body 都不能有 stack trace、SQL、secret 或內部 hostname。用 local profile 以外設定呼叫時，預期 endpoint 不存在/不可用。前端以 `/api` proxy 連到 API，不連資料庫。

在瀏覽器開 `http://localhost:4200`（port 待 Angular CLI 確認）檢查繁體中文測試頁：固定可見「僅供本機測試，非真實漁港、魚種、漁季、價格或限制資料」；分別確認 loading、三筆成功、空集合、API unavailable/error、retry 狀態及鍵盤可操作性。空集合畫面以瀏覽器僅攔截 `GET /api/v1/local-test/fixtures` 並回覆符合契約的 `data=[]`、`meta.testOnly=true`、`meta.datasetVersion=1.0.0`、`meta.count=0` 驗收，無須清除既有 DB 資料；記錄攔截方式、受控回應內容及測試資料來源，解除攔截後再確認真實 API 的三筆成功畫面。此受控回應只證明前端空狀態，真實 API 的空集合契約由 T016 的 HTTP 測試另證，不得宣稱此步驟已驗證資料庫端到端空集合。API 不可用時不可展示看似成功的 fallback fixtures。瀏覽器步驟待 UI 實作後執行。

### 5. Test, lint and build

**全數待驗證候選命令**：

```sh
npm --prefix frontend test -- --watch=false
npm --prefix frontend run lint
npm --prefix frontend run build
./mvnw -f backend/pom.xml test
./mvnw -f backend/pom.xml checkstyle:check
./mvnw -f backend/pom.xml verify
```

Test suites 須涵蓋 API success/error/input, profile boundary, exact persistence values, Flyway clean database startup, malformed fixture atomic rejection, duplicate load, safe reset guards, Angular loading/success/empty/error/retry and visible test labels. DB integration 使用 PostgreSQL Testcontainers，不使用 H2。實際 scripts/goals 是否建立及執行成功待後續實作，不能由計畫文件推定。

### 6. Smoke, restart and safe reset

冒煙流程確認測試頁透過 API 讀到 database rows。**候選命令待驗證**：

```sh
./scripts/smoke-local.sh
```

停止 API 與前端再啟動，重讀列表並逐欄比對三筆資料與 marker 完全相同。

重設僅用於本機 fixture rows。執行前確認四個環境條件與登入連線後的 `current_database()` 均符合計畫；以下命令亦待驗證：

```sh
set -a
. infra/.env.local
set +a
APP_ENV=local RESET_LOCAL_TEST_DATA=YES ./scripts/reset-local-test-data.sh --confirm-local-fixture-delete
```

拒絕案例必須先以自動測試驗證，包括 `APP_ENV` 缺漏或非 local、確認變數/旗標缺漏、非 loopback host、port/database/user 不符、連線實際 database 不符、環境設定解析失敗。以上案例都必須在任何 DELETE 前非零結束且保留所有資料。成功後只有 `local_test_fixture` 中 `test_only=true` rows 消失；schema、Flyway history 與其他 table 不變。再次執行 loader 後應恢復三筆 canonical rows，重跑冒煙和 UI 驗收。不得以資料庫或 schema drop 取代本程序。

## Acceptance record to produce after implementation

根目錄 `README.md` 應明確記錄本次完整驗收的單一目標 OS，並彙整該 OS 的 Node/Java/Docker/PostgreSQL 實際版本、執行目錄、必要 local services、跨端冒煙／重啟與逐條基線命令及結果；前端、後端開發規範各自記錄或直接連結對應端的實測命令、報告與結果。該 OS 本機基線命令須全數實際成功，才符合 SC-006 及該目標 OS 的第一階段完整驗收。macOS、Linux、Windows 其餘未實測平台須逐一標記「待驗證」，不得宣稱跨平台已驗收，但不因此否定已實測目標 OS 的階段結果。候選命令若未實際成功，持續標記待驗證；不得視為可用命令或完整驗收證據。
