import json
from pathlib import Path

import qrcode


OUTPUT_DIR = Path("generated")


def generate_qr(credential_package: dict, credential_id: str) -> str:
    OUTPUT_DIR.mkdir(exist_ok=True)

    qr_data = json.dumps(
        credential_package,
        separators=(",", ":"),
    )

    image = qrcode.make(qr_data)

    path = OUTPUT_DIR / f"{credential_id}.png"

    image.save(path)

    return str(path)