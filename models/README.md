# Epivra 本地模型

[English](README.en.md) · **简体中文**

`docling/` 存放 Docling 版面、表格与 RapidOCR 权重。Epivra 自动发现研究根目录下的此目录；也可在设置中指定其他路径。大语言模型通过所选厂商 API 调用，不需要下载到本地。旧项目的 BGE 嵌入与重排模型不被当前实现使用，不纳入新项目。

当前本地权重约733 MB，已复制进项目，但不提交 Git。`docling-manifest.json` 记录本次文件的 SHA-256 与大小，便于核对；权重及配置应整体保留。图标位于 `src/epivra/web/`，由 Python 包一起安装。

新克隆项目需要安装解析依赖并下载一次：

```powershell
python -m pip install -e ".[documents]"
docling-tools models download layout tableformer rapidocr --rapidocr-backend-lang onnxruntime:chinese --output-dir models/docling
```

该命令来自当前适配的 Docling 工具。不同版本可能下载更新的权重，因此新下载不保证与本次清单逐字一致。依据：[Docling 本地模型](https://docling-project.github.io/docling/usage/advanced_options/)。模型遵循各自上游许可；Epivra 项目的权限不替代模型许可。
