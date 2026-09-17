import csv
import io
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .auth import create_token, get_current_user, get_db, hash_password, require_club_access, verify_password
from .certificate import render_certificate
from .credentials import create_credential
from .crypto import calculate_hash, generate_keys, verify_signature
from .database import init_database
from .models import Club, DeliveryAttempt, Event, Issuance, Membership, TemplateVersion, User
from .qr import generate_qr
from .storage import save_template_artwork, template_path

app = FastAPI(title="VeriCert", description="Verifiable multi-tenant certificates", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
Path("storage/templates").mkdir(parents=True, exist_ok=True)
app.mount("/assets/templates", StaticFiles(directory="storage/templates"), name="templates")


class LoginRequest(BaseModel):
    email: str
    password: str


class ClubRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)


class EventRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    template_version_id: int | None = None


class MemberRequest(BaseModel):
    email: str
    password: str = Field(min_length=10)


class TemplateUpdate(BaseModel):
    field_definitions: list[dict]
    layout: list[dict]


class IssueRequest(BaseModel):
    event_id: int
    recipient_email: str
    roll_number: str = Field(min_length=1, max_length=128)
    values: dict[str, str]


def template_payload(template: TemplateVersion) -> dict:
    return {
        "id": template.id, "club_id": template.club_id, "name": template.name, "version": template.version,
        "status": template.status, "artwork_url": f"/assets/templates/{template.artwork_key}",
        "artwork_mime": template.artwork_mime, "page_width": template.page_width, "page_height": template.page_height,
        "field_definitions": template.field_definitions, "layout": template.layout,
    }


def validate_template(template: TemplateVersion, values: dict) -> None:
    defined = {field["key"]: field for field in template.field_definitions}
    for key, definition in defined.items():
        if definition.get("required") and not str(values.get(key, "")).strip():
            raise HTTPException(status_code=422, detail=f"Missing required field: {key}")
    unexpected = set(values) - set(defined) - {"roll_no"}
    if unexpected:
        raise HTTPException(status_code=422, detail=f"Unknown template fields: {', '.join(sorted(unexpected))}")


def get_event_for_user(event_id: int, user: User, db: Session) -> tuple[Event, Club, TemplateVersion]:
    event = db.get(Event, event_id)
    if not event or not event.template_version_id:
        raise HTTPException(status_code=404, detail="Event or event template not found")
    require_club_access(event.club_id, user, db)
    club, template = db.get(Club, event.club_id), db.get(TemplateVersion, event.template_version_id)
    if not template or template.status != "published":
        raise HTTPException(status_code=422, detail="Event must use a published template")
    return event, club, template


def deliver(issuance_id: int) -> None:
    db = next(get_db())
    try:
        issuance = db.get(Issuance, issuance_id)
        attempt = db.query(DeliveryAttempt).filter_by(issuance_id=issuance_id, status="queued").first()
        if not issuance or not attempt:
            return
        template = db.get(TemplateVersion, issuance.template_version_id)
        qr_path = generate_qr(issuance.credential_id)
        pdf = render_certificate(template, issuance.credential_package, qr_path)
        host = os.getenv("VERICERT_SMTP_HOST")
        if not host:
            raise RuntimeError("SMTP is not configured; set VERICERT_SMTP_HOST")
        message = EmailMessage()
        message["Subject"] = "Your VeriCert certificate"
        message["From"] = os.getenv("VERICERT_SMTP_FROM", "certificates@vericert.local")
        message["To"] = issuance.recipient_email
        message.set_content(f"Your certificate is attached. Verify it at /verify/{issuance.credential_id}.")
        message.add_attachment(pdf, maintype="application", subtype="pdf", filename=f"{issuance.credential_id}.pdf")
        with smtplib.SMTP(host, int(os.getenv("VERICERT_SMTP_PORT", "587"))) as smtp:
            if os.getenv("VERICERT_SMTP_TLS", "true").lower() == "true": smtp.starttls()
            if os.getenv("VERICERT_SMTP_USER"): smtp.login(os.getenv("VERICERT_SMTP_USER"), os.getenv("VERICERT_SMTP_PASSWORD", ""))
            smtp.send_message(message)
        issuance.status, attempt.status, attempt.attempted_at = "delivered", "sent", datetime.utcnow()
    except Exception as error:
        if 'attempt' in locals() and attempt:
            attempt.status, attempt.error, attempt.attempted_at = "failed", str(error), datetime.utcnow()
        if 'issuance' in locals() and issuance: issuance.status = "delivery_failed"
    finally:
        db.commit()
        db.close()


def smtp_enabled() -> bool:
    return bool(os.getenv("VERICERT_SMTP_HOST"))


def create_issuance(payload: IssueRequest, user: User, db: Session) -> Issuance:
    event, club, template = get_event_for_user(payload.event_id, user, db)
    roll_number = payload.roll_number.strip()
    if not roll_number:
        raise HTTPException(status_code=422, detail="Roll number is required")
    existing = db.query(Issuance).filter(
        func.lower(Issuance.roll_number) == roll_number.lower(), Issuance.event_id == event.id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="That roll number already has a certificate for this event")
    values = {**payload.values, "roll_no": roll_number}
    validate_template(template, values)
    package = create_credential(club_id=club.id, club_name=club.name, event_id=event.id, event_name=event.name,
                                template_version_id=template.id, issued_by=user.email, recipient_values=values)
    issuance = Issuance(credential_id=package["credential"]["credential_id"], club_id=club.id, event_id=event.id,
                        template_version_id=template.id, recipient_email=payload.recipient_email,
                        roll_number=roll_number, recipient_values=values, credential_package=package,
                        status="issued", issued_by=user.id)
    db.add(issuance)
    db.flush()
    return issuance


@app.on_event("startup")
def startup():
    generate_keys()
    init_database()
    db = next(get_db())
    if not db.query(User).filter_by(email="admin@vericert.local").first():
        db.add(User(email="admin@vericert.local", password_hash=hash_password("change-me"), is_platform_admin=True))
        db.commit()
    db.close()


@app.get("/")
def root(): return {"project": "VeriCert", "version": "1.0.0", "status": "running"}


@app.post("/auth/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=request.email.lower()).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"token": create_token(user), "user": {"id": user.id, "email": user.email, "platform_admin": user.is_platform_admin}}


@app.get("/clubs")
def list_clubs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Club)
    if not user.is_platform_admin: query = query.join(Membership).filter(Membership.user_id == user.id)
    return [{"id": c.id, "name": c.name} for c in query.all()]


@app.post("/clubs")
def create_club(request: ClubRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    club = Club(name=request.name)
    db.add(club); db.flush(); db.add(Membership(user_id=user.id, club_id=club.id, role="admin")); db.commit()
    return {"id": club.id, "name": club.name}


@app.get("/clubs/{club_id}/events")
def list_events(club_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_club_access(club_id, user, db)
    return [{"id": e.id, "name": e.name, "template_version_id": e.template_version_id} for e in db.query(Event).filter_by(club_id=club_id)]


@app.post("/clubs/{club_id}/events")
def create_event(club_id: int, request: EventRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_club_access(club_id, user, db)
    if request.template_version_id:
        template = db.get(TemplateVersion, request.template_version_id)
        if not template or template.club_id != club_id or template.status != "published": raise HTTPException(422, "Select a published club template")
    event = Event(club_id=club_id, name=request.name, template_version_id=request.template_version_id); db.add(event); db.commit(); db.refresh(event)
    return {"id": event.id, "name": event.name, "template_version_id": event.template_version_id}


@app.post("/clubs/{club_id}/members")
def add_member(club_id: int, request: MemberRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_club_access(club_id, user, db)
    member_user = db.query(User).filter_by(email=request.email.lower()).first()
    if not member_user:
        member_user = User(email=request.email.lower(), password_hash=hash_password(request.password))
        db.add(member_user); db.flush()
    if not db.query(Membership).filter_by(user_id=member_user.id, club_id=club_id).first():
        db.add(Membership(user_id=member_user.id, club_id=club_id, role="admin")); db.commit()
    return {"id": member_user.id, "email": member_user.email}


@app.get("/clubs/{club_id}/templates")
def list_templates(club_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_club_access(club_id, user, db)
    return [template_payload(t) for t in db.query(TemplateVersion).filter_by(club_id=club_id).order_by(TemplateVersion.created_at.desc())]


@app.post("/clubs/{club_id}/templates")
def upload_template(club_id: int, name: str = Form(...), artwork: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_club_access(club_id, user, db)
    key, mime, width, height = save_template_artwork(artwork)
    version = TemplateVersion(club_id=club_id, name=name, artwork_key=key, artwork_mime=mime, page_width=width, page_height=height,
                              field_definitions=[{"key":"recipient_name", "label":"Recipient name", "required":True, "type":"text"}], layout=[], created_by=user.id)
    db.add(version); db.commit(); db.refresh(version)
    return template_payload(version)


@app.put("/templates/{template_id}")
def update_template(template_id: int, request: TemplateUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    template = db.get(TemplateVersion, template_id)
    if not template: raise HTTPException(404, "Template not found")
    require_club_access(template.club_id, user, db)
    if template.status != "draft": raise HTTPException(409, "Published templates are immutable")
    keys = [item.get("key") for item in request.field_definitions]
    if not all(keys) or len(keys) != len(set(keys)): raise HTTPException(422, "Field keys must be unique")
    allowed = set(keys) | {"qr", "roll_no", "credential_id", "issue_date", "club", "event"}
    if any(item.get("key") not in allowed for item in request.layout): raise HTTPException(422, "Layout contains unknown fields")
    template.field_definitions, template.layout = request.field_definitions, request.layout; db.commit()
    return template_payload(template)


@app.post("/templates/{template_id}/publish")
def publish_template(template_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    template = db.get(TemplateVersion, template_id)
    if not template: raise HTTPException(404, "Template not found")
    require_club_access(template.club_id, user, db)
    if not template.layout: raise HTTPException(422, "Place at least one field before publishing")
    template.status, template.published_at = "published", datetime.utcnow(); db.commit()
    return template_payload(template)


@app.post("/templates/{template_id}/revision")
def revise_template(template_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    source = db.get(TemplateVersion, template_id)
    if not source: raise HTTPException(404, "Template not found")
    require_club_access(source.club_id, user, db)
    revision = TemplateVersion(club_id=source.club_id, name=source.name, version=source.version + 1,
        artwork_key=source.artwork_key, artwork_mime=source.artwork_mime, page_width=source.page_width, page_height=source.page_height,
        field_definitions=source.field_definitions, layout=source.layout, created_by=user.id)
    db.add(revision); db.commit(); db.refresh(revision)
    return template_payload(revision)


@app.post("/issue")
def issue_certificate(request: IssueRequest, background_tasks: BackgroundTasks, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    issuance = create_issuance(request, user, db)
    if smtp_enabled():
        db.add(DeliveryAttempt(issuance_id=issuance.id))
        issuance.status = "queued"
    db.commit()
    if smtp_enabled(): background_tasks.add_task(deliver, issuance.id)
    return {"id": issuance.id, "credential_id": issuance.credential_id, "status": issuance.status}


@app.post("/issue/batch")
async def issue_batch(background_tasks: BackgroundTasks, event_id: int = Form(...), recipients: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    event, _, template = get_event_for_user(event_id, user, db)
    rows = list(csv.DictReader((await recipients.read()).decode("utf-8-sig").splitlines()))
    errors, accepted = [], []
    for index, row in enumerate(rows, start=2):
        try:
            email = row.pop("recipient_email", "").strip()
            roll_number = row.pop("roll_no", "").strip()
            if not email: raise HTTPException(422, "recipient_email is required")
            if not roll_number: raise HTTPException(422, "roll_no is required")
            validate_template(template, {**row, "roll_no": roll_number})
            accepted.append(IssueRequest(event_id=event.id, recipient_email=email, roll_number=roll_number, values=row))
        except HTTPException as error: errors.append({"row": index, "error": error.detail})
    if errors: return {"issued": 0, "errors": errors}
    issued = [create_issuance(item, user, db) for item in accepted]
    if smtp_enabled():
        for item in issued:
            db.add(DeliveryAttempt(issuance_id=item.id))
            item.status = "queued"
    db.commit()
    if smtp_enabled():
        for item in issued: background_tasks.add_task(deliver, item.id)
    return {"issued": len(issued), "issuance_ids": [item.id for item in issued], "errors": []}


@app.get("/clubs/{club_id}/issuances")
def list_issuances(club_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_club_access(club_id, user, db)
    return [{"id": i.id, "credential_id": i.credential_id, "email": i.recipient_email, "roll_number": i.roll_number,
             "event": db.get(Event, i.event_id).name, "status": i.status, "created_at": i.created_at}
            for i in db.query(Issuance).filter_by(club_id=club_id).order_by(Issuance.created_at.desc())]


@app.get("/issuances/{issuance_id}/certificate")
def regenerate_certificate(issuance_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    issuance = db.get(Issuance, issuance_id)
    if not issuance: raise HTTPException(404, "Issuance not found")
    require_club_access(issuance.club_id, user, db)
    pdf = render_certificate(db.get(TemplateVersion, issuance.template_version_id), issuance.credential_package, generate_qr(issuance.credential_id))
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{issuance.credential_id}.pdf"'})


@app.get("/certificates/download")
def download_by_roll_number(roll_no: str, db: Session = Depends(get_db)):
    """Return public certificate choices for a roll number."""
    normalized_roll_number = roll_no.strip()
    issuances = db.query(Issuance).filter(func.lower(Issuance.roll_number) == normalized_roll_number.lower()).order_by(Issuance.created_at.desc()).all()
    if not issuances:
        raise HTTPException(404, "No certificate was found for that roll number")
    return [{
        "id": issuance.id,
        "credential_id": issuance.credential_id,
        "event": db.get(Event, issuance.event_id).name,
        "club": db.get(Club, issuance.club_id).name,
        "issue_date": issuance.credential_package["credential"]["issue_date"],
        "status": issuance.status,
    } for issuance in issuances]


@app.get("/certificates/{issuance_id}/download")
def download_selected_certificate(issuance_id: int, db: Session = Depends(get_db)):
    issuance = db.get(Issuance, issuance_id)
    if not issuance:
        raise HTTPException(404, "Certificate not found")
    pdf = render_certificate(db.get(TemplateVersion, issuance.template_version_id), issuance.credential_package,
                             generate_qr(issuance.credential_id))
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{issuance.credential_id}.pdf"'})


@app.get("/verify/{credential_id}")
def verify_public(credential_id: str, db: Session = Depends(get_db)):
    issuance = db.query(Issuance).filter_by(credential_id=credential_id).first()
    if not issuance: raise HTTPException(404, "Credential not found")
    package = issuance.credential_package; credential = package["credential"]
    return {"verified": calculate_hash(credential) == package["hash"] and verify_signature(credential, package["signature"]), "credential": credential, "status": issuance.status}


@app.post("/verify")
def verify_certificate(package: dict):
    credential = package.get("credential", {})
    return {"verified": calculate_hash(credential) == package.get("hash") and verify_signature(credential, package.get("signature", "")), "credential_id": credential.get("credential_id")}
