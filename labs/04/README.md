# Lab 04：scope 與 audience 隔離

[課程首頁](../../README.md) · [Go 入口](../../go/labs/04/main.go) · [Python 入口](../../python/labs/04/main.py)

完整實作：[Go](../../go/internal/workshop/server.go) / [Python](../../python/workshop/server.py)。每關都可直接執行，不需從上一關複製程式。

所有指令從 repo 根目錄執行。每個終端先選語言並載入設定：

```bash
export LAB_LANGUAGE=go  # 或 python
set -a
source .env
set +a
```

## 操作：scope

先在終端 A 按 `Ctrl-C` 停止 Lab 03，再啟動本關。以下 Server A 用終端 A，Client 用終端 B，稍後 Server B 用終端 C；三個終端都先載入設定。

```bash
./scripts/lab.sh 04 "$LAB_LANGUAGE"
```

另一個終端：

```bash
./scripts/oauth.sh "$LAB_LANGUAGE" login --scopes notes:read --token-file .tokens/lab04-read.json
./scripts/oauth.sh "$LAB_LANGUAGE" call --token-file .tokens/lab04-read.json --tool list_notes
./scripts/oauth.sh "$LAB_LANGUAGE" call --token-file .tokens/lab04-read.json --tool create_note --text '應該被拒絕'
# 上一步預期 403，指令非零退出是練習成功，不是程式故障。
./scripts/oauth.sh "$LAB_LANGUAGE" login --scopes 'notes:read notes:write' --token-file .tokens/lab04-write.json
./scripts/oauth.sh "$LAB_LANGUAGE" call --token-file .tokens/lab04-write.json --tool create_note --text '取得寫入權限後成功'
```

觀察 `403` 的 `WWW-Authenticate` 中 `error=insufficient_scope` 及所需 scopes。Server 在 HTTP middleware 檢查 `tools/call` 的工具名稱，讓 Client 看得到 transport 層 challenge；工具 handler 再檢查一次，避免日後更動 transport 時漏掉業務權限。

## 操作：resource / audience

保持 A 在 8000，另一個終端啟動 B：

```bash
MCP_RESOURCE=http://localhost:8001/mcp LISTEN_ADDR=127.0.0.1:8001 ./scripts/lab.sh 04 "$LAB_LANGUAGE"
```

從 Client 終端送 A 的 Token 給本機 B，這是明確的負向測試：

```bash
./scripts/oauth.sh "$LAB_LANGUAGE" call --resource http://localhost:8001/mcp --token-file .tokens/lab04-read.json --allow-cross-resource
# 預期 401；這個測試開關僅允許 loopback 目的地。
./scripts/oauth.sh "$LAB_LANGUAGE" login --resource http://localhost:8001/mcp --scopes notes:read --token-file .tokens/lab04-b.json
./scripts/oauth.sh "$LAB_LANGUAGE" call --resource http://localhost:8001/mcp --token-file .tokens/lab04-b.json
```

自己的 App 必須事先允許 A/B 兩個 resource，否則登入階段的 `invalid_target` 不是 Server 驗證 audience 的結果。

## 觀察與練習

Go：`authorize` 的 scope 分支與 `create_note` handler；Python：`Authorization.__call__` 與 `create_note`。JWT audience 從 Lab 03 就有檢查，此關不關閉驗證。

以另一個練習帳號登入並呼叫 `list_notes`，應看不到第一個帳號的筆記。不要交換彼此 Token。

AI CLI 對 step-up 的呈現可能不同：參照 [Client 指引](../../docs/clients.md) 重新授權；不假設兩者都自動升級 scope。上述參考 Client 是可重現的驗收方式。

## 驗收

讀取成功、未授權寫入回 403、補 scope 後寫入成功；A Token 到 B 回 401、B 自己的 Token 成功；筆記依 subject 隔離。

完成後，在終端 A 與 C 分別按 `Ctrl-C`，停止 8000 與 8001；否則 Lab 05 可能遇到 port 被占用。
