# 驗證紀錄

教材基準：MCP Authorization **2026-07-28**。本頁只列目前狀態；先前彩排的細節與失敗紀錄保存在 [歷史紀錄](validation-history.md)。歷史紀錄中的 introspection 憑證、撤銷後立即 401 等條件不適用目前 Lab 05。

## 目前狀態（2026-10-12）

「已通過」僅代表下列環境與日期的證據，不代表全部學員環境已驗收。本次程式修正只做本機回歸，沒有重新登入真實 Signet 或操作 AI CLI。

| 項目 | 狀態 | 證據與限制 |
| --- | --- | --- |
| Go／Python 本機檢查與六關整合測試 | 已通過（10/12） | 59 tests passed；本機 issuer 不等於真實 Signet |
| 真實 Signet：Lab 01–04 基本流程 | 已通過（10/11） | 兩語言匿名、discovery、PKCE、scope、audience；不包含第二個真實使用者 |
| public Client 撤銷與重複撤銷 | 已通過（10/11） | 兩語言皆不帶 secret；Lab 05 離線 Server 仍可能接受有效 JWT |
| 真實 Kong：兩語言 backend | 已通過（10/11） | 成功呼叫、403／401、偽造 headers 與私有 backend 邊界 |
| Codex 模型實際呼叫 | 已通過（10/11） | 兩語言 Lab 03 的 whoami／list_notes；自動 step-up 未驗收 |
| Claude 模型實際呼叫 | 待驗證 | MCP 登入及 Connected 已成功，模型帳號過期阻擋實際工具呼叫 |
| 一般學員建立／編輯 Client App | 待驗證，開課前必要 | 先前使用管理員帳號的前台，不能代替一般使用者驗收 |
| 兩個真實使用者的資料隔離 | 待驗證 | 本機 fixture 已測；Lab 04 現為選做／講師示範 |
| Windows／WSL2 callback | 待驗證，開課前必要 | 須用 Windows 瀏覽器回到 WSL2 內的 Client 驗證 |
| 60 人集中登入、會場網路 | 待驗證 | 需要對應環境與事先安排的容量彩排 |

## 本機驗證（2026-10-12）

- 基準 commit：`154873daa79d3211fdb81842de51663a3efa2582` 加本次尚未提交的修正；不可把此 commit 單獨視為修正後版本。
- 環境：macOS arm64、Go 1.26.7、Python 3.12.13、uv 0.10.10；依 repository 鎖檔安裝依賴。
- 修正：Go／Python 在處理 OAuth 成功或錯誤回應前先檢查 `iss`；Python 保留空白 query 值，避免將 `iss=` 視為未提供；Go 等 callback handler 完成回應再關閉 listener。
- 回歸範圍：成功／錯誤 callback、issuer 支援宣告 true／false、缺少／空白／錯誤 issuer。拒絕時不得顯示未驗證的 OAuth 錯誤內容、換 Token 或寫 Token 檔；未宣告支援且缺少 issuer 時保留規範允許的行為。
- 執行結果：`./scripts/check.sh` 通過 Go 格式／vet／tests、Ruff lint／format 與 pytest：**59 passed in 24.73s**（原有 35 個測試加 24 個 callback issuer 案例）。
- 補充檢查：`(cd go && go test -race ./...)` 通過；本輪 8 份文件的 55 個本機檔案連結與 41 個 Bash 區塊語法檢查通過。語法檢查沒有執行教材中的登入或容器操作。

重現：

```bash
./scripts/check.sh
```

## 開課前彩排清單

以下仍是待辦，不能以文件調整或 mock 測試標記完成：

- [ ] 用全新的一般學員帳號建立 public App，保存五個 scopes、三個 callbacks、三個 resources；重新開啟編輯頁核對 active、Device Flow 與設定，完成 PKCE、whoami 及 list_notes。不可使用管理員帳號代替。
- [ ] 重新登入 Claude 模型帳號，分別連 Go／Python Lab 03，確認模型實際呼叫 whoami／list_notes，記錄工具結果；Connected 本身不算通過。
- [ ] 在 Windows + WSL2 依學員步驟操作，確認 Windows 瀏覽器能回到 WSL2 內的參考 Client，以及所選 AI CLI 的 callback。
- [ ] 若示範 Lab 04 帳號隔離，準備兩個真實帳號；在同一個不重啟的 Server 上確認 subject 不同、第二帳號看不到第一帳號筆記、第一帳號仍看得到。
- [ ] 確認備援 public Client 設定完整且可登入；學員仍使用各自帳號，不共用 Token。
- [ ] 在會場網路檢查服務可達性，安排集中登入容量彩排；Lab 06 課前完成映像建置，未完成者跟看講師示範。

每次彩排記錄日期、教材 commit（含工作目錄是否有修改）、OS／CLI／runtime 版本、語言路線、實際呼叫與預期／實際結果。不記錄 Token、callback 授權碼或 secret。更新上方狀態後，將詳細過程存入歷史紀錄。

## 歷史證據

10/11 彩排使用 Go 1.26.7、Python 3.12.13、Claude Code 2.1.263、Codex 0.162.1、Docker 29.2.1、Compose 5.1.4。當時未記錄教材 commit，無法宣稱等同目前工作目錄；完整結果見 [歷史紀錄](validation-history.md)。
