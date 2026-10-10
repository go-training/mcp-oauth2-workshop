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

## 操作

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

## 觀察與練習

- 找到 `initialize`、`tools/list`、`tools/call`；理解 Client / Server 的角色即可，不從零實作 JSON-RPC。
- 在 Go 的 `NewHandler` / Python 的 `create_app` 找到三個工具定義，修改 `whoami` 的描述並重啟。
- 思考：如果這是公司的工具，誰能呼叫？Client 傳入 `X-MCP-Subject` 能代表真實身分嗎？後面各關都不能信任這種自稱身分。

## 驗收

Server 正常回應；兩種程式路線都能呼叫三個工具；AI CLI 確實發出工具請求。此關沒有授權，只綁定本機，不對外開放。
