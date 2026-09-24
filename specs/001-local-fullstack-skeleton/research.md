# Research: 第一階段本機前後端骨架

日期：2026-09-25。技術版本與官方支援狀態屬會變動資訊；以下是本次規劃查得的官方文件與決策，不代表本 repository 已建置或驗證相應工具。

## 1. Angular 21 本機工具鏈

**Decision**: Angular framework/CLI 使用 21.x 同步版本，Node.js 採 22.12+ 的 22.x 線，TypeScript 採 5.9.x；patch 版本由 package lock 與 Node 版本檔固定。單元測試使用新 Angular CLI 專案預設 Vitest 與 jsdom，透過 `ng test` 執行。

**Rationale**: Angular 官方相容表列出 21.x 支援 Node `^20.19.0 || ^22.12.0 || ^24.0.0`、TypeScript `>=5.9.0 <6.0.0`；Angular CLI 21 新專案預設 Vitest，官方測試指南說明其 jsdom 執行方式。選 Node 22 作團隊共同 major，避免讓開發者自行挑選 Angular 支援矩陣中的版本。

**Alternatives considered**: Node 20.19 與 24.0 也符合 Angular 相容表，但不採多條 Node 線；Karma/Jasmine 可支援既有專案，但本骨架無相容包袱，採 CLI 預設 Vitest 可少一套瀏覽器 runner。Angular 20 不符合本 feature 指定 Angular 21。

Sources: [Angular version compatibility](https://angular.dev/reference/versions), [Angular CLI `ng new`](https://angular.dev/cli/new), [Angular testing](https://angular.dev/guide/testing), [Angular releases](https://angular.dev/reference/releases).

## 2. Spring Boot 與 Java

**Decision**: 使用 Spring Boot 4.1.1、Java 21 toolchain、Maven Wrapper 3.9.11；精確 wrapper distribution 與 dependency versions 進版控。Boot 管理相容的 Spring、Flyway、PostgreSQL driver 與 testing dependencies。

**Rationale**: 查詢時 Spring Boot 官方系統需求列 4.1.1，要求 Java 17 以上、相容至 Java 26，支援 Maven 3.6.3+。Java 21 是高於最低需求的 LTS toolchain；Maven Wrapper 延續八階段文件已有的 `./mvnw` 命令介面並避免依賴全域 Maven。後端依 package 邊界形成模組化單體，不加入額外模組框架。

**Alternatives considered**: Gradle Wrapper 8.14+ 或 9.x 為 Spring Boot 官方支援選項，但目前階段文件已列 Maven Wrapper，切換會使既有開發指南不同步；Spring Boot 3.5.x 有相容組合，但不採舊主線。Java 17 是最低可行版本，選 21 對齊 LTS toolchain。

Sources: [Spring Boot system requirements](https://docs.spring.io/spring-boot/system-requirements.html), [Spring Boot installing](https://docs.spring.io/spring-boot/installing.html), [Spring Boot 3.5.16 release note](https://spring.io/blog/2026/06/25/spring-boot-3-5-16-available-now/).

## 3. PostgreSQL、Flyway schema 與固定測試資料

**Decision**: 本機 Compose 使用 PostgreSQL 18.6，將 host port 綁定 `127.0.0.1:5432`，資料庫及專用登入角色固定為 `harbor_local`。Flyway 版本化 migration 建表及限制；固定測試 rows 留在 JSON source，由獨立 loader 驗證後冪等 upsert。遷移順序先 schema、後 fixtures、再 API 驗收。禁止用 Flyway `clean` 或 DB drop 當作資料重設。

**Rationale**: PostgreSQL 官方目前將 18 列為支援中的 major，並建議採用所選 major 最新 minor。Flyway 文件說 versioned migrations 依序執行，repeatable migrations 在待執行 versioned migrations 後依序套用，內容 checksum 變動時重跑。Schema 要具可追溯單向演進；本地 fixture 則需要使用者看得見的明確重載／清除語義，獨立命令更容易先做全檔驗證、交易保護和冪等測試。PostgreSQL `DROP DATABASE` 不可逆且不能包在 transaction 內；整個 schema 清理超出重設測試 rows 的需要。

**Alternatives considered**: 把 fixtures 放在 V1 migration 會讓測試資料修改綁在 schema 版本，且只對尚未建置的 DB 執行一次；repeatable migration 會在 checksum 改變時於 migrate 階段重跑，對本機資料造成不明顯覆寫；手動 SQL/import 缺少同一套格式、欄位檢查與冪等驗收。以上方案都不如獨立 loader 符合 FR-009/010。

**Safety decision**: reset command 同時要求 `APP_ENV=local`、`RESET_LOCAL_TEST_DATA=YES`、loopback URL、精確 port/database/user 與連線後 `current_database()` 驗證，另要命令列明確確認旗標。任何條件不足或不符，都在 DELETE 前結束。成功交易只刪 `test_only=true` fixture rows。這是本專案自己的 allow-list 防護，不把 Flyway `cleanDisabled` 誤當成命令安全檢查。

Sources: [PostgreSQL versioning](https://www.postgresql.org/support/versioning/), [Flyway supported database versions](https://documentation.red-gate.com/fd/supported-database-versions-143754067.html), [Flyway migrations](https://documentation.red-gate.com/fd/migrations-271585107.html), [Flyway repeatable migrations](https://documentation.red-gate.com/fd/repeatable-migrations-273973335.html), [Flyway working with data](https://documentation.red-gate.com/flyway/database-development-using-flyway/working-with-data), [Flyway clean](https://documentation.red-gate.com/flyway/reference/commands/clean), [Flyway cleanDisabled](https://documentation.red-gate.com/fd/flyway-clean-disabled-setting-277578981.html), [PostgreSQL DROP DATABASE](https://www.postgresql.org/docs/17/sql-dropdatabase.html).

## 4. API 成功與錯誤契約

**Decision**: 以 OpenAPI 3.1 作契約文件，提供 local/test profile 才啟用的唯讀 list/get 路徑。成功回應帶固定測試 marker 與 dataset version；錯誤使用 RFC 9457 Problem Details，增加穩定 `code` 與欄位錯誤清單。DTO 與持久化 model 分離。

**Rationale**: 此契約保留 `/api/v1` 版本規則，又把 local fixture 路徑與未來公開領域路徑分開；RFC 9457 保持通用 HTTP error shape，擴充欄位可讓前端顯示易懂訊息並辨識驗證錯誤。唯讀端點沒有資料寫入安全面；local/test profile 隔離避免產品 profile 意外暴露骨架資料。

**Alternatives considered**: 以任意 `{error, message}` JSON 自訂錯誤格式容易漂移；讓前端直接讀資料庫違反憲章；建立通用 CRUD/管理 API 超出階段一且提高安全範圍。

Sources: [RFC 9457 Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457.html), [OpenAPI Specification 3.1](https://spec.openapis.org/oas/v3.1.0.html).

## 5. 驗證邊界與命令狀態

**Decision**: 以真實 PostgreSQL 18 Testcontainers 驗證資料庫與 Flyway；後端分應用/API/持久化測試，前端使用 Vitest component/HTTP 測試，跨端另有本機冒煙和人工瀏覽器頁面驗收。TDD 逐片確認紅燈、實作、綠燈。

**Rationale**: 後端規範禁止假定替代資料庫行為等價於 PostgreSQL；前端規範要求觀察載入、錯誤、空結果與未知狀態；共同憲章要求從公開行為驗證。測試工具選擇是計畫決策而非已存在工具。

**Alternatives considered**: H2 不足以驗證 PostgreSQL-specific migration/constraints；單靠跨端冒煙無法定位端點和元件失敗；僅測私有 service 呼叫不符合外部可觀察行為要求。

**Validation status**: 本次只執行 Spec Kit 的 `.specify/scripts/bash/setup-plan.sh --json` 以定位分支規格與計畫範本。沒有執行 Angular、Maven、Docker、資料庫、遷移或冒煙命令；quickstart 內的命令皆標「待驗證」，直至實作後有實際成功輸出。
