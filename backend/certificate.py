from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
)

OUTPUT_DIR = Path("generated")


def generate_certificate(package: dict, qr_path: str) -> str:
    OUTPUT_DIR.mkdir(exist_ok=True)

    credential = package["credential"]
    credential_id = credential["credential_id"]

    pdf_path = OUTPUT_DIR / f"{credential_id}.pdf"

    document = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=25 * mm,
        leftMargin=25 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
    )

    styles = getSampleStyleSheet()

    title = styles["Title"]
    normal = styles["Normal"]

    content = []

    content.append(
        Paragraph(
            "DIGITAL ACADEMIC CERTIFICATE",
            title,
        )
    )

    content.append(Spacer(1, 15 * mm))

    content.append(
        Paragraph(
            f"<b>This certifies that</b><br/><br/>"
            f"<font size='18'><b>{credential['name']}</b></font><br/><br/>"
            f"has successfully completed "
            f"<b>{credential['qualification']}</b>.<br/><br/>"
            f"Graduation Year: {credential['graduation_year']}<br/>"
            f"CGPA: {credential['cgpa']}<br/>"
            f"Issue Date: {credential['issue_date']}<br/><br/>"
            f"Issuer: {credential['issuer']}<br/>"
            f"Credential ID: {credential_id}",
            normal,
        )
    )

    content.append(Spacer(1, 15 * mm))

    qr = Image(qr_path, width=45 * mm, height=45 * mm)

    content.append(qr)

    content.append(Spacer(1, 5 * mm))

    content.append(
        Paragraph(
            "Scan the QR code to cryptographically verify this credential.",
            normal,
        )
    )

    document.build(content)

    return str(pdf_path)