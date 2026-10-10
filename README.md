# MCP OAuth 2.0 Workshop

讓 AI Agent、MCP Server 與 CLI 安全登入的實作工作坊。

Hands-on workshop for securing MCP servers with OAuth 2.0, PKCE, and Kong Gateway using Go.

## 活動資訊

- 活動：Hello World Dev Conference 2026
- 課程：[讓 AI Agent、MCP Server、CLI 安全登入的實作工作坊](https://hwdc.ithome.com.tw/2026/lab/4993)
- 主要技術：Go、MCP、OAuth 2.0、Kong Gateway、Signet

## 預計實作內容

1. 啟動 MCP Server，透過 MCP Client 呼叫工具。
2. 透過 Kong Gateway 保護 MCP 入口，觀察 401 挑戰與 Protected Resource Metadata。
3. 使用 Authorization Code Flow + PKCE 完成登入。
4. 驗證 Access Token、scope 與 audience，測試跨資源存取限制。
5. 操作 CLI Device Flow。
6. 演練 Token 撤銷與稽核追蹤。

> 教材準備中。各 Lab、環境需求與操作指令將陸續補齊。即時撤銷需搭配撤銷狀態檢查；僅離線驗證 JWT 無法保證立即失效。

## 相關專案

- [MCP Workshop](https://github.com/go-training/mcp-workshop)
- [Kong MCP OAuth2 Plugin](https://github.com/go-signet/kong-mcp-oauth2)
- [Signet](https://github.com/go-signet)
