# Epivra 0.3.2 · Windows x64

## 本次更新

- 搜索服务返回原文时直接保存并复用，减少重复网页读取；供应商总结与原文保持区分。
- 通用 MCP 支持可选的可追溯文档结果映射，普通 MCP 连接保持原有行为。
- 优化连接与设置布局，返回和保存固定在顶部；OCR 安装时选择目录并记住位置。
- 改善 MCP 超时处理及本地连接的代理行为。
- 公开安装包不含本地图书馆插件、学校目录、登录数据或浏览器组件。

## 使用与升级

完整解压 ZIP 后打开 Epivra.exe。升级前退出旧程序并备份数据目录，再解压新包；不要将程序覆盖到用户数据目录。

Windows 10/11 x64；内置受限 Python 数据分析，无需 Docker 或单独安装 Python。分析组件在设置中准备后启用；OCR 仍是可选联网下载。macOS 不再构建或验证。

当前程序未签名，Windows 可能提示未知发布者。模型及搜索 API 费用由供应商收取。工程验证不代表研究报告质量验收。

## Changes

Search-provided original content is saved and reused, with provider summaries kept separate. Optional generic MCP document mapping preserves provenance without changing ordinary MCP tools. Settings now keep Save and Back visible; OCR setup remembers the selected directory. Local MCP proxy handling and timeouts are improved.

No private institution plugin, school catalogue, login data or browser component is bundled. Extract the whole ZIP and open Epivra.exe. Quit the old app and back up the data directory before upgrading. Built-in restricted Python analysis requires no Docker; OCR remains optional. Windows x64 only. The application is unsigned. Engineering checks do not certify research-report quality.
