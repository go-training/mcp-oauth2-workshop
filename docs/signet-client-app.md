# 學員操作：登入 Signet，建立自己的 Client App

這是 Lab 01 的一部分，Go / Python 共用同一份步驟。主流程使用**你自己建立、設定完整且已啟用的 public Client App**；講師共用 App 只作為備援。

服務：[https://signet.wu-boy.com](https://signet.wu-boy.com/)。

> 2026-10-11 已核對 Signet `v1.6.0-2-gc4d3d86`：註冊頁顯示新 App 立即啟用，提供自訂 scopes 與允許的資源。此次使用既有管理員帳號的前台介面；一般學員身分仍需課前複核。若部署改為審核制，以畫面狀態為準。

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

一人一個 App。建議用座位編號命名，方便助教識別，例如 `hwdc-2026-seat-023`；兩種語言與兩套 CLI 可以共用同一個自己的 Client ID。

| 欄位 | 填寫內容 | 原因 |
| --- | --- | --- |
| 應用程式名稱 | `hwdc-2026-seat-023`，換成自己的編號 | 講師能找到你的申請 |
| 描述 | `HWDC MCP Authorization workshop; Go` 或 `Python` | 練習編輯 App 的基本資料 |
| Client 類型 | **公開 — SPA、CLI、行動應用程式（需要 PKCE）** | CLI 不持有 client secret |
| 授權類型 | 勾選 **授權碼流程 / Authorization Code Flow** | 本課使用瀏覽器 + PKCE |
| 裝置授權流程 / Device Flow | 取消勾選（新表單可能預設勾選） | 不在六關主線使用 |
| Client Credentials Flow | 不勾選 | 這是使用者授權練習 |
| Personal API Key | 不啟用 | 本課不用固定 API key 取代 OAuth |
| 權限範圍 | 保留 `email profile`，加入 `openid notes:read notes:write` | Codex add 首次可能申請標準 scopes；MCP 使用 notes scopes |

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

`localhost` 與 `127.0.0.1` 必須照填；不要加結尾 `/`。這些是**瀏覽器回到 CLI 的位置**，不要填 MCP 的 `http://localhost:8000/mcp`。

### Scopes 與允許的資源

1. 點 `openid`；在「權限範圍」分別輸入 `notes:read`、`notes:write`，每筆按 Enter，確認變成標籤。
2. 在「允許的資源 (RFC 8707)」逐筆輸入以下 URL 並按 Enter：

```text
http://localhost:8000/mcp
http://localhost:8001/mcp
http://localhost:9000/mcp
```

Allowed Resources 必須包含完整的 `http://localhost:PORT/mcp`，不要只填 `8000/mcp`，也不要加結尾斜線或把 `localhost` 換成 `127.0.0.1`。這三筆分別對應主 Server、Lab 04 的 Server B、Lab 06 的 Gateway，必須與 Client 送出的 resource 完全一致。

3. 確認三個 callbacks、三個 resources、五個 scopes 都已形成標籤，才按「註冊應用程式」。留在輸入框的文字不等於已加入。
4. 新版註冊頁說明建立後立即啟用；提交後仍要以詳情實際顯示的狀態為準。若為 pending，請講師處理，先完成 Lab 02。

**檢查點 B：** 取得 Client ID，public App 沒有 secret，狀態為 active／啟用。

## 3. 複核儲存結果，再練習編輯

1. 開啟 App 詳情，複製 **Client ID**；名稱不是 ID。
2. 進入編輯頁，核對 public、Authorization Code 已勾、三個 callbacks 與三個 resources 都有保存。**本次新版仍重現：建立時取消 Device Flow，首次編輯卻再次勾選。請在編輯頁取消，按更新後再開編輯頁確認已關閉。** 這是介面狀態問題，不要直接推論 Device Flow endpoint 已可用。
3. 已保存的 `notes:read notes:write` 會出現在「已儲存的自訂與管理 scopes」，一般 Owner 無法移除；修改描述時會保留。不要因為不在可編輯標籤列就重複新增。
4. 把描述補上語言與 CLI，例如 `HWDC MCP workshop; Python; Codex`，按「更新應用程式」，再回詳情確認。
5. 若缺 scopes 或 resources，回自己的編輯頁補齊；找不到欄位或狀態仍 pending 才請助教處理。不需要為此換成 confidential App。

**只看到 active 還不夠**：缺少自訂 scopes 會出現 `invalid_scope`；resources 留空會出現 `invalid_target`。callbacks 是回 CLI 的位置，resources 是 Token 的接收對象，兩組 URL 不可交換。

**檢查點 C：** 狀態、流程、scopes、callbacks、resources 五項全部正確。

## 4. 將自己的 Client ID 接回教材

編輯 repo 根目錄的 `.env`，將建立完成的 ID 貼到：

```dotenv
SIGNET_ISSUER=https://signet.wu-boy.com
OAUTH_CLIENT_ID=貼上自己的已啟用ClientID
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

1. 回到「我的應用程式」，開啟自己的 App 與「已授權的使用者」頁，觀察登入後的授權紀錄。
2. 分辨「App 允許申請的 scopes」和「你這次實際同意的 scopes」。Lab 04 再申請 write 後重新比較。
3. 在個人帳號的「已連線應用程式」查看自己的 Token／連線紀錄；Lab 05 仍以同一個 token file 驗證撤銷，避免 AI CLI 自動重新登入後誤判。
4. 不操作其他學員的 App 或 Token，也不為了重練刪除整個 App。

**檢查點 E：** 能說明帳號、Client App、授權紀錄和 Access Token 的差別。

## 備援：自己的 App 尚未設定完成

講師可以提供共用 **public** Client ID，讓你先完成後續 Lab。共用的是應用程式識別；**每位學員仍登入自己的帳號，各自取得 Token**。

參考 Client 可以只對這一次指令指定備援 ID，保留 `.env` 中自己的 ID：

```bash
./scripts/oauth.sh "$LAB_LANGUAGE" login --client-id '講師提供的共用PublicClientID' --scopes notes:read --token-file .tokens/fallback-read.json
./scripts/oauth.sh "$LAB_LANGUAGE" call --token-file .tokens/fallback-read.json
```

AI CLI 備援用新名稱 `workshop-fallback`，將 [Client 指南](clients.md) 的 public Client ID 換成共用 ID。自己的 App 設定完成後，以自己的 ID 新增 `workshop-personal` 並重新授權；舊 Token 不會因為你改了 `.env` 就變成由新 App 簽發。

不要共用登入帳號、Token、confidential Client secret 或講師管理員帳密。Lab 05 introspection 憑證仍由講師另行提供，不能用自己的 public Client ID 取代。

## 常見卡點

| 現象 | 處理 |
| --- | --- |
| pending 還不能登入 | 請講師完成設定與核准，先繼續 Lab 02 |
| notes scopes 不在標籤列 | 查看「已儲存的自訂與管理 scopes」；新 scope 在輸入框按 Enter 新增 |
| 找不到 Allowed Resources | 新版在 callbacks 下方；確認頁面版本並請助教協助 |
| 建立時要求 redirect URI | 勾選 Authorization Code，新增三個 callback 標籤 |
| public App 沒有 secret | 正常，PKCE 不需要共用 secret |
| active 後仍 invalid_target | 回編輯頁核對三個完整 resource URL，不要跳過 audience 驗證 |
| 同意畫面是講師的 App 名稱 | CLI 還在用備援 ID；新增自己的 entry 再登入 |
| 修改 ID 後 whoami 一樣 | 正常，subject 代表登入使用者，不是 Client ID；以同意畫面的 App 名稱及 App 授權紀錄確認 |

## 現場彩排

現場一般使用者畫面與完整自助建立流程仍須依 [彩排清單](instructor.md) 驗證。學員不需要存取 Signet 原始碼。
