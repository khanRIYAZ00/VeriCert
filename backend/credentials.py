from datetime import date
import uuid

from .crypto import calculate_hash, sign_data


def create_credential(
    name: str,
    qualification: str,
    graduation_year: int,
    cgpa: float,
    issuer: str = "ABC Institute of Technology",
):
    credential = {
        "credential_id": f"VC-{date.today().year}-{uuid.uuid4().hex[:8].upper()}",
        "issuer": issuer,
        "name": name,
        "qualification": qualification,
        "graduation_year": graduation_year,
        "cgpa": cgpa,
        "issue_date": date.today().isoformat(),
    }

    credential_hash = calculate_hash(credential)
    signature = sign_data(credential)

    return {
        "credential": credential,
        "hash": credential_hash,
        "signature": signature,
        "algorithm": "Ed25519",
        "hash_algorithm": "SHA-256",
    }