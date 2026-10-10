# 常見問題

| 現象 | 先檢查 |
| --- | --- |
| address already in use | 停止上一關，或依 Lab 04 同時修改 LISTEN_ADDR 與 MCP_RESOURCE |
| metadata discovery failed | 新終端是否載入 .env；issuer 是否為真正 HTTPS 網址；DNS / TLS 是否可達 |
| issuer mismatch | BASE_URL、metadata issuer、JWT iss 必須逐字一致 |
| invalid_target | Signet public Client 的 allowed_resources 是否包含精確 URL；localhost 與 127.0.0.1 不相同 |
| invalid_scope | 使用管理員預先建立的 public Client，確認允許 notes:read / notes:write；不是未核准 DCR Client |
| redirect mismatch | 核對 Client 實際產生的 host、port、path 與預先註冊值；不要使用萬用 callback 放寬 |
| Lab 02 一直 401 | 這是設計，下一關才開始接受 Token |
| Lab 03 401 | Token 必須是 RS256 access token；檢查 issuer、audience、expiry、kid，勿使用 refresh / ID token |
| 寫入回 403 | 確認 Token 同時具有 notes:read 與 notes:write，重新授權後使用新檔案 |
| Lab 05 503 | introspection 是否可達、confidential credentials 是否有效；不要停用檢查來放行 |
| 撤銷 API 200 但還能用 | 是否其實在跑 Lab 03/04/06？是否 AI CLI 自動取得新 Token？用同一 token file 呼叫 Lab 05 |
| Kong 502 | backend profile 是否啟動、network alias mcp 是否只有一個服務使用 |
| Kong config 無法讀取 | 重新執行 configure_gateway.py；.runtime 目錄 0700，config 0644，唯讀 bind mount |
| Python 421 Invalid Host | 使用 repo 的 preserve_host=true route；不要停用 DNS rebinding protection |
| Go/Python 原始碼能跑但 AI 沒用工具 | 查看 /mcp 連線及工具紀錄，明確要求使用 whoami；用參考 Client 分離模型選擇與協定問題 |
| token file exists | 參考 Client 刻意不覆寫，指定新的 --token-file |
| WSL callback 無法連回 | 用瀏覽器檢查 localhost 導流與防火牆；必要時依 AI CLI 官方流程手動提交 callback，切勿貼到公開聊天 |

不要把完整 Token、Client secret、登入 callback URL 放進 issue。可以提供去識別的 HTTP 狀態、錯誤代碼、Lab/語言/CLI 版本與 request 時間。
