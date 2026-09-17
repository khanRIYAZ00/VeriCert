from datetime import date
import uuid

from .crypto import calculate_hash, sign_data


def create_credential(*, club_id: int, club_name: str, event_id: int, event_name: str,
                      template_version_id: int, issued_by: str, recipient_values: dict):
    credential = {
        "credential_id": f"VC-{date.today().year}-{uuid.uuid4().hex[:8].upper()}",
        "issuer": "VeriCert",
        "club": {"id": club_id, "name": club_name},
        "event": {"id": event_id, "name": event_name},
        "template_version_id": template_version_id,
        "issued_by": issued_by,
        "recipient": recipient_values,
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
