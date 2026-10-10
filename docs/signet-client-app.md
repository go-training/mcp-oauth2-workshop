# 學員操作：登入 Signet，建立自己的 Client App

這是 Lab 01 的一部分，Go / Python 共用同一份步驟。主流程使用**你自己建立、經講師核准的 public Client App**；講師共用 App 只作為備援。

服務：[https://signet.wu-boy.com](https://signet.wu-boy.com/)。

> 表單欄位與權限依 Signet 原始碼版本 `66f40d5ce6229f8c3f618db98db92286d1379fb8` 核對。目前尚未登入現場網站逐頁彩排；若現場版本或語系不同，請以欄位含義對照，不要為了找不到欄位而改用管理員帳號。

## 先理解三件事

- **你的登入帳號**：代表使用者，Token 中的 subject 對應這個身分。
- **Client App / Client ID**：代表向 Signet 申請授權的應用程式；Client ID 不是使用者帳號，也不是密碼。
- **MCP resource**：代表 Token 要存取哪一個 MCP Server，與 OAuth callback URL 不同。

建立 App 是註冊應用程式；稍後在 CLI 開啟瀏覽器同意授權，才是讓該 App 以你的身分取得 Token。這兩步都要操作。

## 1. 登入自己的帳號

1. 開啟 Signet，使用講師指定的登入方式與自己的練習身分。
2. 確認登入後顯示的是自己的帳號。若登入方式、邀請或帳號啟用未完成，先請助教處理。
3. 在「開發 → 我的應用程式」進入 App 清單；也可直接開啟 [我的應用程式](https://signet.wu-boy.com/apps)。
4. 找到「註冊新應用程式」，或開啟 [建立 App](https://signet.wu-boy.com/apps/new)。

**檢查點 A：** 你看得到自己的 App 清單，而不是講師的管理員 Client 清單。

## 2. 填寫自己的 App

一人一個 App。建議用座位編號命名，方便講師核准，例如 `hwdc-2026-seat-023`；兩種語言與兩套 CLI 可以共用同一個自己的 Client ID。

| 欄位 | 填寫內容 | 原因 |
| --- | --- | --- |
| 應用程式名稱 | `hwdc-2026-seat-023`，換成自己的編號 | 講師能找到你的申請 |
| 描述 | `HWDC MCP Authorization workshop; Go` 或 `Python` | 練習編輯 App 的基本資料 |
| Client 類型 | **公開 — SPA、CLI、行動應用程式（需要 PKCE）** | CLI 不持有 client secret |
| 授權類型 | 勾選 **授權碼流程 / Authorization Code Flow** | 本課使用瀏覽器 + PKCE |
| 裝置授權流程 / Device Flow | 取消勾選（新表單可能預設勾選） | 不在六關主線使用 |
| Client Credentials Flow | 不勾選 | 這是使用者授權練習 |
| Personal API Key | 不啟用 | 本課不用固定 API key 取代 OAuth |
| 可編輯的權限範圍 | 移除預設的 `email`、`profile`，選 `openid` 即可 | 建立階段先選標準 scope；業務 scope 待講師加入 |

### Redirect URIs

把以下三個 URI **分別新增成標籤**，輸入後按 Enter。不要只把文字留在尚未提交的輸入框。

```text
http://127.0.0.1:8765/callback
http://127.0.0.1:8766/callback
http://localhost:8767/callback
```

- 8765：本 repo 的 Go / Python 參考 Client。
- 8766：Codex CLI，教材會固定 callback URL。
- 8767：Claude Code，教材會固定 callback port。

`localhost` 與 `127.0.0.1` 必須照填；不要加結尾 `/`。這些是**瀏覽器回到 CLI 的位置**，不要填 MCP 的 `8000/mcp`。

### 看不到 notes scope 或 Allowed Resources 是正常的

目前一般使用者的表單只允許標準 scopes，不能自行新增 `notes:read` / `notes:write`；Allowed Resources 則由管理員設定。因此建立時不要嘗試貼入自訂 scope、找隱藏欄位或換成 confidential Client。

按「註冊應用程式」提交。

**檢查點 B：** App 出現在「我的應用程式」，狀態是 `pending` / 待審核。public App 沒有 client secret，這是正確結果。

## 3. 操作 App 詳情，交給講師核准

1. 打開自己 App 的詳情，找到並複製 **Client ID**。
2. 進入編輯頁，把描述補上自己選用的 CLI，例如 `HWDC MCP workshop; Python; Codex`，儲存後確認內容。
3. 透過講師指定的現場收集方式提供：座位編號、App 名稱、Client ID。只交識別資訊，不交密碼、Token 或 secret。
4. 繼續 Lab 02 的 discovery 練習。等待期間不反覆送登入請求。

講師會完成：

| 檢查／設定 | 值 |
| --- | --- |
| App owner | 保留為建立它的學員 |
| 類型與流程 | public、Authorization Code enabled |
| Scopes | 保留 `openid`，加入 `notes:read notes:write` |
| Allowed Resources | 以下三個精確 URL |
| 審核狀態 | 完成設定後確認為 `active` |

```text
http://localhost:8000/mcp
http://localhost:8001/mcp
http://localhost:9000/mcp
```

**只改成 active 還不夠**：缺少自訂 scopes 會出現 `invalid_scope`；沒有 allowed resources 會出現 `invalid_target`。

重新整理 App 詳情，確認 active；到編輯頁查看管理員設定的權限。這些業務 scopes 可能顯示為不可編輯，學員仍可修改自己的名稱、描述與 callbacks。

**檢查點 C：** 講師確認該 App 的 scopes、resources、狀態均設定完成。

## 4. 將自己的 Client ID 接回教材

編輯 repo 根目錄的 `.env`，將建立完成的 ID 貼到：

```dotenv
SIGNET_ISSUER=https://signet.wu-boy.com
OAUTH_CLIENT_ID=貼上自己的已核准ClientID
```

保留其他設定，然後在每個需要使用 Client 的終端重新載入：

```bash
set -a
source .env
set +a
export LAB_LANGUAGE=go  # 或 python
```

到了 Lab 03，先啟動 Server：

```bash
./scripts/lab.sh 03 "$LAB_LANGUAGE"
```

另一個已載入設定的終端：

```bash
./scripts/oauth.sh "$LAB_LANGUAGE" login --scopes notes:read --token-file .tokens/my-app-read.json
./scripts/oauth.sh "$LAB_LANGUAGE" call --token-file .tokens/my-app-read.json
```

開啟登入網址時，觀察同意授權畫面中的 **App 名稱應是你自己的 App**；要求的權限是這次 request 的 scopes，不一定是 App 允許申請的全部 scopes。

**檢查點 D：** 登入後 `whoami` 回傳自己的身分；不是只完成建立 App 就算成功。

接著依 [Claude Code / Codex 指南](clients.md) 把相同的 `OAUTH_CLIENT_ID` 設進所選 CLI。請注意舊的 CLI entry 可能保留先前的 Client ID；若要從備援切回自己的 App，使用新的 entry 名稱並重新登入。

## 5. 回到介面觀察授權結果

1. 回到「我的應用程式」，開啟自己的 App 與「授權」頁，觀察登入後的授權紀錄。
2. 分辨「App 允許申請的 scopes」和「你這次實際同意的 scopes」。Lab 04 再申請 write 後重新比較。
3. 在個人帳號的「已連線應用程式」查看自己的 Token／連線紀錄；Lab 05 仍以同一個 token file 驗證撤銷，避免 AI CLI 自動重新登入後誤判。
4. 不操作其他學員的 App 或 Token，也不為了重練刪除整個 App。

**檢查點 E：** 能說明帳號、Client App、授權紀錄和 Access Token 的差別。

## 備援：自己的 App 尚未完成核准

講師可以提供共用 **public** Client ID，讓你先完成後續 Lab。共用的是應用程式識別；**每位學員仍登入自己的帳號，各自取得 Token**。

參考 Client 可以只對這一次指令指定備援 ID，保留 `.env` 中自己的 ID：

```bash
./scripts/oauth.sh "$LAB_LANGUAGE" login --client-id '講師提供的共用PublicClientID' --scopes notes:read --token-file .tokens/fallback-read.json
./scripts/oauth.sh "$LAB_LANGUAGE" call --token-file .tokens/fallback-read.json
```

AI CLI 備援用新名稱 `workshop-fallback`，將 [Client 指南](clients.md) 的 public Client ID 換成共用 ID。自己的 App 核准後，以自己的 ID 新增 `workshop-personal` 並重新授權；舊 Token 不會因為你改了 `.env` 就變成由新 App 簽發。

不要共用登入帳號、Token、confidential Client secret 或講師管理員帳密。Lab 05 introspection 憑證仍由講師另行提供，不能用自己的 public Client ID 取代。

## 常見卡點

| 現象 | 處理 |
| --- | --- |
| pending 還不能登入 | 請講師完成設定與核准，先繼續 Lab 02 |
| 只能選標準 scopes | 正常；notes scopes 由講師加在你原本的 App 上 |
| 找不到 Allowed Resources | 正常；這是管理員欄位 |
| 建立時要求 redirect URI | 勾選 Authorization Code，新增三個 callback 標籤 |
| public App 沒有 secret | 正常，PKCE 不需要共用 secret |
| active 後仍 invalid_target | 請講師檢查 resource 白名單，不要改成跳過 audience 驗證 |
| 同意畫面是講師的 App 名稱 | CLI 還在用備援 ID；新增自己的 entry 再登入 |
| 修改 ID 後 whoami 一樣 | 正常，subject 代表登入使用者，不是 Client ID；以同意畫面的 App 名稱及 App 授權紀錄確認 |

## 欄位與行為來源

核對 [Signet 66f40d5](https://github.com/go-signet/signet/tree/66f40d5ce6229f8c3f618db98db92286d1379fb8)：`internal/handlers/user_client.go`、`internal/templates/user_app_form.templ`、`internal/templates/client_shared.templ`、`internal/services/client_user.go`、`internal/services/client_bulk_approve.go`。現場一般使用者畫面與完整核准流程仍列在 [彩排清單](instructor.md)。
