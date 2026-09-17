from pathlib import Path
import os

import qrcode


OUTPUT_DIR = Path("generated")


def generate_qr(credential_id: str) -> str:
    OUTPUT_DIR.mkdir(exist_ok=True)

    base_url = os.getenv("VERICERT_PUBLIC_URL", "http://127.0.0.1:8000")
    qr_data = f"{base_url.rstrip('/')}/verify/{credential_id}"

    image = qrcode.make(qr_data)

    path = OUTPUT_DIR / f"{credential_id}.png"

    image.save(path)

    return str(path)
