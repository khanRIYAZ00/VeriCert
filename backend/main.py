from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from pydantic import BaseModel, Field

from .crypto import (
    generate_keys,
    calculate_hash,
    verify_signature,
)

from .credentials import create_credential
from .qr import generate_qr
from .certificate import generate_certificate


app = FastAPI(
    title="VeriCert",
    description="Cryptographically Verifiable Academic Credentials",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CertificateRequest(BaseModel):
    name: str = Field(min_length=1)
    qualification: str = Field(min_length=1)
    graduation_year: int
    cgpa: float = Field(ge=0, le=10)


class VerifyRequest(BaseModel):
    credential: dict
    hash: str
    signature: str


@app.on_event("startup")
def startup():
    generate_keys()


@app.get("/")
def root():
    return {
        "project": "VeriCert",
        "version": "0.1.0",
        "status": "running",
    }


@app.post("/issue")
def issue_certificate(request: CertificateRequest):

    package = create_credential(
        name=request.name,
        qualification=request.qualification,
        graduation_year=request.graduation_year,
        cgpa=request.cgpa,
    )

    credential_id = package["credential"]["credential_id"]

    qr_path = generate_qr(
        package,
        credential_id,
    )

    pdf_path = generate_certificate(
        package,
        qr_path,
    )

    return {
        **package,
        "qr_file": qr_path,
        "certificate_file": pdf_path,
    }


@app.post("/verify")
def verify_certificate(request: VerifyRequest):

    calculated_hash = calculate_hash(
        request.credential
    )

    hash_valid = (
        calculated_hash == request.hash
    )

    signature_valid = verify_signature(
        request.credential,
        request.signature,
    )

    verified = (
        hash_valid
        and signature_valid
    )

    return {
        "verified": verified,
        "credential_id": request.credential.get(
            "credential_id"
        ),
        "checks": {
            "hash_valid": hash_valid,
            "signature_valid": signature_valid,
        },
    }

@app.post("/verify-qr")
def verify_qr(package: dict):

    credential = package.get("credential")
    supplied_hash = package.get("hash")
    signature = package.get("signature")

    if not credential or not supplied_hash or not signature:
        raise HTTPException(
            status_code=400,
            detail="Invalid VeriCert credential package",
        )

    calculated_hash = calculate_hash(credential)

    hash_valid = calculated_hash == supplied_hash

    signature_valid = verify_signature(
        credential,
        signature,
    )

    verified = hash_valid and signature_valid

    return {
        "verified": verified,
        "credential": credential,
        "checks": {
            "credential_format": True,
            "hash_valid": hash_valid,
            "signature_valid": signature_valid,
        },
    }