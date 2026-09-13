"""Docling conversion of local bytes to located text; no research summarization."""

import io
from importlib.metadata import version
from pathlib import Path

FORMATS = {".docx", ".pptx", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def convert(name, raw, options):
    try:
        from docling.datamodel.base_models import DocumentStream, InputFormat
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions,
            RapidOcrOptions,
        )
        from docling.document_converter import (
            DocumentConverter,
            ImageFormatOption,
            PdfFormatOption,
        )
    except ImportError:
        raise ValueError(
            "Docling is not installed; install the project's [documents] extra"
        ) from None
    suffix = Path(name).suffix.lower()
    format_options = {}
    if suffix in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        artifacts = options.get("artifacts_path")
        if not artifacts or not Path(artifacts).is_dir():
            raise ValueError(
                "Docling PDF/OCR needs a downloaded model directory; configure --docling-models"
            )
        pipeline = PdfPipelineOptions(
            artifacts_path=Path(artifacts),
            do_ocr=True,
            do_table_structure=True,
            enable_remote_services=False,
        )
        pipeline.ocr_options = RapidOcrOptions()
        format_options = {
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline),
            InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline),
        }
    converter = DocumentConverter(format_options=format_options)
    result = converter.convert(
        DocumentStream(name=name, stream=io.BytesIO(raw)), raises_on_error=False
    )
    status = result.status.value
    if status not in {"success", "partial_success"}:
        raise ValueError(
            "Docling conversion failed; verify format or local model resources"
        )
    return located_document(result.document, status, version("docling"), result.errors)


def located_document(document, status, parser_version, errors=()):
    parts, segments, issues = [], [], []
    offset = 0
    seen_pages = set()
    for item, level in document.iterate_items():
        label = getattr(item, "label", "")
        label = getattr(label, "value", str(label))
        if hasattr(item, "data") and hasattr(item, "export_to_markdown"):
            text = item.export_to_markdown(doc=document)
        else:
            text = getattr(item, "text", "")
        provenance = []
        for location in getattr(item, "prov", []):
            seen_pages.add(location.page_no)
            provenance.append(
                {
                    "page": location.page_no,
                    "bbox": location.bbox.model_dump(mode="json"),
                }
            )
        locator = {"element": item.self_ref, "label": label, "level": level}
        if provenance:
            locator["locations"] = provenance
            locator["page"] = provenance[0]["page"]
        if "picture" in label:
            issues.append(
                {"locator": locator, "reason": "image_semantics_not_interpreted"}
            )
        if not text:
            continue
        block = text + "\n\n"
        segments.append(
            {
                "start": offset,
                "end": offset + len(block),
                "locator": locator,
                "status": "extracted_not_reviewed",
            }
        )
        offset += len(block)
        parts.append(block)
    for page in document.pages:
        if page not in seen_pages:
            issues.append({"page": page, "reason": "page_has_no_located_content"})
    if status == "partial_success" or errors:
        issues.append(
            {"reason": "docling_partial_conversion", "error_count": len(errors)}
        )
    if not parts:
        issues.append({"reason": "no_readable_text"})
    return {
        "text": "".join(parts),
        "segments": segments,
        "parser": "docling-" + parser_version,
        "coverage": "partial_extraction"
        if issues
        else "structure_extracted_not_reviewed",
        "issues": issues,
    }
