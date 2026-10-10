# 驗證紀錄

教材基準：MCP Authorization **2025-11-25**。本頁區分已執行的本機驗證與尚待現場服務的彩排，不將 mock 當作 Signet。

## 已執行

- Go 1.26.7：六個 Lab 與參考 OAuth Client 編譯成功，`go vet ./...` 通過。
- Python 3.12.13、uv lock：依賴安裝成功，Ruff 檢查與格式化通過。
- `tests/test_labs.py` 以本機測試 issuer 啟動兩種語言的真實 MCP HTTP Server，測試：
  - 初始化、工具探索、工具呼叫與匿名 baseline。
  - 401 challenge、PRM、AS discovery。
  - RS256、issuer、audience、expiry、subject、access type、偽造 HS256 拒絕。
  - scope 403、寫入成功、不同 subject 筆記隔離、跨 audience 拒絕。
  - 同一 Token 撤銷後拒絕、introspection outage 回 503。
  - Gateway secret 與身分邊界、Python 的 Host 保護。
  - Go/Python PKCE：state 負向驗證、S256、兩次 resource 綁定、0600 token file、呼叫、撤銷。
  - 參考 Client 拒絕非 loopback 明文目的地，正確處理 JSON-RPC error。
- CLI 旗標核對：Codex 0.162.1、Claude Code 2.1.263 的本機 `--help`。
- Kong 設定產生器的私有檔案權限與 `preserve_host` / `strip_path` 有測試。
- 兩個 Docker Compose profiles 均通過 `config --quiet`，不需要 Docker daemon。
- 本次 `./scripts/check.sh`：**33 tests passed**。第三方套件有 Starlette TestClient / Pydantic settings 警告，不影響斷言結果。

執行 `./scripts/check.sh` 取得最新測試數與結果；GitHub Actions 重跑相同檢查。

## 尚未宣稱完成

| 項目 | 原因／完成條件 |
| --- | --- |
| 新的現場 Signet 端到端驗證 | 尚未提供部署 URL、Client 與測試身分；依 instructor checklist 彩排 |
| Claude Code / Codex 瀏覽器登入與 step-up | 目前核對文件與旗標，沒有使用真實課程身分完成互動登入 |
| Kong 容器實際代理 Go / Python | 本機 Docker daemon 未啟動；Compose 設定可檢查，但不是容器 runtime 成功證明 |
| 60 人集中登入容量 | 需在實際授權服務與會場網路條件下壓測 |
| Windows + WSL2 | 需以學員相同環境彩排 callback 導流 |

## 已知設計取捨

- 跨資源 scope 升級由參考 Client 明確重新登入，不假設 AI CLI 自動 step-up。
- Lab 06 使用固定 plugin commit `bafa464e89d6c46bb222dfce1877304f9e62473a`，只做離線 JWT；不含即時撤銷。
- 基礎 HTTP MCP 使用官方 SDK 的 stateless + JSON response，減少 session/SSE 分支，集中教學授權。
- 範例是教學完成版；尚未經真人逐行安全審查，不宣稱已可直接上正式環境。

## 重現

```bash
./scripts/check.sh
```

Signet 原始碼核對版本與課前設定見 [講師手冊](instructor.md)。
