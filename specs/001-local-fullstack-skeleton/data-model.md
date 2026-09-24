# Data Model: Local Test Fixture

此模型只支援第一階段本機骨架，刻意不使用魚種、漁港或行情等領域詞彙。固定來源採 UTF-8 JSON，預計路徑 `backend/src/main/resources/local-test-fixtures.v1.json`。檔案含 datasetVersion `1.0.0` 和恰好三筆資料；三筆是本階段可見、可比對的固定資料，不是產品內容數量承諾。

## Entity: LocalTestFixture

| 欄位 | JSON 型別 / DB 型別 | 必填 | 規則 |
| --- | --- | --- | --- |
| `id` | string UUID / `uuid` | 是 | 版控中的固定 UUID；三筆不得重複。僅為 fixture row identity。 |
| `fixtureKey` | string / `varchar(64)` | 是 | `^[a-z0-9][a-z0-9-]{0,63}$`；資料集內唯一，作為冪等 upsert key。 |
| `title` | string / `varchar(100)` | 是 | 修剪前後不可有差異、不可空白、長度 1–100 字元；使用「本機測試樣本一/二/三」等中性文字。 |
| `description` | string / `varchar(500)` | 是 | 長度 1–500 字元；清楚表示這是自行編造的測試內容，不得放入真實地名、魚名、價格、限制、個資或秘密。 |
| `datasetVersion` | string / `varchar(16)` | 是 | 全資料集同值，符合 `^[0-9]+\.[0-9]+\.[0-9]+$`；本版固定 `1.0.0`。 |
| `testOnly` | boolean / `boolean` | 是 | 必須恆為 `true`；DB `CHECK (test_only = true)`，API 與 UI 均保留並呈現。 |

### Fixed records

資料集三筆 `fixtureKey` 為 `sample-one`、`sample-two`、`sample-three`，`title` 分別為「本機測試樣本一」、「本機測試樣本二」、「本機測試樣本三」。`id` 分別固定為 `00000000-0000-4000-8000-000000000001`、`00000000-0000-4000-8000-000000000002`、`00000000-0000-4000-8000-000000000003`。每筆 `description` 都包含「僅供本機測試，非真實產品資料」語句，datasetVersion 為 `1.0.0`，testOnly 為 `true`。UI 與 fixture 契約的額外全域提醒不得只依賴 description。

ID 和 key 固定，title、description 由版控 fixture source 維護；不包含 `createdAt`、隨機值或目前時間，避免相同 dataset 再載入後 response 欄位漂移。

## PostgreSQL representation

`local_test_fixture` table 由初始 `V1__create_local_test_fixture.sql` 建立：

- `id uuid PRIMARY KEY`
- `fixture_key varchar(64) NOT NULL UNIQUE`
- `title varchar(100) NOT NULL`
- `description varchar(500) NOT NULL`
- `dataset_version varchar(16) NOT NULL`
- `test_only boolean NOT NULL CHECK (test_only = true)`
- 額外 `CHECK` constraints 對 key/version pattern 及非空文字重複保護。

不建外鍵；本表不屬任何真實領域實體。API DTO 僅映射以上明確欄位，不回傳內部資料庫細節。

## Validation and load semantics

1. 讀取 JSON 後以嚴格 schema 驗證：根物件欄位、陣列恰為三筆、欄位型別、必填、trim/長度、UUID/key 唯一性、version 一致與 testOnly=true。未知欄位亦拒絕，避免誤拼欄位被忽略。
2. 對整檔驗證完畢後才開始資料庫 transaction。任何 parse/validation error 都不連入寫入階段。
3. 依 `fixtureKey` 執行 `INSERT ... ON CONFLICT (fixture_key) DO UPDATE`，更新 `id/title/description/dataset_version/test_only` 為來源檔 canonical values；唯一 UUID 約束可拒絕不同 key 使用相同 ID。transaction 內檢查最後恰有三筆、欄位與來源逐欄相等後 commit。
4. 載入成功兩次的筆數和全部 API-visible 欄位完全相同；不為 rows 更新非固定時間欄位。資料集升版時修改 source `datasetVersion` 並由 loader 明確同步內容，不以重跑 Flyway 代替載入。
5. 清除流程只針對 `local_test_fixture` 中 `test_only=true` 的列，依計畫中的環境 allow-list 通過後在 transaction 刪除。schema 和 `flyway_schema_history` 永遠保留。

## State transitions

資料列生命週期僅為：不存在 → 由 loader 建立；已存在 → loader 對齊至 canonical source；已存在 → 經明確 guard 的 reset 清除。API 不提供寫入端點。欄位驗證失敗、版本不符、遷移未完成或啟動 profile 不符時，不得回報成功資料。
