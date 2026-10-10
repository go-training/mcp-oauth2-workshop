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

## 操作 B：登入 Signet，建立自己的 Client App（約 6 分鐘）

依 [學員 Client App 逐步教學](../../docs/signet-client-app.md) 操作：

1. 登入 `https://signet.wu-boy.com`，開啟「開發 → 我的應用程式 → 註冊新應用程式」。
2. 建立 `hwdc-2026-seat-你的編號`，選 **public**、啟用 **Authorization Code Flow**，取消預設 Device Flow，填入教學列出的三個 callbacks。
3. 建立階段先選 `openid`，取得自己的 Client ID，查看 pending 狀態，再練習修改 App 描述。
4. 將座位編號、App 名稱與 Client ID 交給講師核准，繼續 Lab 02；此時不要期待 pending App 可以登入。

`notes:read` / `notes:write` 和 Allowed Resources 由講師在你的 App 上設定。核准後把自己的 ID 放入 `.env`，Lab 03 使用；若尚未完成核准，先用講師共用 public App 備援。App 的 public 是 OAuth 類型，並不代表所有人都能管理你的 App。

## 觀察與練習

- 找到 `server/discover`、`tools/list`、`tools/call`（2026-07-28 版沒有 `initialize` 交握）；理解 Client / Server 的角色即可，不從零實作 JSON-RPC。
- 在 Go 的 `NewHandler` / Python 的 `create_app` 找到三個工具定義，修改 `whoami` 的描述並重啟。
- 思考：如果這是公司的工具，誰能呼叫？Client 傳入 `X-MCP-Subject` 能代表真實身分嗎？後面各關都不能信任這種自稱身分。

## 驗收

所選語言的 Server 正常回應，能呼叫三個工具；AI CLI 確實發出工具請求。另已用自己的帳號建立 public App，取得 Client ID 並提交核准。此關沒有授權，只綁定本機，不對外開放。
