# Epivra local models

**English** · [简体中文](README.md)

`docling/` holds Docling layout, table, and RapidOCR models. Epivra discovers this directory under the research root automatically; you may also configure another path. Language models are accessed through provider APIs and do not need local downloads.

The local snapshot is approximately 733 MB and is excluded from Git. `docling-manifest.json` records SHA-256 hashes and sizes for verification. Keep model weights and their configuration files together. Application icons live in `src/epivra/web/` and are installed with the Python package.

After cloning, install the parsing extension and download the models once:

```powershell
python -m pip install -e ".[documents]"
docling-tools models download layout tableformer rapidocr --rapidocr-backend-lang onnxruntime:chinese --output-dir models/docling
```

This command matches the currently integrated Docling tools. Future versions may download updated weights, so a fresh download may differ from the recorded snapshot. See [Docling local models](https://docling-project.github.io/docling/usage/advanced_options/). Models remain subject to their respective upstream licenses.
