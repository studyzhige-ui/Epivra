"""Local bytes to citable text, with explicit extraction coverage."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, time
from pathlib import Path

from .domain import encode

TEXT_SUFFIXES = {".txt", ".md", ".json", ".yaml", ".yml", ".html"}
SUPPORTED_SUFFIXES = TEXT_SUFFIXES | {".csv", ".tsv", ".pdf", ".xlsx"}


def parse(name: str, raw: bytes) -> dict:
    suffix = Path(name).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError("unsupported material format")
    parts, segments, issues = [], [], []
    position = 0

    def append(text, locator, status="extracted"):
        nonlocal position
        block = text + "\n"
        segments.append(
            {
                "start": position,
                "end": position + len(block),
                "locator": locator,
                "status": status,
            }
        )
        position += len(block)
        parts.append(block)

    if suffix in TEXT_SUFFIXES:
        text = raw.decode("utf-8-sig")
        return {
            "text": text,
            "segments": [
                {
                    "start": 0,
                    "end": len(text),
                    "locator": {"document": name},
                    "status": "extracted",
                }
            ],
            "coverage": "text_extracted_not_reviewed",
            "issues": [],
            "parser": "utf8-v1",
        }
    if suffix in {".csv", ".tsv"}:
        reader = csv.reader(
            io.StringIO(raw.decode("utf-8-sig"), newline=""),
            delimiter="," if suffix == ".csv" else "\t",
            strict=True,
        )
        try:
            for row, cells in enumerate(reader, 1):
                append(encode(cells), {"row": row})
        except csv.Error:
            raise ValueError("invalid delimited table") from None
        parser = "csv-v1"
    elif suffix == ".pdf":
        from pypdf import PdfReader, __version__

        try:
            reader = PdfReader(io.BytesIO(raw))
            if reader.is_encrypted:
                raise ValueError(
                    "encrypted PDF requires an unlocked user-provided copy"
                )
            for number, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                status = (
                    "text_extracted" if text.strip() else "needs_ocr_or_visual_review"
                )
                append(text, {"page": number}, status)
                if not text.strip():
                    issues.append({"page": number, "reason": status})
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("PDF extraction failed: " + type(exc).__name__) from None
        parser = "pypdf-" + __version__
        issues.append(
            {"reason": "text_layer_only; layout_images_and_tables_not_verified"}
        )
    else:
        from openpyxl import __version__, load_workbook

        book = None
        try:
            book = load_workbook(
                io.BytesIO(raw), read_only=True, data_only=False, keep_links=False
            )
            for sheet in book.worksheets:
                sheet.reset_dimensions()
                for row_number, row in enumerate(sheet.iter_rows(), 1):
                    cells = []
                    for cell in row:
                        if cell.value is None:
                            continue
                        value = cell.value
                        if isinstance(value, (datetime, date, time)):
                            value = value.isoformat()
                        if not isinstance(value, (str, int, float, bool)):
                            value = str(value)
                        cells.append(
                            {
                                "cell": cell.coordinate,
                                "value": value,
                                "type": cell.data_type,
                                "number_format": cell.number_format,
                            }
                        )
                    if cells:
                        append(
                            encode(cells),
                            {
                                "sheet": sheet.title,
                                "row": row_number,
                                "visibility": sheet.sheet_state,
                            },
                        )
            issues.append(
                {
                    "reason": "formulas_not_evaluated; charts_images_and_merged_layout_not_extracted"
                }
            )
        except Exception as exc:
            raise ValueError("XLSX extraction failed: " + type(exc).__name__) from None
        finally:
            if book is not None:
                book.close()
        parser = "openpyxl-" + __version__
    return {
        "text": "".join(parts),
        "segments": segments,
        "coverage": "partial_extraction" if issues else "table_extracted_not_reviewed",
        "issues": issues,
        "parser": parser,
    }
