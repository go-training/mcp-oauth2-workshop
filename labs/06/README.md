# Lab 06：Kong MCP Gateway

[課程首頁](../../README.md) · [Go 入口](../../go/labs/06/main.go) · [Python 入口](../../python/labs/06/main.py)

完整實作：[Go](../../go/internal/workshop/server.go) / [Python](../../python/workshop/server.py)。每關都可直接執行，不需從上一關複製程式。

所有指令從 repo 根目錄執行。每個終端先選語言並載入設定：

```bash
export LAB_LANGUAGE=go  # 或 python
set -a
source .env
set +a
```

## 架構目的

最後才加入 Kong：當有許多 MCP Server，共通的 discovery、JWT 驗證與入口 scope 可集中管理；個別工具和資料權限仍由 MCP Server 負責。

這關的 Go/Python backend 不自行驗 JWT，而是驗證 Gateway 共享憑證並讀取可信任身分。Compose 不發布 backend port，使用私有 network；Kong 覆寫 Gateway 憑證並驗證外部 Token。Kong admin API 關閉。

## 操作

先停止 Lab 04 的 A/B Server（若曾啟動其他 Lab，也請先停止）。確認 `docker info` 與 `docker compose version` 成功；只有 Compose 指令存在、daemon 沒啟動仍不能操作。

課前在實際操作電腦下載／編譯映像（Go 路線也要有 `python3` 執行設定產生器）：

```bash
# 課前執行，可能需要數分鐘與網路；LAB_LANGUAGE 選 go 或 python。
docker compose --env-file .env -f labs/06/compose.yml --profile "$LAB_LANGUAGE" build
```

課堂啟動使用 `--no-build`，避免重抓 GitHub build context。若提示 image 不存在，先完成上面的課前建置。Docker Compose v2 以上必須可用。從 repo 根目錄、已載入 `.env` 的終端執行：

```bash
python3 scripts/configure_gateway.py
# 產生的 labs/06/.runtime/kong.yml 與 .env 都含本機憑證，已被 Git 忽略。
# 選一個 profile，不要同時啟動 go 與 python。
docker compose --env-file .env -f labs/06/compose.yml --profile "$LAB_LANGUAGE" up --no-build -d --wait --wait-timeout 120
curl -i http://localhost:9000/mcp
curl -s http://localhost:9000/.well-known/oauth-protected-resource/mcp
```

`--wait` 會等待容器就緒；若逾時先看下方 logs，不要立刻把 Empty reply 誤判成 OAuth 失敗。

預期 401 與正確 PRM。Kong 的 resource 是 `http://localhost:9000/mcp`，你必須事先在自己的 Signet App 加入這個 allowed resource。

```bash
./scripts/oauth.sh "$LAB_LANGUAGE" login --resource http://localhost:9000/mcp --scopes 'notes:read notes:write' --token-file .tokens/lab06.json
./scripts/oauth.sh "$LAB_LANGUAGE" call --resource http://localhost:9000/mcp --token-file .tokens/lab06.json
./scripts/oauth.sh "$LAB_LANGUAGE" call --resource http://localhost:9000/mcp --token-file .tokens/lab06.json --tool create_note --text '經過 Kong'
```

在 Claude Code／Codex 新增另一個名稱 `workshop-gateway`，URL 改成 `http://localhost:9000/mcp`，沿用 [public Client 登入方式](../../docs/clients.md)。必須重新為 Gateway resource 授權，不能沿用 8000 的 Token。

### 可直接執行的拒絕測試

```bash
./scripts/oauth.sh "$LAB_LANGUAGE" login --resource http://localhost:9000/mcp --scopes notes:read --token-file .tokens/lab06-read.json
./scripts/oauth.sh "$LAB_LANGUAGE" call --resource http://localhost:9000/mcp --token-file .tokens/lab06-read.json --tool create_note --text '應被拒絕'
# 預期 403，非零退出是成功驗收。
./scripts/oauth.sh "$LAB_LANGUAGE" login --resource http://localhost:8000/mcp --scopes notes:read --token-file .tokens/lab06-a.json
./scripts/oauth.sh "$LAB_LANGUAGE" call --resource http://localhost:9000/mcp --token-file .tokens/lab06-a.json --allow-cross-resource
# 預期 401。先確認上一步已成功存檔，否則只是在測試沒有 Token。
```

## 對照與練習

- 檢查 [Kong 設定產生器](../../scripts/configure_gateway.py)：issuer、resource path、required scopes。
- PRM 路徑與 `/mcp` 都需要匹配 Kong route，`strip_path=false` 保留後端的 `/mcp`，`preserve_host=true` 保留 Client 入口 Host。
- Go `authorize` / Python `Authorization.__call__` 的 Lab 06 分支顯示 Gateway 信任邊界。
- 使用只含 `notes:read` 的新 Token，`create_note` 仍由 backend 回 403。
- 用 A（8000）的 Token 打 Gateway（9000），應回 401。
- 直接傳 `X-MCP-Subject: admin` 不能偽造身分；共用 header 只在 Gateway 信任邊界內使用。

## 撤銷限制

本次固定版本的 plugin 只做離線 JWT 驗證，**不具備即時撤銷能力**。不要以「接上 Kong」推論已解決撤銷；課堂提醒此限制即可；撤銷與 introspection 的取捨留到課後選修 [Lab 05](../05/README.md)，本 repo 不修改 plugin。

## 驗收與清理

兩種 backend 各自透過 Kong 成功呼叫，錯 audience 被拒、工具 scope 仍有效、後端沒有 host port。容器實測狀態見 [驗證紀錄](../../docs/validation.md)。

```bash
docker compose --env-file .env -f labs/06/compose.yml --profile "$LAB_LANGUAGE" logs --tail 50
docker compose --env-file .env -f labs/06/compose.yml --profile "$LAB_LANGUAGE" down
```
