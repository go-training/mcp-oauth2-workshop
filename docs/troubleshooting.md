# 常見問題

| 現象                                   | 先檢查                                                                                                 |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| address already in use                 | 停止上一關，或依 Lab 04 同時修改 LISTEN_ADDR 與 MCP_RESOURCE                                           |
| metadata discovery failed              | 新終端是否載入 .env；issuer 是否為真正 HTTPS 網址；DNS / TLS 是否可達                                  |
| issuer mismatch                        | SIGNET_ISSUER、metadata issuer、JWT iss 必須逐字一致                                                   |
| invalid_target                         | Signet public Client 的 allowed_resources 是否包含精確 URL；localhost 與 127.0.0.1 不相同              |
| invalid_scope                          | 在自己的 App 編輯頁加入 notes:read / notes:write；Codex 首次 add 另需 openid profile email             |
| App 是 pending                         | App 建立後應立即啟用；仍顯示 pending 時找助教確認，先繼續 Lab 02，必要時改用備援 ID               |
| OAUTH_CLIENT_ID is still the placeholder | 編輯 `.env` 填入自己的 Client ID，再 `set -a; source .env; set +a`                                   |
| authorization denied: invalid_scope    | 冒號後是 Signet 回傳的原因；依上方 invalid_scope / invalid_target 列處理                               |
| UI 不能新增 notes scope / resource     | 可自行新增；輸入後按 Enter，若沒有欄位請助教協助，詳見 [Client App 教學](signet-client-app.md) |
| redirect mismatch                      | 核對 Client 實際產生的 host、port、path 與預先註冊值；不要使用萬用 callback 放寬                       |
| Lab 02 一直 401                        | 這是設計，下一關才開始接受 Token                                                                       |
| Lab 03 401                             | Token 必須是 RS256 access token；檢查 issuer、audience、expiry、kid，勿使用 refresh / ID token         |
| 寫入回 403                             | 確認 Token 同時具有 notes:read 與 notes:write，重新授權後使用新檔案                                    |
| 撤銷 API 200 但還能用                  | Lab 03–05 與 Kong 都離線驗 JWT，不查撤銷狀態；尚未到期的 Token 仍可能通過，不代表撤銷 API 失效                 |
| Kong 啟動後 Empty reply                | 使用 Compose `up -d --wait --wait-timeout 120`；逾時看容器 logs                                        |
| CLI OAuth session expired              | 先登入 Claude／Codex 本身的模型帳號；MCP Connected 不代表模型帳號有效                                  |
| Go tools fetch failed、audience schema | 更新教材到修正版本並重啟 Server；舊版 whoami 的 boolean schema 不相容 Claude                           |
| Kong 502                               | backend profile 是否啟動、network alias mcp 是否只有一個服務使用                                       |
| Kong config 無法讀取                   | 重新執行 configure_gateway.py；.runtime 目錄 0700，config 0644，唯讀 bind mount                        |
| Kong 回 401 untrusted_gateway          | 重跑 configure_gateway.py 可能產生新 secret；先重新 `source .env`，再 `up --no-build --force-recreate -d --wait` 讓 Kong 與 backend 同步 |
| Kong 回 401 invalid_gateway_identity   | `.env` 的 SIGNET_ISSUER 需與產生 Kong 設定時相同；backend 的 MCP_RESOURCE 必須是 `http://localhost:9000/mcp` |
| 啟動 Lab 03–05 即 configuration failed / discovery failed | Server 啟動時必須連得到 Signet；先 `curl -sI https://signet.wu-boy.com`，不通請舉手，暫時跟看講師畫面 |
| Python 421 Invalid Host                | 使用 repo 的 preserve_host=true route；不要停用 DNS rebinding protection                               |
| Go/Python 原始碼能跑但 AI 沒用工具     | 查看 /mcp 連線及工具紀錄，明確要求使用 whoami；用參考 Client 分離模型選擇與協定問題                    |
| token file exists                      | 參考 Client 刻意不覆寫，指定新的 --token-file                                                          |
| WSL callback 無法連回                  | 用瀏覽器檢查 localhost 導流與防火牆；必要時依 AI CLI 官方流程手動提交 callback，切勿貼到公開聊天       |

不要把完整 Token、Client secret、登入 callback URL 放進 issue。可以提供去識別的 HTTP 狀態、錯誤代碼、Lab/語言/CLI 版本與 request 時間。
