from fastapi import HTTPException
from sqlmodel import Session, select
from app.models import Employee, Tender, OrganizationResponsible
import uuid


def get_user_or_raise(username: str, session: Session):
    user = session.exec(select(Employee).where(Employee.username == username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")
    return user


def get_tender_or_raise(tender_id: uuid.UUID, session: Session):
    tender = session.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender


def check_org_responsible(user_id: uuid.UUID, organization_id: uuid.UUID, session: Session):
    org_resp = session.exec(select(OrganizationResponsible).where(
        OrganizationResponsible.user_id == user_id,
        OrganizationResponsible.organization_id == organization_id
    )).first()
    if not org_resp:
        raise HTTPException(status_code=403, detail="User is not responsible for this organization")
    return org_resp
