# Epivra 0.3.4 · Windows x64

## 本次更新

- 研究失败按具体原因恢复：区分限流、账户、权限、参数错误及结果未知，避免盲目重试。
- 已取得的资料、部分成功结果和已结算判断继续复用；定向补查缺口，减少重复调用。
- 修复中断后的 HTTP/Jina 读取及 Jev 恢复，判断关联最终成功回执。
- 限流等待与未解决的请求限制跨重启保留；并发在途成功不会误解除限制。
- 研究负责人沿现有流程处理资料缺口，获取失败不会被当作证据充分。

## 使用与升级

完整解压 ZIP 后打开 Epivra.exe。升级前退出旧程序并备份数据目录，再解压新包。历史报告仍可查看和导出；旧运行合同的未完成研究不能直接按新合同继续执行，请新建研究。

Windows 10/11 x64。内置受限 Python 数据分析，无需 Docker 或单独安装 Python；OCR 仍是可选下载。默认 BM25，可选 Jev 使用自己的 TypeSafe API 密钥；无需下载 embedding 模型。当前程序未签名。

## Changes

Research recovery now follows the actual failure cause, separating rate limits, account/access errors, invalid parameters and unknown outcomes. Acquired sources, partial results and settled judgments are retained and reused; investigators address specific evidence gaps.

Interrupted HTTP/Jina reading and Jev recovery now resume correctly, with judgments linked to the successful receipt. Waiting deadlines and unresolved request barriers survive restart, and already-in-flight successes cannot incorrectly clear them. Evidence acquisition failures do not establish research sufficiency.

Quit the old app and back up your data before upgrading. Extract the whole ZIP and open Epivra.exe. Historical reports remain readable and exportable; unfinished studies bound to an older runtime contract require a new study. Windows x64 only, unsigned; restricted Python analysis is bundled and OCR is optional. BM25 is the default; optional Jev uses your TypeSafe key and no embedding model download is required.
