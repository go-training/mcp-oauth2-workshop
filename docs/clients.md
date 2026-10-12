# Claude Code / Codex CLI 操作

選一套即可，Go / Python 的 MCP URL 與操作方式完全相同。下列旗標於 **Codex CLI 0.162.1、Claude Code 2.1.263** 的本機 help 核對；真實彩排結果見 [驗證紀錄](validation.md)。舊版本請先升級或以參考 Client 完成練習。

本文件不會自動修改你的 CLI 設定。操作前確認 server 名稱未被其他專案使用；課後只移除這次新增的 workshop entries。

## Lab 01：未授權版本

先啟動所選語言的 Lab 01。

### Claude Code

```bash
claude mcp add --transport http --scope local workshop-open http://localhost:8000/mcp
claude mcp get workshop-open
claude
```

先確認 CLI 本身能正常對話；若顯示模型帳號 OAuth session expired，先完成 CLI 自己的登入，這與 Signet MCP 登入是兩件事。

在互動介面輸入 `/mcp` 檢查連線，然後要求「呼叫 workshop-open 的 whoami，再列出筆記」。確認工具紀錄，而不是只看模型文字。

### Codex CLI

```bash
codex mcp add workshop-open --url http://localhost:8000/mcp
codex mcp list
codex
```

使用 `/mcp` 檢查，再要求呼叫 `whoami`。出現工具執行批准提示時，確認是自己的 workshop Server 再批准本次操作；OAuth 同意與 CLI 工具批准是不同步驟。使用 HTTP URL，不要把範例啟動指令設定成 STDIO MCP。

## Lab 02：只觀察 discovery

此關故意拒絕所有 Token，用 curl 觀察 401 與 metadata 即可。不要陷入 CLI 重複登入循環。

## Lab 03 起：預先註冊的 public Client

先結束正在執行的 AI CLI 互動工作階段，再移除 Lab 01 本次新增的 `workshop-open` entry。只執行所選 CLI 的一行；若當時使用其他名稱，改成該名稱，未新增則略過。

```bash
claude mcp remove --scope local workshop-open
# 或
codex mcp remove workshop-open
```

`workshop-open` 與下方 `workshop-auth` 都指向 8000；移除舊 entry 可避免換關後重複探索、登入提示及同名工具混淆。完成下方設定後重新啟動 CLI，明確要求「呼叫 workshop-auth 的 whoami，再列出筆記」，並查看工具紀錄。

先完成 [建立自己的 Client App](signet-client-app.md)，自行補齊 scope、resource 並確認 active 後啟動 Lab 03，從 repo 根目錄載入 `.env`。`OAUTH_CLIENT_ID` 優先使用自己的 public App ID；設定尚未完成時才用講師共用的備援 ID。public Client 不需要 secret；Lab 05 撤銷也沿用同一個 public Client ID。

學員建立 App 時填入下列**精確** callback，建立後重新開啟編輯頁複核；共用備援 App 也使用相同設定：

| 用途                             | Redirect URI                     |
| -------------------------------- | -------------------------------- |
| 本 repo Go/Python 參考 Client    | `http://127.0.0.1:8765/callback` |
| Codex（以下指令固定 override）   | `http://127.0.0.1:8766/callback` |
| Claude Code（以下指令固定 port） | `http://localhost:8767/callback` |

### Claude Code

```bash
claude mcp add --transport http --scope local --client-id "$OAUTH_CLIENT_ID" --callback-port 8767 workshop-auth http://localhost:8000/mcp
claude mcp login workshop-auth
claude
```

也可在 `/mcp` 選取 server 進行登入。不要加 `--client-secret`。在 Lab 04 發生 `insufficient_scope` 時，觀察 CLI 是否要求重新授權；必要時從 `/mcp` 清除本機授權後重登。清除本機憑證不作為 Server 已撤銷 Token 的證據。

### Codex CLI

固定 callback，避免預先註冊的 redirect URI 與自動選取的路徑不一致：

```bash
codex -c 'mcp_oauth_callback_port=8766' -c 'mcp_oauth_callback_url="http://127.0.0.1:8766/callback"' mcp add workshop-auth --url http://localhost:8000/mcp --oauth-client-id "$OAUTH_CLIENT_ID" --oauth-resource http://localhost:8000/mcp
codex -c 'mcp_oauth_callback_port=8766' -c 'mcp_oauth_callback_url="http://127.0.0.1:8766/callback"' mcp login workshop-auth --scopes notes:read
codex
```

**第一行可能直接開啟瀏覽器，先完成它再執行第二行。** Codex 0.162.1 的 `mcp add` 首次可能申請 `openid profile email`，因此 App 應保留這三個標準 scopes。完成這次登入不代表已有 notes 權限；第二行 `mcp login --scopes notes:read` 才是 Lab 03 驗收登入。若第一次出現 `invalid_scope`，先在 App 補齊標準 scopes，使用 `mcp get workshop-auth` 確認 entry 是否已保存，避免反覆新增。

Lab 04 需要讀寫時，沿用 callback overrides 重新授權：

```bash
codex -c 'mcp_oauth_callback_port=8766' -c 'mcp_oauth_callback_url="http://127.0.0.1:8766/callback"' mcp login workshop-auth --scopes notes:read,notes:write
```

若本機已有較大 scope 的授權快取，請用參考 Client 的獨立 Token 檔案驗證「只有 read 時必須拒絕 write」，不要以 CLI 的既有登入狀態推論 Server 有問題。

## Lab 04 / 06：新增另一個 resource

沿用以上新增與登入指令，將名稱和 URL 一起更換；Codex 的 `--oauth-resource` 也必須同步更換。

| 場景                 | 名稱               | URL / resource              |
| -------------------- | ------------------ | --------------------------- |
| Lab 04 第二個 Server | `workshop-b`       | `http://localhost:8001/mcp` |
| Lab 06 Gateway       | `workshop-gateway` | `http://localhost:9000/mcp` |

不同 resource 需要各自取得 Token，不能只改連線 URL 然後沿用舊 Token。

## 課後清理

只刪除你實際建立且尚未移除的 workshop entries；Lab 03 前已移除的 `workshop-open` 不需再刪：

```bash
claude mcp remove --scope local workshop-open
claude mcp remove --scope local workshop-auth
codex mcp remove workshop-open
codex mcp remove workshop-auth
```

若另外新增 `workshop-b` / `workshop-gateway`，也以對應名稱移除。依講師流程撤銷練習授權，再刪除本機 `.tokens` 中的練習檔案；不要清空其他工具的憑證庫。

## 依據

- [Claude Code MCP 文件](https://code.claude.com/docs/en/mcp)：HTTP、public client、callback port、登入操作。
- [Codex MCP 文件](https://developers.openai.com/codex/mcp)：新增 HTTP server、OAuth login、callback overrides。
- `codex mcp add --help` / `codex mcp login --help` / `claude mcp add --help`：本機指定版本的實際旗標。
