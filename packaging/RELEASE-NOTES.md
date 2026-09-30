# Epivra 0.3.5 · Windows x64

## 本次更新

- 修复快速暂停、继续时研究任务无法恢复的问题；旧一轮执行结束后，统一进入已接受的新一轮，结果未知的已发送请求仍不会自动重放。
- 协调全局 Agent 排队与供应商限流：等待不预占调用额度，发送前再次核验，按供应商公平排队，避免长时间等待后突发超额调用。
- 暂停时及时撤回排队但尚未发送的任务，让补充材料和重新加载配置恢复可用；已经发送的请求仍正常结算。
- 修复新建研究期间输入与文件丢失、部分材料导入失败后的恢复，以及重复打开设置导致旧响应覆盖或重开窗口的问题。
- 统一 HTTP 解压与文本解码，修复压缩纯文本和 Markdown 的重复解压；本地文件先核验大小和类型，再进行有上限的读取。
- CLI 上传和回执文件使用对应传输上限，编码后的 IPC 请求也会在发送前检查，避免超大文件先分配内存。
- Windows 分析沙盒拒绝输出与临时目录中的隐藏 NTFS 数据流，并在进程结束后再次检查，修复磁盘用量监测遗漏；该机制仍是周期监测，并非操作系统硬配额。
- 补齐英文界面的资料检索、恢复提示和 Jev 原文外发说明。
- 外部 MCP 的排队、连接准备与工具定义刷新均移到发送准入之前；暂停或取消后，不会继续发送尚未开始的读写调用，已经发送但结果未知的调用仍禁止自动重放。
- 统一终端、网页与 MCP 的状态错误处理；其他客户端删除当前研究后，终端不会再因缺少控制版本而崩溃。
- 补充后端、前端和真实 Chromium 回归测试，并明确研究生命周期、发送准入、输入边界和界面状态的模块职责。

## 使用与升级

先退出旧程序并备份数据目录，再完整解压 ZIP，打开 Epivra.exe。此版本沿用 0.3.4 的数据与研究运行合同；更早版本中运行合同不兼容的未完成研究仍需新建，历史报告可查看和导出。

材料导入失败时，可以在该研究的“补充材料”中重试剩余文件；待导入文件只保留在当前页面，请在关闭页面前完成导入。原始文件不会被删除。

Windows 10/11 x64。内置受限 Python 数据分析，无需 Docker 或单独安装 Python；OCR 仍为可选下载。默认 BM25，可选 Jev 使用自己的 TypeSafe API 密钥。当前程序未签名。回归测试不调用付费模型或搜索服务，不代表真实供应商兼容性或研究质量评测。

## Changes

- Recover consistently after quick pause/resume, including when an older execution finishes with an error. Sent requests with unknown outcomes remain blocked from automatic replay.
- Coordinate global Agent turns with provider limits, charge rate allowance immediately before sending, and admit provider waiters fairly without holding scarce resources across unrelated waits.
- Withdraw queued, unsent work on pause so material uploads and configuration reloads can proceed; already-sent requests continue to settle.
- Preserve creation drafts and files, retain unimported materials for retry, and fence stale settings responses after repeated opens, dismissal or saving.
- Decode compressed plain text and Markdown once; validate local file size/type before bounded reading.
- Apply transport-specific file bounds to CLI uploads and receipts, and reject oversized encoded IPC requests before sending.
- Reject hidden NTFS data streams in native-analysis output and scratch, including a post-exit check. This closes a monitoring gap; disk limits remain periodically monitored rather than OS-enforced quotas.
- Complete the English evidence-retrieval, recovery and Jev data-sharing notices.
- Move external MCP queuing, session setup and tool-definition refresh before send admission. Pause/cancel withdraws unsent reads/writes; dispatched unknown outcomes remain protected from automatic replay.
- Share status-error handling across terminal, web and MCP interfaces, preventing terminal failure when another client deletes the selected study.
- Add backend, frontend and real Chromium regressions, with documented ownership of lifecycle, admission, input and interface state.

Quit the old app and back up its data before upgrading. Extract the complete ZIP and open Epivra.exe. Version 0.3.5 preserves the 0.3.4 data and runtime contract; unfinished studies using incompatible older contracts still require a new study, while historical reports remain readable and exportable.

Retry failed material imports from the study's Supplement panel before closing the page; pending files are page-local and original files are never deleted. Windows x64 only, unsigned; restricted Python analysis is bundled and OCR is optional. Offline regression checks do not establish live-provider compatibility or research quality.
