from __future__ import annotations

import re


def _pdf_escape_text(s: str) -> str:
    s = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)


def render_simple_text_pdf(*, title: str, lines: list[str]) -> bytes:
    """
    Minimal deterministic single-page PDF generator (Helvetica, text only).
    No timestamps, no metadata, stable bytes for identical inputs.
    """
    font_obj = "2 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"

    # Content stream
    y = 760
    content_lines = ["BT", "/F1 12 Tf", "72 800 Td", f"({ _pdf_escape_text(title) }) Tj"]
    for line in lines:
        y -= 14
        content_lines.append("0 -14 Td")
        content_lines.append(f"({ _pdf_escape_text(line) }) Tj")
        if y < 72:
            break
    content_lines.append("ET")
    content_stream = "\n".join(content_lines).encode("utf-8")
    content_obj = (
        f"4 0 obj\n<< /Length {len(content_stream)} >>\nstream\n".encode("utf-8")
        + content_stream
        + b"\nendstream\nendobj\n"
    )

    page_obj = (
        "3 0 obj\n"
        "<< /Type /Page /Parent 1 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 2 0 R >> >> "
        "/Contents 4 0 R >>\n"
        "endobj\n"
    )
    pages_obj = "1 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    catalog_obj = "5 0 obj\n<< /Type /Catalog /Pages 1 0 R >>\nendobj\n"

    parts: list[bytes] = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    offsets: list[int] = []

    def add_obj(obj_bytes: bytes) -> None:
        offsets.append(sum(len(p) for p in parts))
        parts.append(obj_bytes)

    add_obj(pages_obj.encode("utf-8"))  # 1
    add_obj(font_obj.encode("utf-8"))  # 2
    add_obj(page_obj.encode("utf-8"))  # 3
    add_obj(content_obj)  # 4
    add_obj(catalog_obj.encode("utf-8"))  # 5

    xref_offset = sum(len(p) for p in parts)
    xref = ["xref", "0 6", "0000000000 65535 f "]
    for off in offsets:
        xref.append(f"{off:010d} 00000 n ")
    xref_bytes = ("\n".join(xref) + "\n").encode("utf-8")
    trailer = (
        "trailer\n"
        "<< /Size 6 /Root 5 0 R >>\n"
        "startxref\n"
        f"{xref_offset}\n"
        "%%EOF\n"
    ).encode("utf-8")

    parts.append(xref_bytes)
    parts.append(trailer)
    return b"".join(parts)

