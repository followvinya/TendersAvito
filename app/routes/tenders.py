from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.database import get_session
from app.models import Tender, Employee, OrganizationResponsible, TenderStatus, Bid, BidStatus, \
    TenderServiceType, TenderHistory
from app.schemas import TenderCreate, TenderResponse, TenderUpdate
from typing import List
import uuid

router = APIRouter()


@router.post("/tenders/new", response_model=TenderResponse)
async def create_tender(
        tender: TenderCreate,
        session: Session = Depends(get_session)
):
    user = session.exec(select(Employee).where(
        Employee.username == tender.creator_username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")

    org_resp = session.exec(select(OrganizationResponsible).where(
        OrganizationResponsible.user_id == user.id,
        OrganizationResponsible.organization_id == tender.organization_id
    )).first()
    if not org_resp:
        raise HTTPException(status_code=403, detail="User is not responsible for this organization")

    new_tender = Tender(
        name=tender.name,
        description=tender.description,
        service_type=tender.service_type,
        organization_id=tender.organization_id,
        status=TenderStatus.CREATED
    )
    session.add(new_tender)
    session.commit()
    session.refresh(new_tender)
    return new_tender


# all PUBLISHED tenders, visible for all users
@router.get("/tenders", response_model=List[TenderResponse])
async def get_tenders(
        service_type: List[TenderServiceType] = Query(None),
        limit: int = Query(5, le=50),
        offset: int = Query(0, ge=0),
        session: Session = Depends(get_session)
):
    query = select(Tender).where(Tender.status == TenderStatus.PUBLISHED)
    if service_type:
        query = query.where(Tender.service_type.in_(service_type))
    query = query.order_by(Tender.name).offset(offset).limit(limit)
    tenders = session.exec(query).all()
    return tenders


# all responsible for organization can view organization's tenders as their
@router.get("/tenders/my", response_model=List[TenderResponse])
async def get_user_tenders(
        username: str,
        limit: int = Query(5, le=50),
        offset: int = Query(0, ge=0),
        session: Session = Depends(get_session)
):
    user = session.exec(select(Employee).where(Employee.username == username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")

    query = select(Tender).join(OrganizationResponsible,
                                Tender.organization_id == OrganizationResponsible.organization_id)
    query = query.where(OrganizationResponsible.user_id == user.id)
    query = query.order_by(Tender.name).offset(offset).limit(limit)
    tenders = session.exec(query).all()
    return tenders


# only organization responsible can view closed/created tenders
@router.get("/tenders/{tender_id}/status", response_model=TenderStatus)
async def get_tender_status(
        tender_id: uuid.UUID,
        username: str,
        session: Session = Depends(get_session)
):
    user = session.exec(select(Employee).where(Employee.username == username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")

    tender = session.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    org_resp = session.exec(select(OrganizationResponsible).where(
        OrganizationResponsible.user_id == user.id,
        OrganizationResponsible.organization_id == tender.organization_id
    )).first()

    if not org_resp:
        raise HTTPException(status_code=403, detail="User is not authorized to view the status of this tender")
    return tender.status


# only organization responsible can edit
@router.put("/tenders/{tender_id}/status", response_model=TenderResponse)
async def update_tender_status(
        tender_id: uuid.UUID,
        status: TenderStatus,
        username: str,
        session: Session = Depends(get_session)
):
    user = session.exec(select(Employee).where(Employee.username == username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")

    tender = session.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    org_resp = session.exec(select(OrganizationResponsible).where(
        OrganizationResponsible.user_id == user.id,
        OrganizationResponsible.organization_id == tender.organization_id
    )).first()

    if not org_resp:
        raise HTTPException(status_code=403, detail="User is not responsible for this organization")

    tender.status = status

    if status == TenderStatus.CLOSED:  # Close all associated bids
        bids = session.exec(select(Bid).where(Bid.tender_id == tender_id)).all()
        for bid in bids:
            bid.status = BidStatus.CANCELED

    session.commit()
    session.refresh(tender)
    return tender


# only organization responsible can edit
@router.patch("/tenders/{tender_id}/edit", response_model=TenderResponse)
async def edit_tender(
        tender_id: uuid.UUID,
        tender_update: TenderUpdate,
        username: str,
        session: Session = Depends(get_session)
):
    user = session.exec(select(Employee).where(Employee.username == username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")

    tender = session.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    org_resp = session.exec(select(OrganizationResponsible).where(
        OrganizationResponsible.user_id == user.id,
        OrganizationResponsible.organization_id == tender.organization_id
    )).first()

    if not org_resp:
        raise HTTPException(status_code=403, detail="User is not responsible for this organization")

    tender_history = TenderHistory(        # for rollback
        tender_id=tender.id,
        name=tender.name,
        description=tender.description,
        service_type=tender.service_type,
        version=tender.version,
    )
    session.add(tender_history)

    tender_data = tender_update.dict(exclude_unset=True)
    for key, value in tender_data.items():
        setattr(tender, key, value)

    tender.version += 1
    session.commit()
    session.refresh(tender)
    return tender


@router.put("/tenders/{tender_id}/rollback/{version}", response_model=TenderResponse)
async def rollback_tender(
        tender_id: uuid.UUID,
        version: int,
        username: str,
        session: Session = Depends(get_session)
):
    user = session.exec(select(Employee).where(Employee.username == username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")

    tender = session.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    org_resp = session.exec(select(OrganizationResponsible).where(
        OrganizationResponsible.user_id == user.id,
        OrganizationResponsible.organization_id == tender.organization_id
    )).first()

    if not org_resp:
        raise HTTPException(status_code=403, detail="User is not responsible for this organization")

    if version >= tender.version:
        raise HTTPException(status_code=400, detail="Invalid version for rollback")

    historical_tender = session.exec(
        select(TenderHistory)
        .where(TenderHistory.tender_id == tender_id, TenderHistory.version == version)
    ).first()

    if not historical_tender:
        raise HTTPException(status_code=404, detail="Historical version not found")

    tender_history = TenderHistory(
        tender_id=tender.id,
        name=tender.name,
        description=tender.description,
        service_type=tender.service_type,
        version=tender.version,
    )
    session.add(tender_history)

    tender.name = historical_tender.name
    tender.description = historical_tender.description
    tender.service_type = historical_tender.service_type

    tender.version += 1
    session.commit()
    session.refresh(tender)
    return tender
