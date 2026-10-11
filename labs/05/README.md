# Lab 05：撤銷同一顆 Token（課後進階選修）

[課程首頁](../../README.md) · [Go 入口](../../go/labs/05/main.go) · [Python 入口](../../python/labs/05/main.py)

完整實作：[Go](../../go/internal/workshop/server.go) / [Python](../../python/workshop/server.py)。每關都可直接執行，不需從上一關複製程式。

所有指令從 repo 根目錄執行。每個終端先選語言並載入設定：

```bash
export LAB_LANGUAGE=go  # 或 python
set -a
source .env
set +a
```

本關不列入 90 分鐘主課與主課驗收。主課完成 Lab 04 後，直接前往 [Lab 06](../06/README.md)。本關保留完整程式與操作，供課後研究 Token 撤銷及 introspection。

## 操作

先停止 Lab 04 的 A/B Server。終端 A 啟動本關，終端 B 依序執行登入、呼叫、撤銷、再次呼叫。

課後操作前，先向講師另行取得該組專用 confidential Client 的 introspection 憑證；放入 `.env` 的 `INTROSPECTION_CLIENT_ID` / `INTROSPECTION_CLIENT_SECRET` 並重新載入。這不是 Claude Code／Codex 的 public Client，也不是 Signet 管理員密碼。

載入後先確認兩項都有值，不要用 `echo` 印出 secret：

```bash
test -n "$INTROSPECTION_CLIENT_ID" && test -n "$INTROSPECTION_CLIENT_SECRET" && echo 'introspection 設定已填入'
```

沒有顯示確認文字就先補設定；public Client ID 不能代替這一組憑證。

```bash
./scripts/lab.sh 05 "$LAB_LANGUAGE"
```

另一個終端：

```bash
./scripts/oauth.sh "$LAB_LANGUAGE" login --scopes notes:read --token-file .tokens/lab05.json
./scripts/oauth.sh "$LAB_LANGUAGE" call --token-file .tokens/lab05.json
./scripts/oauth.sh "$LAB_LANGUAGE" revoke --token-file .tokens/lab05.json
./scripts/oauth.sh "$LAB_LANGUAGE" call --token-file .tokens/lab05.json
```

`revoke` 使用登入時的 public Client ID（`OAUTH_CLIENT_ID`，亦可用 `--client-id` 指定），以 form 傳送 `client_id`、`token` 與 `token_type_hint=access_token`，不需要 Client secret。Signet 須確認 Token 屬於提出撤銷請求的 Client。這與 Server 查詢 introspection 時使用的 confidential Client 憑證是兩回事。

本關刻意撤銷 access token，以驗證同一顆 Token 的拒絕結果；若手動撤銷 refresh token，應改送該 Token 並使用 `token_type_hint=refresh_token`。

第一次 call 應回 200；revoke 應顯示 `Revocation accepted`。最後一次必須回 401，而且使用的是**同一個檔案、同一顆 Token**。不要用會自動重新登入／更新 Token 的 AI CLI 作為唯一撤銷證據。

## 觀察與練習

- Go：`active`；Python：`Authorization.active`。先完整驗證 JWT，再向 Signet introspection 查詢 `active`。
- Introspection 回應不一定包含完整 claims；教材只讀取 `active`，身分、scope、audience 仍來自已驗證 JWT。
- 此範例不快取 active 結果。Signet 逾時、回錯誤或 malformed response 時回 503，不能降級為放行。
- 對照 Lab 03：同一顆已撤銷但未到期的 Token，離線驗簽仍可能接受，因為 RSA 簽章沒有失效。
- 日誌顯示允許請求的 subject／jti，以及拒絕原因，沒有 raw token。講師若需要展示管理介面的事件紀錄，應另外彩排並確認網站實際顯示的內容。

## 驗收

有效 → 撤銷 → 401，順序可重現。`./scripts/check.sh` 額外驗證 introspection 不可用時回 503。說得出「撤銷 API 回 200」和「Resource Server 已拒絕」為何是兩件事。
