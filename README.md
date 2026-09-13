# Epivra

**自主研究工作台 · 从问题到洞见。**

Epivra 根据你的问题和用途，结合公开网络、上传文件或授权资料文件夹开展研究。你先确认初始策略，随后由研究 Agent 自主调查、分析、综合、写作与核查，交付带来源依据、适用条件和不确定性说明的成果。研究过程中可以暂停、补充资料或调整方向。

提供用户本地运行的 CLI、轻量 Web UI 与双向 MCP 接入。研究记录和成果保存在本机；在线模型、搜索及外部工具会接收完成任务所需的查询与资料内容。关闭客户端不会结束后台研究，本机和研究服务需保持运行。

已接入12家官方模型、5家搜索 API 与 DuckDuckGo，以及 Jina/Tavily/Exa 网页读取；支持本地文档解析、可选 Docling OCR 和 Docker 数据分析。底层使用自研、供应商无关的 Agent Runtime / Harness，提供上下文管理、角色协作、持久恢复与用量记录。默认模型为 deepseek-flash。

**当前状态：工程能力已集成，跨题材、真实长文档及规模化研究质量验收仍待完成。** 供应商适配并非全部经过真实账户联调；图表语义理解与云端解析尚未实现。具体已验证范围见实施记录，不能把工程测试通过视为研究结论必然正确。

- [唯一现行架构](docs/ARCHITECTURE.md)
- [研究与产品设计](docs/product-redesign/README.md)
- [实施进度与待完成项](docs/product-redesign/IMPLEMENTATION.md)
- [开发与验证](docs/GETTING-STARTED.md)

日常使用：在此 worktree 安装后运行 `.venv/Scripts/deep-research.exe`，无参数进入交互工作台。支持系统文件/文件夹选择、策略审批、研究控制与成果导出；显式子命令保留 JSON 接口。

历史学习、面试和复盘文档描述旧实现，仅作为背景材料；不指导本分支的新架构。开发规则见 [AGENTS.md](AGENTS.md)。

可选 Docker 通用分析已接入现有角色与成果链：数据处理、统计和绘图共用 run_analysis，使用来源引用传入原始文件。部署与恢复边界见[通用分析执行](docs/product-redesign/ANALYSIS_EXECUTION.md)。
