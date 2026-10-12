# Lab 01：MCP 起手式

[課程首頁](../../README.md) · [Go 入口](../../go/labs/01/main.go) · [Python 入口](../../python/labs/01/main.py)

完整實作：[Go](../../go/internal/workshop/server.go) / [Python](../../python/workshop/server.py)。每關都可直接執行，不需從上一關複製程式。

所有指令從 repo 根目錄執行。每個終端先選語言並載入設定：

```bash
export LAB_LANGUAGE=go  # 或 python
set -a
source .env
set +a
```

## 操作 A：連上 MCP（約 4 分鐘）

```bash
./scripts/lab.sh 01 "$LAB_LANGUAGE"
```

另一個終端先設定相同的 `LAB_LANGUAGE`，再操作：

```bash
curl http://localhost:8000/healthz
./scripts/oauth.sh "$LAB_LANGUAGE" call --token-file .tokens/anonymous.json
./scripts/oauth.sh "$LAB_LANGUAGE" call --token-file .tokens/anonymous.json --tool create_note --text '第一個練習'
./scripts/oauth.sh "$LAB_LANGUAGE" call --token-file .tokens/anonymous.json --tool list_notes
```

`.tokens/anonymous.json` 刻意不存在，參考 Client 因此不帶 Token。`whoami` 回 `subject: anonymous`；讀寫任何匿名使用者共用的練習筆記都會成功。

依 [兩套 CLI 指引](../../docs/clients.md#lab-01未授權版本) 接上 Client。輸入：「請使用 workshop 的 whoami 工具，接著列出筆記。」不要把模型自行回答當成工具呼叫成功，要看工具紀錄。

## 操作 B：為 Lab 3 預先準備：登入 Signet，建立自己的 Client App（約 6 分鐘）

這裡登入的是 Signet 的應用程式管理介面，先建立 Lab 3 授權流程所需的 Client App。Lab 1 的 MCP 工具仍可匿名呼叫；Lab 2 只探索授權資訊，不需要 Client ID，也不需登入。直到 Lab 3 才會使用這個 Client ID 進行 OAuth 授權並取得 Token。

依 [學員 Client App 逐步教學](../../docs/signet-client-app.md) 操作：

1. 登入 `https://signet.wu-boy.com`，開啟「開發 → 我的應用程式 → 註冊新應用程式」。
2. 建立 `hwdc-2026-seat-你的編號`，選 **public**、啟用 **Authorization Code Flow**，取消預設 Device Flow。在「Redirect URIs / Callback URLs」逐筆填入以下三個 URL，每筆按 Enter，確認形成三個標籤：

   ```text
   http://127.0.0.1:8765/callback
   http://127.0.0.1:8766/callback
   http://localhost:8767/callback
   ```

   | Port | 本課程用途 |
   | ---- | ---------- |
   | 8765 | `./scripts/oauth.sh` 使用的 Go／Python Client |
   | 8766 | Codex CLI（依教材固定 callback） |
   | 8767 | Claude Code（依教材固定 callback port） |

   這些 URL 是授權完成後瀏覽器回到本機 Client 的位置。請照填 `127.0.0.1` 與 `localhost`，不要互換，也不要加結尾 `/`；MCP 的 `/mcp` URL 請填在下一步的 Allowed Resources。

3. 保留 `email profile`，加入 `openid notes:read notes:write`。在「允許的資源 / Allowed Resources」逐筆複製以下完整 URL，每筆按 Enter，確認形成三個標籤：

   ```text
   http://localhost:8000/mcp
   http://localhost:8001/mcp
   http://localhost:9000/mcp
   ```

   必須包含 `http://`、`localhost`、port 與 `/mcp`；不要加結尾斜線，也不要換成 callback URL 或 `127.0.0.1`。

4. 提交後確認 active，取得 Client ID，進入編輯頁複核流程與所有 URL，再練習修改 App 描述。
5. 將 ID 存入 `.env` 的 `OAUTH_CLIENT_ID`，在 Client 終端重新載入。

App 建立後立即啟用，不需排隊等講師核准。若現場畫面仍是 pending，請助教確認部署政策，可先做 Lab 02 或使用備援 public Client ID。App 的 public 是 OAuth 類型，不代表所有人都能管理你的 App。

## 觀察重點

- 查看 AI CLI 的工具紀錄，確認它確實呼叫了 `whoami`、`list_notes`，並收到 Server 回傳的結果。理解 Client 發出請求、Server 執行工具的角色即可，此時不必記住協定方法名稱。
- 思考：目前任何連上 Server 的人都能讀寫共用筆記，要如何限制？Lab 2 會先探索授權資訊，Lab 3 再加入登入授權與 Token 驗證。

## 選做練習

在 Go 的 `NewHandler` / Python 的 `create_app` 找到三個工具定義，修改 `whoami` 的描述並重啟 Server，重新連線後查看工具描述的變化。這項練習不列入驗收，可略過並繼續下一關。

## 驗收

所選語言的 Server 正常回應，能呼叫三個工具；AI CLI 確實發出工具請求。另已用自己的帳號建立 public App，取得 Client ID 並確認設定完整、狀態 active。此關沒有授權，只綁定本機，不對外開放。
