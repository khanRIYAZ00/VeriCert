from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .storage import template_path


def _value_for(field: dict, credential: dict) -> str:
    key = field["key"]
    builtins = {
        "credential_id": credential["credential_id"],
        "issue_date": credential["issue_date"],
        "club": credential["club"]["name"],
        "event": credential["event"]["name"],
    }
    return str(builtins.get(key, credential["recipient"].get(key, "")))


def render_certificate(template, credential_package: dict, qr_path: str) -> bytes:
    credential = credential_package["credential"]
    width, height = template.page_width, template.page_height
    overlay = BytesIO()
    layer = canvas.Canvas(overlay, pagesize=(width, height))
    for field in template.layout:
        x, y = float(field["x"]) * width, float(field["y"]) * height
        w, h = float(field.get("width", .25)) * width, float(field.get("height", .08)) * height
        if field["key"] == "qr":
            layer.drawImage(ImageReader(qr_path), x, height - y - h, width=w, height=h, mask="auto")
            continue
        layer.setFont("Helvetica-Bold" if field.get("bold") else "Helvetica", float(field.get("font_size", 18)))
        layer.setFillColor(field.get("color", "#111111"))
        text = _value_for(field, credential)
        draw_y = height - y - h / 2
        if field.get("align") == "center":
            layer.drawCentredString(x + w / 2, draw_y, text)
        elif field.get("align") == "right":
            layer.drawRightString(x + w, draw_y, text)
        else:
            layer.drawString(x, draw_y, text)
    layer.save()
    overlay.seek(0)
    artwork = template_path(template.artwork_key)
    writer = PdfWriter()
    if template.artwork_mime == "application/pdf":
        background = PdfReader(str(artwork)).pages[0]
    else:
        image_pdf = BytesIO()
        base = canvas.Canvas(image_pdf, pagesize=(width, height))
        base.drawImage(ImageReader(str(artwork)), 0, 0, width=width, height=height, mask="auto")
        base.save()
        image_pdf.seek(0)
        background = PdfReader(image_pdf).pages[0]
    background.merge_page(PdfReader(overlay).pages[0])
    writer.add_page(background)
    result = BytesIO()
    writer.write(result)
    return result.getvalue()
