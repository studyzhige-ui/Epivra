# Epivra

**自主研究工作台 · 从问题到洞见。**

Epivra 根据你的问题和用途，结合公开网络、上传文件或授权资料文件夹开展研究。你先确认初始策略，随后由研究 Agent 自主调查、分析、综合、写作与核查，交付带来源依据、适用条件和不确定性说明的成果。研究过程中可以暂停、补充资料或调整方向。

提供用户本地运行的 CLI、轻量 Web UI 与双向 MCP 接入。研究记录和成果保存在本机；在线模型、搜索及外部工具会接收完成任务所需的查询与资料内容。关闭客户端不会结束后台研究，本机和研究服务需保持运行。

已接入12家官方模型、5家搜索 API 与 DuckDuckGo，以及 Jina/Tavily/Exa 网页读取；支持本地文档解析、可选 Docling OCR 和 Docker 数据分析。底层使用自研、供应商无关的 Agent Runtime / Harness，提供上下文管理、角色协作、持久恢复与用量记录。默认模型为 deepseek-flash。

**当前状态：工程能力已集成，跨题材、真实长文档及规模化研究质量验收仍待完成。** 供应商适配并非全部经过真实账户联调；图表语义理解与云端解析尚未实现。不能把工程测试通过视为研究结论必然正确。


## 快速开始

在项目目录执行（Windows PowerShell）：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
.venv/Scripts/epivra.exe web
```

打开“连接与设置”，选择厂商、填写密钥并选择模型；输入问题，确认研究策略后开始。终端工作台使用 `.venv/Scripts/epivra.exe`。

- [完整使用说明](docs/USAGE.md)：连接、研究、暂停改向、资料、分析、MCP 与备份。
- [本地模型](models/README.md)：模型位于项目 `models/docling/`，权重不纳入 Git。

## 项目结构

`src/epivra/` 包含应用与图标；`models/` 组织本地解析模型；`sandbox/` 提供可选分析容器；`tests/` 为离线工程测试；`evals/` 为研究验证资料；`tools/` 为检查和验证工具；`docs/` 包含使用帮助。

`.env` 保存本地凭据，`.epivra/` 保存研究和配置，两者均不提交。仓库保留从初始实现到 Epivra 的代码演进历史；内部开发文档和环境配置文件已从上传历史中排除。
