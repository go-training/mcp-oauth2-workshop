# Lab 03：Authorization Code + PKCE 與 Token 驗證

[課程首頁](../../README.md) · [Go 入口](../../go/labs/03/main.go) · [Python 入口](../../python/labs/03/main.py)

完整實作：[Go](../../go/internal/workshop/server.go) / [Python](../../python/workshop/server.py)。每關都可直接執行，不需從上一關複製程式。

所有指令從 repo 根目錄執行。每個終端先選語言並載入設定：

```bash
export LAB_LANGUAGE=go  # 或 python
set -a
source .env
set +a
```

## 進入本關前

先依 [Client App 教學](../../docs/signet-client-app.md) 確認自己的 App 已是 active，已加入 `notes:read notes:write` 與三個 allowed resources；把自己的 Client ID 填入 `.env` 並重新載入。若自己的 App 尚未就緒，使用教學中的講師共用 App 備援，不要跳過授權檢查。

## 操作

停止上一關，啟動 JWT 驗證：

```bash
./scripts/lab.sh 03 "$LAB_LANGUAGE"
```

另一個已載入 `.env` 的終端：

```bash
./scripts/oauth.sh "$LAB_LANGUAGE" login --scopes notes:read --token-file .tokens/lab03-read.json
# 開啟終端顯示的授權網址，使用自己的練習帳號登入。
./scripts/oauth.sh "$LAB_LANGUAGE" call --token-file .tokens/lab03-read.json
```

登入指令會持續等待 callback，完成前不要在同一個終端輸入下一行 call。Go 會印出網址供手動開啟；Python 預設也會嘗試開瀏覽器。到 Signet 確認 App 名稱、`notes:read`、8000 resource、8765 callback，再按允許。回到終端看到 `Saved access token` 才執行 call。

若瀏覽器顯示 callback 錯誤，先看終端是否已存檔成功；本次 Chrome 擴充環境曾顯示 ERR_BLOCKED_BY_CLIENT，但 callback 已完成且 Token 換取成功。若未存檔，確認 CLI 仍在等待、port 8765 沒被占用，逾時後用新流程重試，不要重用舊授權網址。

Token 寫入本機 0600 檔案，不輸出 Token 本文。PKCE Client 綁定 `127.0.0.1:8765/callback`；必須先在 Signet 註冊這個 redirect URI。檔案已存在時程式拒絕覆寫，重練請改用新檔名。

接著依 [CLI 授權設定](../../docs/clients.md#lab-03-起預先註冊的-public-client) 用 Claude Code 或 Codex 登入，再呼叫 `whoami`。模型本身不接觸 client secret。

## 觀察與練習

- Go：`verify`、`Discover`；參考 Client 的 `login`。
- Python：`Authorization.verify`、`discover`；參考 Client 的 `login`。
- 從瀏覽器授權 URL 找到 `client_id`、`redirect_uri`、`state`、`code_challenge_method=S256` 與 `resource`。不要展示 callback 的 code。
- Token request 也包含同一個 `resource` 與 `code_verifier`。Client 驗證 state，metadata 不宣告 S256 時拒絕登入。
- Server 使用成熟 JWT 函式庫驗證 RS256、issuer、audience、expiry，並額外檢查 Signet `type=access`、subject。
- `client_id` 是公開識別，不等於 secret。介紹 pre-registration / CIMD / DCR；本次由學員在 UI 註冊自己的 App、複核設定與啟用狀態，CLI 以已取得的 Client ID 進行 pre-registration 路線。

## 驗收

未登入回 401，登入後 `whoami.subject` 是自己的練習身分。使用 `./scripts/check.sh` 可重現偽造簽章、過期、錯 issuer、錯 audience、refresh token 被拒的情境。每一個 HTTP 請求都要帶授權，不能把 MCP session 當成登入憑證。
