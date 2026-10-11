# Lab 05：用 public Client 撤銷 Token（課後選修）

[課程首頁](../../README.md) · [Go 參考 Client](../../go/cmd/oauth/main.go) · [Python 參考 Client](../../python/workshop/oauth.py)

本關不列入 90 分鐘主課。主課完成 Lab 04 後，直接前往 [Lab 06](../06/README.md)。

## 練習目標

**沿用既有 public Client App，登入取得 Token，再撤銷它；不需申請另一個 App，也不需 Client secret。** 本關直接操作 Signet，不需要啟動 MCP Server。

Public Client 的撤銷請求包含 `client_id` 與要撤銷的 Token。Signet 會確認 Token 屬於提出請求的 Client。`INTROSPECTION_CLIENT_ID`、`INTROSPECTION_CLIENT_SECRET` 均不需要設定；本關不使用 introspection。

## 操作：登入，再撤銷

### 1. 載入既有設定

所有指令從 repo 根目錄執行，Go 或 Python 選一種即可。沿用先前 Lab 的 `.env` 與 `OAUTH_CLIENT_ID`：

```bash
export LAB_LANGUAGE=go  # 或 python
set -a
source .env
set +a
```

自己的 App 應已允許 `notes:read`、resource `http://localhost:8000/mcp`，以及 callback `http://127.0.0.1:8765/callback`。

### 2. 取得一顆新的 Token

```bash
./scripts/oauth.sh "$LAB_LANGUAGE" login --resource http://localhost:8000/mcp --scopes notes:read --token-file .tokens/lab05.json
```

完成瀏覽器登入與同意授權後，終端應顯示 Token 已儲存。若檔案已存在，請換一個未使用的檔名，後續指令也使用相同路徑。不要輸出或分享 Token 內容。

### 3. 撤銷剛取得的 Token

```bash
./scripts/oauth.sh "$LAB_LANGUAGE" revoke --token-file .tokens/lab05.json
```

**預期：** 顯示 `Revocation accepted`，表示 Signet 的撤銷端點回應 HTTP 200。

參考 Client 會從 metadata 找到撤銷端點，以 form 傳送 `client_id`、`token` 與 `token_type_hint=access_token`。`client_id` 來自 `OAUTH_CLIENT_ID`；若登入時用 `--client-id` 指定其他 ID，撤銷時也必須指定相同 ID。不需傳送 secret。

本指令撤銷的是 Token 檔案中的 **access token**。若手動撤銷 refresh token，應送出該 refresh token，並改用 `token_type_hint=refresh_token`；不能只改 hint 而仍傳入 access token。

### 4. 再撤銷一次，觀察回應

```bash
./scripts/oauth.sh "$LAB_LANGUAGE" revoke --token-file .tokens/lab05.json
```

**預期：** 仍顯示 `Revocation accepted`。依 [RFC 7009](https://www.rfc-editor.org/rfc/rfc7009.html#section-2.2)，成功撤銷、未知或已撤銷的 Token 都可能回 200；Signet 仍會先檢查 Client。

**檢查點：** 撤銷不會刪除本機 Token 檔案，API 回 200 也不代表每個 MCP Server 已立即拒絕它。

## 為什麼撤銷後，MCP 不一定立刻回 401？

本教材的 Lab 03–05 Server 與 Lab 06 Gateway 都使用離線 JWT 驗證。撤銷不會改變 Token 原本的簽章，所以尚未到期、也符合其他檢查的 Token，仍可能通過。

**本關驗收撤銷請求成功，不要求撤銷後呼叫 MCP 立即回 401。** 若系統需要即時拒絕，必須另外設計狀態查詢或其他撤銷傳播機制，這不在本關實作範圍。

### 選做：觀察離線驗證的限制

想親眼觀察時，先停止其他使用 8000 port 的 Server，在終端 A 選好語言並載入 `.env`，啟動保留的 Lab 05 Server 入口：

```bash
./scripts/lab.sh 05 "$LAB_LANGUAGE"
```

它沿用 Lab 04 的 JWT、scope 與資料權限檢查，不查詢 introspection，也不需要額外憑證。終端 B 載入相同設定，使用另一個未使用的 Token 檔名：

```bash
./scripts/oauth.sh "$LAB_LANGUAGE" login --resource http://localhost:8000/mcp --scopes notes:read --token-file .tokens/lab05-offline.json
./scripts/oauth.sh "$LAB_LANGUAGE" call --resource http://localhost:8000/mcp --token-file .tokens/lab05-offline.json
./scripts/oauth.sh "$LAB_LANGUAGE" revoke --token-file .tokens/lab05-offline.json
./scripts/oauth.sh "$LAB_LANGUAGE" call --resource http://localhost:8000/mcp --token-file .tokens/lab05-offline.json
```

撤銷前後使用同一顆 Token。只要尚未到期且其他檢查仍通過，最後一次 call 預期仍成功；這展示 Server 沒有查詢撤銷狀態，不能據此判定撤銷 API 失效。這是刻意的教學測試，實際 Client 撤銷後應停止使用該 Token。

## 卡住時先檢查

| 現象 | 處理方式 |
| --- | --- |
| 登入失敗 | 檢查 public App 是否啟用、scope／resource／callback 是否正確 |
| Token 檔案已存在 | 改用新檔名，後續指令沿用相同路徑 |
| revoke 提示缺少 Client ID | 重新載入 `.env`，確認 `OAUTH_CLIENT_ID` 有值 |
| revoke 被拒絕 | 確認 Client ID 與取得 Token 時一致，且 App 仍有效 |
| 舊版 Server 要求 introspection 憑證 | 更新教材程式；目前版本已移除此需求 |
| 選做的 call 回 401 | 檢查 Token 是否過期、resource 是否一致；不能只看 401 就認定是撤銷生效 |

## 驗收與結束

- [ ] 使用既有 public Client App 完成登入與撤銷，不需 secret 或另一個 App。
- [ ] 第一次與重複撤銷都得到 `Revocation accepted`。
- [ ] 能說明「Signet 接受撤銷」與「MCP Server 立即拒絕」是兩件事。

選做有啟動 Server 的學員，完成後在終端 A 按 `Ctrl-C` 停止。Token 檔案不需提交到 Git，也不要把內容貼到聊天中。
