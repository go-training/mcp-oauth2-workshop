# Lab 02：授權探索：從 401 找到 Signet

[課程首頁](../../README.md) · [Go 入口](../../go/labs/02/main.go) · [Python 入口](../../python/labs/02/main.py)

完整實作：[Go](../../go/internal/workshop/server.go) / [Python](../../python/workshop/server.py)。每關都可直接執行，不需從上一關複製程式。

所有指令從 repo 根目錄執行。每個終端先選語言並載入設定：

```bash
export LAB_LANGUAGE=go  # 或 python
set -a
source .env
set +a
```

## 操作

先停止 Lab 01；載入講師提供的 `.env`，再啟動：

```bash
./scripts/lab.sh 02 "$LAB_LANGUAGE"
```

另一個終端：

```bash
curl -i http://localhost:8000/mcp
curl -s http://localhost:8000/.well-known/oauth-protected-resource/mcp
./scripts/oauth.sh "$LAB_LANGUAGE" metadata
```

第一個請求預期 `401` 與 `WWW-Authenticate`；依其中 `resource_metadata` 取得 PRM。PRM 的 `resource` 是 `http://localhost:8000/mcp`，`authorization_servers` 指向 Signet；接著查看 Signet 的 `issuer`、`authorization_endpoint`、`token_endpoint`、`jwks_uri`、`code_challenge_methods_supported`。

## 觀察與練習

- Go：`NewHandler` 的 metadata 路由、`authorize` 的 Lab 02 分支、`Discover`。
- Python：`Authorization.__call__` 的 metadata／Lab 02 分支、`discover`。
- PRM 描述受保護資源；AS metadata 描述授權伺服器，兩者不是同一份文件。
- PRM 公開可讀，不需要先登入。兩種 well-known 路徑都提供；Client 應優先使用 challenge 指定的位置。
- 分辨誰回 401、誰顯示登入畫面、誰簽發 Token。

## 驗收

沿著 challenge → PRM → AS metadata 找到正確 Signet，看到 `S256`。本關是 discovery 檢查點，**即使帶有效 Token 也仍回 401**；不要在此關反覆登入或期待 CLI 可用，下一關才啟用驗證。
