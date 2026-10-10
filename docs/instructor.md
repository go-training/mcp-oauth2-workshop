# 講師：Signet 與現場準備

授權服務使用 **[go-signet/signet](https://github.com/go-signet/signet)**（先前討論的 `signt` 對應此 repo）。已提供工作坊服務 **https://signet.wu-boy.com**，學員不用自行部署。學員在自己的筆電執行 HTTP MCP 與 Claude Code／Codex，瀏覽器 callback 回到自己的筆電，Signet 不需主動連進學員筆電。

## 服務設定

依 Signet 官方部署文件完成資料庫、使用者登入方式、TLS、備份與必要 secrets。本 repo 不建立真實授權服務，也不保存講師管理員憑證。

授權行為核對來源：Signet checkout [`a6747be2a6364e4c15bfa5e39524247f5ecc9fd9`](https://github.com/go-signet/signet/tree/a6747be2a6364e4c15bfa5e39524247f5ecc9fd9)。部署若使用其他版本，重新核對以下設定與 API。

```dotenv
BASE_URL=https://signet.wu-boy.com
ENVIRONMENT=production
JWT_SIGNING_ALGORITHM=RS256
JWT_PRIVATE_KEY_PATH=/run/secrets/signet-rsa-private.pem
PKCE_REQUIRED=true
INTROSPECTION_REQUIRE_OWNERSHIP=true
```

私鑰只放 Signet。MCP Server / Kong 只取得公開 JWKS，不能把 RSA 私鑰或 HS256 共用密鑰發給學員。

本次採固定 callback URI。若確實需要動態 loopback port，可用 `LOOPBACK_REDIRECT_ANY_PORT_ENABLED=true` 並註冊不含 port 的 loopback URI；host / path 仍需相符，`localhost` 和 `127.0.0.1` 不可互換。固定版本 CLI 的 callback 以 [Client 指引](clients.md) 為準。

## 現場服務公開檢查（2026-10-10）

- HTTPS AS metadata / OIDC discovery 與 JWKS 均可讀取。
- Metadata 的 issuer 是 `https://signet.wu-boy.com`，設定不要附加 `/`。
- 宣告 PKCE `S256`、Authorization Code、public Client 的 `none` 認證方式與 resource indicators 支援。
- JWKS 提供 RSA / RS256 signing key；尚未用實際 access token 核對其簽章、claims 與 audience。
- 公開 `scopes_supported` 列出 `openid profile email`；這份全域清單不能證明 workshop Client 已允許 `notes:read notes:write`，請依下表確認管理員建立的 Client。

這些讀取操作沒有建立帳號、註冊 Client 或更動現場服務。登入、撤銷與兩套 AI CLI 仍需使用課程身分彩排。

## 每組的 Client 與帳號

### 主流程：學員建立自己的 public App，講師完成核准

課前寄出 [學員逐步教學](signet-client-app.md)。入場先登入 Signet，Lab 01 由學員自行填表、取得 Client ID、查看 pending 狀態並編輯描述；讓每位學員實際操作 App 介面。Lab 02 期間由講師或已有管理員權限的工作人員處理設定，Lab 03 使用自己的 App 登入。

目前學員 `/apps/new` 有三個限制：建立後 pending、只能自行選標準 scopes、沒有 Allowed Resources 欄位。這些限制不需要為工作坊而解除；核准是課程的一部分。

1. 收集座位編號、App 名稱、Client ID；不用收 Token、密碼或 secret。
2. 在 [管理員 Client 清單](https://signet.wu-boy.com/admin/clients) 找到該 App，核對 owner 與學員對應，**保留 owner 為學員**。
3. 開啟編輯設定，複核以下欄位、加入 scopes / resources，將 Status 選為 active 後一起儲存。
4. 回到詳情頁確認設定與 active 狀態，再通知學員重新整理；不要只按核准而漏掉 scope / resource。
5. 學員更新自己的 `.env`，以 App 同意畫面的名稱與登入後的 App 授權紀錄確認使用的是自己的 App。

| 設定 | 核准時應有的值 |
| --- | --- |
| Client type | public |
| Authorization Code Flow | enabled |
| Device Flow / Client Credentials / Personal API Key | 本課主線不啟用 |
| Scopes | 保留初始 `openid`，加入 `notes:read notes:write` |
| Redirect URIs | `http://127.0.0.1:8765/callback`、`http://127.0.0.1:8766/callback`、`http://localhost:8767/callback` |
| Allowed resources | `http://localhost:8000/mcp`、`http://localhost:8001/mcp`、`http://localhost:9000/mcp` |
| Owner | 建立該 App 的學員 |
| Status | 完成設定後 active |
| 略過同意授權 / Skip Consent | 不勾選，讓學員能看到自己 App 的同意畫面 |
| Client secret | public Client 沒有，也不需要發放 |

若部署版本有批次核准功能，它只改 pending → active，**不會自動補上自訂 scopes / allowed resources**。每個 App 的設定仍須完成。不要對公開服務的全部 pending App 無條件核准，只處理這場工作坊確認過的清單。

60 人現場手動設定可能超過 Lab 02 的時間。優先讓學員課前先建立 App，講師預先處理；當天才建立者邊上課邊處理，到 Lab 03 還沒完成就使用下面的備援。這份教材沒有自動批量修改正式服務的程式。

### 備援：講師共用 public Client App

講師課前建立 `hwdc-2026-shared-fallback`，設定與上表相同 callbacks、resources，至少允許 `notes:read notes:write` 並確認 active。發放的是 **public Client ID**；每位學員仍用自己的登入帳號、個別同意授權，取得各自 Token。

- 不共用帳號、Token、confidential Client secret 或管理員憑證。
- 學員自己的 App 仍保留並完成核准；備援只是避免課程中斷。
- 切換 Client ID 需要重新登入；AI CLI 用 `workshop-fallback` 與 `workshop-personal` 分開設定，避免沿用舊授權快取。
- 課後由講師停用共用 App，學員不要嘗試管理這個不屬於自己的 App。

這仍是 CLI 使用已註冊 Client ID 的 pre-registration 路線，與自動 DCR / CIMD 不同。DCR 同樣可能 pending，DCR/CIMD 的自助 safe scopes 不包含本課 notes scopes，不能用來跳過講師設定。

Resource 逐字匹配。相同本機 URL 出現在不同學員電腦是同一個 OAuth resource 識別，**不表示不同筆電已由 audience 隔離**；本課跨資源隔離示範是 8000 / 8001 / 9000 三個識別。學員身分與資料隔離另由 subject 處理；勿交換 Token。

### Confidential introspection Client（Lab 05）

另為每組建立一組 active confidential Client 憑證，使用 Signet `/oauth/introspect`。不授予管理 API 權限，不使用講師管理員帳密。將 ID/secret 私下提供給該組，放在被 Git 忽略的 `.env`。

保留 `INTROSPECTION_REQUIRE_OWNERSHIP=true`：對另一個 Client 的有效 Token，Signet 可以只回 `{"active":true}`。教材先驗證 JWT，再只取 introspection 的 active 狀態，因此不需要降低 ownership 保護。

## 端點核對

實際 URL 由 metadata 發現，不在範例中寫死 host。

| 用途 | Signet 路徑 | 本課使用 |
| --- | --- | --- |
| AS metadata | `/.well-known/oauth-authorization-server` | discovery / PKCE 能力 |
| OIDC discovery | `/.well-known/openid-configuration` | metadata fallback |
| JWKS | `/.well-known/jwks.json` | RS256 驗簽 |
| Authorize | `/oauth/authorize` | 使用者登入／同意 |
| Token | `/oauth/token` | PKCE code 換 Token，帶 resource |
| Introspect | `/oauth/introspect` | confidential Client Basic auth，每次請求查 active |
| Revoke | `/oauth/revoke` | form token；此版本不要求 Client 認證 |

`/oauth/revoke` 對不存在或已撤銷的 Token 仍可能回 200；必須再用相同 Token 呼叫 MCP 才能驗收。此端點路徑不保證記錄管理員撤銷 audit event，教材以 Resource Server 的允許／拒絕紀錄為最低證據；若要展示完整管理事件，先彩排 Signet 管理介面的撤銷流程。

## 課前彩排

- [ ] 固定 Signet 部署版本、issuer、TLS，確認使用者可登入。
- [ ] Metadata 的 issuer 與 JWT `iss` 完全一致，JWKS 有對應 `kid`，access token 使用 RS256。
- [ ] `S256` 被 metadata 宣告；public clients、callbacks、自訂 scopes、三個 resources 都完成設定。
- [ ] Go / Python PKCE 參考 Client 分別登入成功；檢查 Token audience 與所請求 resource 一致。
- [ ] 使用一般學員帳號完成 `/apps/new` → pending → 講師補 scopes/resources 並核准 → active → 以自己的 ID 登入；不能只用管理員帳號測 UI。
- [ ] 確認學員可編輯描述；管理員加入的 notes scopes 被保留且不可由學員任意更改。
- [ ] 共用備援 App 已跑通，切回學員自己的 ID 時確實重新登入。
- [ ] Claude Code / Codex 各自登入、呼叫工具、重新授權成功；不要只測其中一套。
- [ ] A Token 到 B 被拒；只有 read 的 Token 不能 write。
- [ ] 撤銷後下一次請求被拒；introspection 失效時回 503。
- [ ] Kong 的 Go / Python profiles 分別跑過。先停止一個 profile 再啟動另一個。
- [ ] 以接近 60 人同時操作的登入、換 Token、JWKS、introspection 流量彩排容量。
- [ ] 確認會場 Wi-Fi、DNS、HTTPS、loopback callback 與 WSL2 瀏覽器導流。
- [ ] 凍結教材 commit，預先下載 Go modules、uv dependencies、Kong / backend images。
- [ ] 準備已下載的完成版與關鍵流程錄影作為網路故障備案。

## 現場節奏

13:00–13:25 進場執行 health check、登入 Signet，尚未建立 App 的學員可先依教學填表；13:25 後協助備取學員；13:30 開始 90 分鐘主課。建議 3–4 位助教處理各區環境問題。Lab 01 約 4 分鐘 MCP baseline、6 分鐘 Client App 介面，Lab 02 同步處理核准。每關結束回報成功／卡住；卡住的學員直接啟動下一關完成版，保留主線時間。

課後停用工作坊 Client／帳號、撤銷尚有效的授權、清理臨時資料。保留教材與匿名化問題紀錄供下一場改進。Device Flow 已移出六關主線，活動頁的現場承諾需由講師同步調整。
