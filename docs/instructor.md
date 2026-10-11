# 講師：Signet 與現場準備

授權服務使用 **[Signet](https://signet.wu-boy.com/)**。已提供工作坊服務 **https://signet.wu-boy.com**，學員不用自行部署。學員在自己的筆電執行 HTTP MCP 與 Claude Code／Codex，瀏覽器 callback 回到自己的筆電，Signet 不需主動連進學員筆電。

## 服務設定

Signet 由講師維運；本教材只涵蓋公開服務的使用與課程 Client 設定，不包含服務內部部署方式。課前確認 HTTPS、使用者登入、RS256 簽章與 PKCE S256 可用。本 repo 不保存講師管理員憑證。

MCP Server / Kong 只取得公開 JWKS；簽章私鑰不得發給學員。

本次採固定 callback URI，請逐一註冊 [Client 指引](clients.md) 中的完整 URL；`localhost` 和 `127.0.0.1` 不可互換。

## 現場服務與新版學員流程（2026-10-11）

新版 Signet `v1.6.0-2-gc4d3d86` 的前台註冊頁已提供自訂 scopes、Allowed Resources，並明示新 App 立即啟用。不要再安排所有學員等待管理員手動補欄位與核准。既有管理員身分已核對前台欄位；一般非管理員身分仍須課前複核。

Metadata 的 issuer 是 `https://signet.wu-boy.com`，宣告 S256 與 resource indicators；真實 Token 的結果以 [驗證紀錄](validation.md) 最新一節為準。全域 `scopes_supported` 不能證明特定 App 已允許 notes scopes。

## 每組的 Client 與帳號

### 主流程：學員自行建立、儲存後複核

課前寄出 [學員逐步教學](signet-client-app.md)。Lab 01 由學員完成以下欄位，建立後回詳情／編輯頁確認實際保存結果，再練習修改描述。Lab 02 不需要任何 Client ID，可用來排除個別設定問題。

| 設定                                                | 應有的值                                                                                             |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Client type                                         | public                                                                                               |
| Authorization Code Flow                             | enabled                                                                                              |
| Device Flow / Client Credentials / Personal API Key | 不啟用，建立後再複核                                                                                 |
| Scopes                                              | `openid profile email notes:read notes:write`                                                        |
| Redirect URIs                                       | `http://127.0.0.1:8765/callback`、`http://127.0.0.1:8766/callback`、`http://localhost:8767/callback` |
| Allowed resources                                   | `http://localhost:8000/mcp`、`http://localhost:8001/mcp`、`http://localhost:9000/mcp`                |
| Owner                                               | 建立該 App 的學員                                                                                    |
| Status                                              | active／啟用；若仍 pending，請管理員確認部署政策                                                     |
| Skip Consent                                        | 不勾選，保留授權畫面                                                                                 |
| Client secret                                       | public Client 不需要                                                                                 |

標準 scopes 保留給 Codex add 的首次自動 OAuth；真正 MCP 登入仍明確申請 notes scopes。新增 scopes、callbacks、resources 都需按 Enter 成為標籤。已保存的自訂 scopes 在編輯頁有獨立鎖定區塊，修改描述不會移除。

若現場政策重新啟用審核，只處理這場課確認過的 App，核對 owner、scopes、resources 後啟用；不可對全部 pending App 無條件核准。若到 Lab 03 還沒完成，使用以下備援。

### 備援：講師共用 public Client App

講師課前建立 `hwdc-2026-shared-fallback`，設定與上表相同 callbacks、resources，允許 `openid profile email notes:read notes:write` 並確認 active。發放的是 **public Client ID**；每位學員仍用自己的登入帳號、個別同意授權，取得各自 Token。

- 不共用帳號、Token、confidential Client secret 或管理員憑證。
- 學員自己的 App 仍保留並完成設定；備援只是避免課程中斷。
- 切換 Client ID 需要重新登入；AI CLI 用 `workshop-fallback` 與 `workshop-personal` 分開設定，避免沿用舊授權快取。
- 課後由講師停用共用 App，學員不要嘗試管理這個不屬於自己的 App。

這仍是 CLI 使用已註冊 Client ID 的 pre-registration 路線，與自動 DCR / CIMD 不同。本課不使用 DCR / CIMD，學員依教學取得並填入已啟用的 Client ID。

Resource 逐字匹配。相同本機 URL 出現在不同學員電腦是同一個 OAuth resource 識別，**不表示不同筆電已由 audience 隔離**；本課跨資源隔離示範是 8000 / 8001 / 9000 三個識別。學員身分與資料隔離另由 subject 處理；勿交換 Token。

### Confidential introspection Client（課後選修 Lab 05）

90 分鐘主課不發放此憑證。若安排課後選修，再為參與組別建立一組 active confidential Client 憑證，使用 Signet `/oauth/introspect`。不授予管理 API 權限，不使用講師管理員帳密。將 ID/secret 私下提供給該組，放在被 Git 忽略的 `.env`。

教材先驗證 JWT，再只取 introspection 的 `active` 狀態；不要依賴 introspection 回傳完整的身分或權限欄位。選修操作前用每組憑證確認此流程可用。

## 端點核對

實際 URL 由 metadata 發現，不在範例中寫死 host。

| 用途           | Signet 路徑                               | 本課使用                                          |
| -------------- | ----------------------------------------- | ------------------------------------------------- |
| AS metadata    | `/.well-known/oauth-authorization-server` | discovery / PKCE 能力                             |
| OIDC discovery | `/.well-known/openid-configuration`       | metadata fallback                                 |
| JWKS           | `/.well-known/jwks.json`                  | RS256 驗簽                                        |
| Authorize      | `/oauth/authorize`                        | 使用者登入／同意                                  |
| Token          | `/oauth/token`                            | PKCE code 換 Token，帶 resource                   |
| Introspect     | `/oauth/introspect`                       | confidential Client Basic auth，每次請求查 active |
| Revoke         | `/oauth/revoke`                           | public Client：form client_id、token、token_type_hint；選修前確認可完成撤銷        |

`/oauth/revoke` 對不存在或已撤銷的 Token 仍可能回 200；必須再用相同 Token 呼叫 MCP 才能驗收。教材以 Resource Server 的允許／拒絕紀錄驗收；若要展示管理介面的事件紀錄，另行彩排並確認網站實際顯示的內容。

## 課前彩排

- [ ] 固定 Signet 部署版本、issuer、TLS，確認使用者可登入。
- [ ] Metadata 的 issuer 與 JWT `iss` 完全一致，JWKS 有對應 `kid`，access token 使用 RS256。
- [ ] `S256` 被 metadata 宣告；public clients、callbacks、自訂 scopes、三個 resources 都完成設定。
- [ ] Go / Python PKCE 參考 Client 分別登入成功；檢查 Token audience 與所請求 resource 一致。
- [ ] 使用一般學員帳號完成 `/apps/new` → 自填 scopes/resources → active → 編輯複核 → 以自己的 ID 登入；不能只用管理員帳號測 UI。
- [ ] 確認學員可編輯描述；已儲存的 notes scopes 被保留，Owner 無法移除但可新增合法自訂 scopes。
- [ ] 共用備援 App 已跑通，切回學員自己的 ID 時確實重新登入。
- [ ] Claude Code / Codex 各自登入、呼叫工具、重新授權成功；不要只測其中一套。
- [ ] A Token 到 B 被拒；只有 read 的 Token 不能 write。
- [ ] 僅課後選修 Lab 05：撤銷後下一次請求被拒；introspection 失效時回 503，不列為主課開課條件。
- [ ] Kong 的 Go / Python profiles 分別跑過。先停止一個 profile 再啟動另一個。
- [ ] 以接近 60 人同時操作的登入、換 Token、JWKS 流量彩排容量；introspection 僅在安排課後選修時另行彩排。
- [ ] 確認會場 Wi-Fi、DNS、HTTPS、loopback callback 與 WSL2 瀏覽器導流。
- [ ] 凍結教材 commit，預先下載 Go modules、uv dependencies、Kong / backend images。
- [ ] 準備已下載的完成版與關鍵流程錄影作為網路故障備案。

## 現場節奏

13:00–13:25 進場執行 health check、登入 Signet，尚未建立 App 的學員可先依教學填表；13:25 後協助備取學員；13:30 開始 90 分鐘主課。建議 3–4 位助教處理各區環境問題。Lab 01 約 4 分鐘 MCP baseline、6 分鐘 Client App 介面，Lab 02 同步協助設定問題。每關結束回報成功／卡住；卡住的學員直接啟動下一關完成版，保留主線時間。

主課依序為 Lab 01（10 分）、02（15 分）、03（25 分）、04（20 分）、06（10 分），另留 5 分鐘排錯緩衝與 5 分鐘 Q&A。Lab 04 結束後直接進 Lab 06；Lab 05 保留為課後進階選修，不發放 introspection secret、不做撤銷實作驗收。課堂只提醒：「Token 撤銷後，本地驗 JWT 的 Server 不一定立即知道；需要即時撤銷時，再進一步研究 introspection。」

若安排課後選修，另行約定 Client／帳號可用期限與清理時間。課後停用工作坊 Client／帳號、撤銷尚有效的授權、清理臨時資料。保留教材與匿名化問題紀錄供下一場改進。Token 撤銷與 Device Flow 均不列入 90 分鐘主線，活動頁的現場承諾需由講師同步調整。
