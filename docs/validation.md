# 驗證紀錄

教材基準：MCP Authorization **2026-07-28**。本頁區分已執行的本機驗證與尚待現場服務的彩排，不將 mock 當作 Signet。

## 2026-10-11：Lab 05 簡化為 public Client 撤銷（目前版本）

Lab 05 已移除 introspection 與額外 confidential Client 憑證需求。必做流程改為 public Client 登入、撤銷與重複撤銷；Server 入口保留為選做，沿用 Lab 04 的離線 JWT／scope 檢查，不再以撤銷後立即回 401 驗收。

本次真實 Signet 介面顯示版本 `v1.7.0-2-g7e68fb5`，issuer 為 `https://signet.wu-boy.com`。

| 驗證 | Go | Python |
| --- | --- | --- |
| 本次對話中新取得的 `notes:read` Token：PKCE 登入與 public Client 撤銷，不帶 secret | 通過 | 通過 |
| 修改後重複撤銷上述測試 Token，檔案內容保持不變 | 通過 | 通過 |
| 修改後使用真實 Signet 啟動 Lab 05，兩個 introspection 環境變數皆空白 | 通過 | 通過 |
| 啟動後 health 200、匿名 MCP 請求 401 | 通過 | 通過 |

本機 `./scripts/check.sh` 通過 Go 格式／vet／tests、Ruff lint／format 與 pytest：**33 passed in 17.58s**。測試 issuer 不提供 introspection endpoint；測試確認 Lab 05 仍拒絕匿名、過期、錯 audience 與缺少 write scope 的請求，並驗證 public Client 撤銷、重複撤銷與離線 Server 仍接受尚有效 JWT 的限制。

真實服務這輪未重跑選做的「MCP 呼叫 → 撤銷 → 再呼叫」；此限制的回歸證據來自本機測試，不冒充真實服務驗收。測試 Server 已停止，未修改本機 `.env`，未輸出 raw token。

以下保留歷史紀錄；其中要求 introspection 憑證、期待撤銷後 401 或 503 的 Lab 05 描述，只適用於當時的舊版教材，不是目前的設定或驗收條件。

## 2026-10-11：新版 Signet 重跑與教材修正

**本節為先前版本的歷史紀錄，保留當時結果；Lab 05 的目前流程與驗收請以上一節為準。當時未完成的其他現場項目仍需分別驗收。**

環境：Signet `v1.6.0-2-gc4d3d86`、本機 Go 1.26.7、Python 3.12.13、Claude Code 2.1.263、Codex 0.162.1、Docker 29.2.1、Compose 5.1.4。真實 issuer 為 `https://signet.wu-boy.com`。

| 項目                        | 本輪真實結果                                                                                                                                    |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Lab 01／Go、Python          | 匿名 whoami、create_note、list_notes 均 200                                                                                                     |
| Lab 01／Signet UI           | 新建專用 public App，五個 scopes、三個 callbacks、三個 resources 保存，立即 active；編輯描述與授權紀錄可查看                                    |
| Lab 02／Go、Python          | 無 Token 401、有 Token 仍 401；challenge、PRM、真實 Signet metadata 正確                                                                        |
| Lab 03／Go、Python          | 新的 Go read、Python read+write PKCE 登入成功；無 Token 401，有效 Token 200                                                                     |
| Lab 04／Go、Python          | read 可讀、write 403；read+write 可建立／列出筆記；A Token 打 B 401，B Token 200                                                                |
| Lab 05／Go、Python          | 真實啟動均因缺 introspection ID/secret 拒絕；本機 fixture 的撤銷與 outage 測試通過，但不等於真實服務通過                                        |
| Lab 06／Go、Python profiles | 分別建置並 `up --wait` 成功；有效 Token 200、建立筆記 200、錯 audience 401、read-only 寫入 403、偽造 subject 被覆寫，backend 沒有發布 host port |
| Lab 06／撤銷限制            | 真實 Signet 接受撤銷 Gateway read Token，同一檔案呼叫 Kong 仍 200，符合離線驗證的限制                                                           |

本輪 Labs 01–04 共 30 個 HTTP 狀態斷言與兩份 PRM 斷言；兩個 Gateway profiles 各 5 個 HTTP 斷言。兩套參考 Client 另有實際呼叫驗證。Token 全部保存為被忽略的 0600 檔案，未記錄 raw token。

### 新版 App 流程

新建測試 App `hwdc-2026-rehearsal-20261011`，Client ID `e2836f48-bf8e-4edd-a18e-abb1e3a67bc9`。僅配置本機 workshop resources 與練習 scopes，沒有管理權限。此 App 完成「註冊 → 立即 active → 編輯描述 → PKCE 同意 notes:read → 呼叫 Python Lab 03 成功 → 已授權使用者頁顯示 notes:read 與 8000 resource」。保留供後續驗證，未取代原本 `.env` 的 public Client ID。

本輪使用既有管理員帳號的前台介面；尚未提供第二個一般學員帳號，因此不能據此宣稱非管理員流程及兩個真實使用者隔離已驗收。

**仍存在的 Signet 介面問題：** 註冊時明確取消 Device Flow，建立後 grant_types 只有 authorization_code，但第一次編輯頁的 Device Flow 又顯示勾選。再次取消並更新，再開編輯頁則正確關閉。尚未證明 endpoint 行為；教材加入明確複核與修正步驟。另外，詳情頁 Allowed Resources 仍標「由管理員管理」，但前台建立／編輯已可保存，文案容易誤導。

### 已修正的教材與程式問題

- Go whoami 的 `audience: true` outputSchema 使 Claude `tools/list` 失敗。已改成明確 string／string array schema，保留 JWT aud 兩種原有回應形狀；修正前 `tools fetch failed`，修正後 Go Lab 01 與 Lab 03 均 `Connected`。新增 schema 與 audience 陣列回歸斷言。
- 全部學員指引改為自行新增 notes scopes、resources、確認 active；保留 pending 的例外處理，不再把等待核准當主流程。
- Codex add 仍會先自動申請 openid/profile/email；教材保留標準 scopes，要求完成首次流程後，再顯式 login notes:read。
- Kong 啟動加入 `--wait --wait-timeout 120`；明確要求 Docker daemon 啟動、課前 build，課堂用 --no-build、切換 profile 前先 down。
- 補齊 A/B 終端分工、換關停服、Lab 05 憑證預檢、Lab 06 可直接執行的 403／401 測試、CLI 模型登入與 MCP 登入的區別。

### AI CLI

- Claude 的 Signet MCP 瀏覽器登入成功；Go／Python Lab 03 都 `Connected`。但模型呼叫實測回 `OAuth session expired and could not be refreshed`，屬 Claude 自己的模型帳號憑證；需要使用者重新登入 Claude 後再驗收模型工具呼叫。
- Codex add 與明確 notes:read login 均成功；Go／Python Lab 03 的模型已分別實際呼叫 whoami 與 list_notes，四次均成功。
- 非互動 Codex 初次被本機工具批准設定擋下；採單次 `-c`、僅限本次測試 entry 的 whoami/list_notes 批准後成功，沒有修改全域批准政策。互動學員應在看過工具名稱後批准該次呼叫。
- 自動 scope step-up 尚未驗收；Lab 04 以獨立參考 Token 明確重登驗收。

### 本機回歸與未完成條件

`./scripts/check.sh`：Go vet/tests、Ruff lint/format 通過，**33 passed in 14.43s**。另 `go test -race ./...` 與兩個 Compose profile 的 `config --quiet` 均通過。涵蓋六關兩語言、本機 issuer 的 Token 拒絕、scope、audience、subject 隔離、撤銷、503 fail-closed 與 Gateway 信任邊界。

本輪結束已停止測試 Server／Compose，移除新增的 workshop-rehearsal-1011 CLI entries；保留專用 Signet App 與被忽略的測試 Token 供後續驗證。

剩餘：填入 `.env` 的 `INTROSPECTION_CLIENT_ID`／`INTROSPECTION_CLIENT_SECRET` 後完成真實 Lab 05；重新登入 Claude 模型帳號；提供一般學員與第二使用者測試身分。60 人容量、會場網路與 Windows/WSL2 仍需在對應環境驗收。

## 2026-10-10：scopes / resources 補齊後的真實 Token 驗證

本節為最新結果；下方保留前兩輪的失敗原因供重現，不代表目前 Client 仍缺設定。

Client `e15b4afb-f989-4baf-afe9-a5dc98e17fa0` 已確認 active、具有 `notes:read notes:write` 與 8000 / 8001 / 9000 三個完整 resource。使用瀏覽器既有 appleboy 身分，Go / Python 參考 Client 均完成真實 Authorization Code + PKCE；取得的 Token 為 `type=access`，issuer 正確、audience 對應所請求 resource，檔案權限 0600。整個流程未輸出 raw access token。

| 驗收                                                           | Go   | Python |
| -------------------------------------------------------------- | ---- | ------ |
| Lab 03：無 Token 401、真實 Token 呼叫成功                      | 通過 | 通過   |
| Lab 04：read Token 可讀、寫入 403；read+write 可建立並讀取筆記 | 通過 | 通過   |
| Lab 04：A Token 到 B 回 401，B 自己的 Token 成功               | 通過 | 通過   |
| Lab 06：9000 Token 經真實 Kong 呼叫、寫入成功                  | 通過 | 通過   |
| Lab 06：8000 Token 被拒、read-only 寫入 403                    | 通過 | 通過   |
| Lab 06：外部偽造 `X-MCP-Subject` 被正確身分覆寫                | 通過 | 通過   |

上述為實際啟動兩種語言 Server 與兩個 Compose profiles 的結果，包含 20 個 Lab 03/04 HTTP 斷言與 10 個 Gateway HTTP 斷言；並另用 Go / Python 參考 Client 分別呼叫實際 Server。此次使用 Compose `up -d --wait` 等待 Kong 就緒。

### AI CLI 真實登入結果

- Claude Code 2.1.263：固定 `localhost:8767/callback`，實際申請 `notes:read`，登入成功；Python Lab 03 的 `claude mcp get` 為 `✔ Connected`。非 TTY 執行 login 會拒絕，改用互動終端即成功，符合課程的終端使用情境。
- Codex 0.162.1：固定 `127.0.0.1:8766/callback`，明確執行 `mcp login --scopes notes:read` 後回報 `Successfully logged in`。這是登入成功證據，不等於已由模型呼叫工具。
- **新增教材卡點**：`codex mcp add ... --oauth-client-id ... --oauth-resource ...` 會立即啟動 OAuth，首次實際送出的是 `openid profile email`，而非 PRM 的 `notes:read`。原文件直到下一行 login 才指定 notes scope，學員會先進入另一個授權流程；依原教材只允許 openid/notes 的 App，首次自動流程還可能因 profile/email 未允許而失敗。需補充首次自動登入的處理方式，並以顯式 notes login 作為驗收。
- Codex 的授權 URL 同時出現兩個相同 `resource` 參數；本次 Signet 接受且登入成功，未將此現象列為阻斷問題。
- Go 共用 `whoami` outputSchema 的 Claude 相容性問題仍需修正；Signet 設定補齊不會修復該 schema。

### 撤銷與剩餘缺口

- Go / Python 參考 Client 分別向真實 Signet 撤銷本輪新取得的 B Token / Gateway read Token，API 均接受。
- 撤銷 Gateway read Token 後，以同一檔案呼叫 Kong 仍回 200，實際重現 Lab 06 離線 JWT 驗證不保證即時撤銷的教材限制。
- **Lab 05 尚未完成**：`.env` 的 `INTROSPECTION_CLIENT_ID` / `INTROSPECTION_CLIENT_SECRET` 仍空白；尚不能驗收真實同一 Token「有效 → 撤銷 → 401」。已保留 8000 resource 的獨立測試 Token 供後續驗證。
- 一般非管理員自助 App 流程、第二個真實使用者的資料隔離、AI CLI 由模型實際呼叫與 step-up、60 人容量及 WSL2 仍未驗收。先前本機 fixture 通過不能代替這些項目。

## 2026-10-10：Client 核准後重測

使用者核准 `e15b4afb-f989-4baf-afe9-a5dc98e17fa0` 後，已再次查看真實 Signet 詳情並執行兩個參考 Client 的 PKCE 授權：

- App 狀態已是 active；Authorization Code enabled，Device Flow disabled，三個 callbacks 正確。
- 實際儲存 scopes 仍只有 `openid`，Allowed Resources 顯示「—（全部拒絕）」；上一輪表單預填的 notes scopes 與 resources 並未保存。
- Go 依教材申請 `scope=notes:read`、`resource=http://localhost:8000/mcp`，Signet callback 回 `error=invalid_scope`；Client 以 `authorization denied` 結束。
- Python 改用已允許的 `scope=openid` 隔離測試同一 resource，Signet callback 回 `error=invalid_target`，描述為 `this client is not configured to request any resource indicator`。
- 瀏覽器在 callback 顯示 `ERR_BLOCKED_BY_CLIENT`，但 callback URL 已包含上述 Signet 錯誤；本輪未更動瀏覽器保護設定，不能把這個畫面當作已成功授權。
- 本機 `.env` 的 `OAUTH_CLIENT_ID` 已更新為此 ID。`INTROSPECTION_CLIENT_ID` / `INTROSPECTION_CLIENT_SECRET` 仍空白，未產生成功登入的 Token。

結論：**只核准 active 不足以進入 Lab 03**。需在該 Client 保留 `openid`，加入 `notes:read notes:write`，並保存以下三個 Allowed Resources，才能繼續 Lab 03 / 04 / 06 的真實 Token 驗證：

```text
http://localhost:8000/mcp
http://localhost:8001/mcp
http://localhost:9000/mcp
```

Lab 05 另外需要獨立 confidential introspection Client 憑證。此次未修改 Signet 的權限設定，亦未將失敗的登入算作六關通過。

## 2026-10-10 晚間：更新後 Signet v1.6.0 彩排（尚未完成登入全流程）

本輪實際使用 `https://signet.wu-boy.com`、Claude Code 2.1.263、Go / Python Server 與 Docker 29.2.1。以下是新增證據；下方較早紀錄的「瀏覽器不可用」「Docker daemon 未啟動」已不適用本輪。

| Lab | 本輪實際結果                                                                                                                                                                                | 尚未驗收                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 01  | Go / Python 匿名工具呼叫、建立與讀取筆記成功；Python 的 Claude `mcp get` 顯示 Connected；Go 工具探索失敗，見問題 1。透過 Signet `/apps/new` 建立專用 public App、取得 pending、編輯描述成功 | 一般非管理員身分操作；AI CLI 由模型實際呼叫工具                                           |
| 02  | 兩種語言均取得 401、challenge、PRM；兩個參考 Client 成功讀取真實 AS metadata；OIDC discovery / RS256 JWKS 可讀                                                                              | 無：本關 discovery 主線已完成                                                             |
| 03  | 兩種語言均以真實 issuer 啟動、未帶 Token 回 401；pending App 的 PKCE 授權頁回 `unauthorized_client`                                                                                         | 已核准 App 的 PKCE、真實 access token 驗簽、兩套 AI CLI 登入                              |
| 04  | 兩種語言以真實 issuer 啟動；scope、A/B audience、subject 隔離的本機 fixture 測試通過                                                                                                        | 真實 Signet read / write / B resource Token，以及第二個測試身分                           |
| 05  | 本機 fixture 的同一 Token 撤銷、503 fail-closed 測試通過；沒有 introspection 憑證時兩種語言均拒絕啟動                                                                                       | 真實 confidential Client 憑證、有效 → 撤銷 → 401                                          |
| 06  | Go / Python profiles 分別 build / 啟動成功，Kong healthy，backend 未發布 host port；401 與 9000 PRM 正確；偽造身分 header、無效 Bearer 被拒絕                                               | 真實 9000 Token 經 Kong 呼叫兩種 backend、read-only 寫入拒絕、8000 Token 跨 audience 拒絕 |

`./scripts/check.sh` 本輪結果：**33 passed in 18.18s**，Go vet / tests、Python lint / format 均通過。這些包含本機 issuer 的測試，不能代替表中尚未驗收項目。

### 問題 1：Go 的 whoami outputSchema 使 Claude 工具探索失敗（阻擋上課）

`go/internal/workshop/server.go` 的 `identity.Audience` 使用 `any`，SDK 產生 `outputSchema.properties.audience: true`。Claude Code 2.1.263 回報：

```text
Status: ! Connected · tools fetch failed
Issue: Invalid input (at tools.2.outputSchema.properties.audience)
```

六關共用同一工具定義。參考 Client 直接 `tools/call` 能成功，所以現有測試沒有涵蓋這個相容性問題。相同版本 Claude 連 Python Lab 01 顯示 `✔ Connected`。

重現：啟動 Go Lab 01，依 `docs/clients.md` 新增獨立測試 entry，再執行 `claude mcp get <entry>`。建議將對外 audience schema 明確定義成 Client 可解析的型別，並以 Claude 工具探索再次驗證。尚未修改產品程式碼。

另以 `initialize` / `protocolVersion=2025-11-25` 向 Go Lab 01 發送請求，Server 成功回應；不能將以上 schema 錯誤歸因於完全不支援舊版交握。

### 問題 2：Signet 註冊頁與教材的 scope 說明不一致

部署 v1.6.0 的 `/apps/new` 已顯示自訂 scope 輸入、命名限制、保留前綴與「儲存後，非標準 scopes 僅能由管理員移除」提示。`docs/signet-client-app.md` 與 `docs/instructor.md` 仍說一般表單只能選標準 scopes。此次使用的是已登入管理員帳號的前台表單；一般非管理員的實際新增權限仍需另測，不能由本次畫面直接宣稱兩者相同。

### 問題 3：建立 App 時取消 Device Flow，編輯頁卻仍顯示啟用

本輪在註冊頁明確取消 Device Flow、僅勾 Authorization Code。建立後首次進入編輯頁，Device Flow 又顯示已勾選；再次取消並更新後，管理員編輯頁才顯示關閉。詳情頁的 `grant_types` 仍僅顯示 `authorization_code`，因此目前是欄位狀態不一致的實測證據，尚未證明 Device Flow endpoint 實際可用。應追查建立時的布林值保存，並在教材要求建立後複核。

### 問題 4：Lab 06 啟動指令缺少就緒等待

Python profile 的 `up -d` 返回後立即執行教材下一行 `curl`，重現 `curl: (52) Empty reply from server`；約一秒後再次請求即回預期 401。建議以 Compose `--wait` 或有逾時的就緒輪詢取代立即驗收；本次兩個 profiles 最終均正常啟動。

### 本輪留下的設定與阻擋條件

- 建立專用 App `hwdc-2026-rehearsal-20261010`，Client ID `e15b4afb-f989-4baf-afe9-a5dc98e17fa0`；仍為 pending。已完成教材的三個 callback，已儲存 scope 僅 `openid`。管理員頁上 notes scopes / 三個 resources / active 的變更僅填入表單，尚未提交。
- 現有 `Workshop acceptance tests public` 是另一個 fixture：callback 為 `http://localhost:8888/callback`、scopes 為 `openid profile offline_access`、allowed resources 為空，不能直接當這六關的備援 App。本輪未修改它。
- 本機建立被 Git 忽略的 `.env` 與 `.runtime/kong.yml`，只含範例設定及隨機 Gateway secret；尚無有效 public Client ID / introspection 憑證，也未取得真實 Token。
- 要完成剩餘彩排，需核准專用 public App、提供獨立 introspection Client 與一般測試身分。未完成前，不能宣稱六關真實 Signet 端到端全部通過。

MCP 傳輸層使用 2026-07-28（無 `initialize` 交握，Go go-sdk v1.8.0、Python `mcp` 2.3.0），測試與參考 Client 皆以此版本呼叫。Claude Code / Codex CLI 對新版傳輸的支援尚未核對，需在彩排時確認。

## 已執行

- Go 1.26.9：六個 Lab 與參考 OAuth Client 編譯成功，`go vet ./...` 通過。
- Python 3.12.13、uv lock：依賴安裝成功，Ruff 檢查與格式化通過。
- `tests/test_labs.py` 以本機測試 issuer 啟動兩種語言的真實 MCP HTTP Server，測試：
  - 初始化、工具探索、工具呼叫與匿名 baseline。
  - 401 challenge、PRM、AS discovery。
  - RS256、issuer、audience、expiry、subject、access type、偽造 HS256 拒絕。
  - scope 403、寫入成功、不同 subject 筆記隔離、跨 audience 拒絕。
  - 同一 Token 撤銷後拒絕、introspection outage 回 503。
  - Gateway secret 與身分邊界、Python 的 Host 保護。
  - Go/Python PKCE：state 負向驗證、S256、兩次 resource 綁定、0600 token file、呼叫、撤銷。
  - 參考 Client 拒絕非 loopback 明文目的地，正確處理 JSON-RPC error。
- CLI 旗標核對：Codex 0.162.1、Claude Code 2.1.263 的本機 `--help`。
- Kong 設定產生器的私有檔案權限與 `preserve_host` / `strip_path` 有測試。
- 兩個 Docker Compose profiles 均通過 `config --quiet`，不需要 Docker daemon。
- 本次 `./scripts/check.sh`：**33 tests passed**。第三方套件有 Starlette TestClient / Pydantic settings 警告，不影響斷言結果。

執行 `./scripts/check.sh` 取得最新測試數與結果；GitHub Actions 重跑相同檢查。

## 現場服務：公開連線檢查（2026-10-10）

服務：`https://signet.wu-boy.com`。

- AS metadata、OIDC discovery、JWKS：HTTPS 讀取成功；issuer 不含結尾斜線。
- 宣告 `S256`、resource indicators、public Client `none` 認證方式；JWKS 提供 RSA / RS256 公鑰。
- Go / Python 的參考 Client `metadata` 指令均成功讀取真實 Signet。
- 兩種語言的 Lab 03 使用真實 issuer 啟動，PRM 指向該 issuer，未帶 Token 的請求回 401 與 challenge。
- 沒有使用真實帳號登入或取得 access token，以上不代表授權、scope、audience、撤銷端到端已完成。

## 尚未宣稱完成

| 項目                                     | 原因／完成條件                                                                            |
| ---------------------------------------- | ----------------------------------------------------------------------------------------- |
| 新的現場 Signet 端到端驗證               | 部署 URL 與公開 discovery 已確認；仍待 Client ID 與測試身分，依 instructor checklist 彩排 |
| 學員自助 Client App UI 完整流程          | 瀏覽器控制服務不可用，尚未登入網站驗證建立、核准、自己的 ID 登入；未建立或修改現場 App    |
| Claude Code / Codex 瀏覽器登入與 step-up | 目前核對文件與旗標，沒有使用真實課程身分完成互動登入                                      |
| Kong 容器實際代理 Go / Python            | 本機 Docker daemon 未啟動；Compose 設定可檢查，但不是容器 runtime 成功證明                |
| 60 人集中登入容量                        | 需在實際授權服務與會場網路條件下壓測                                                      |
| Windows + WSL2                           | 需以學員相同環境彩排 callback 導流                                                        |

## 已知設計取捨

- 跨資源 scope 升級由參考 Client 明確重新登入，不假設 AI CLI 自動 step-up。
- Lab 06 使用固定 plugin commit `bafa464e89d6c46bb222dfce1877304f9e62473a`，只做離線 JWT；不含即時撤銷。
- 基礎 HTTP MCP 使用官方 SDK 的 stateless + JSON response，減少 session/SSE 分支，集中教學授權。
- 範例是教學完成版；尚未經真人逐行安全審查，不宣稱已可直接上正式環境。

## 重現

```bash
./scripts/check.sh
```

Signet 服務檢查與課前設定見 [講師手冊](instructor.md)。
