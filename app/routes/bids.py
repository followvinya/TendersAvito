from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from app.database import get_session
from app.models import Bid, Employee, Tender, BidStatus, BidAuthorType, BidDecision, BidReview, \
    OrganizationResponsible, TenderStatus, BidChangeStatus, BidHistory, BidDecisionRecord
from app.schemas import BidCreate, BidResponse, BidUpdate, BidReviewCreate, BidReviewResponse
from typing import List
import uuid

router = APIRouter()


# authorID - only user's id; one may choose authorType as organization (though not used in task specification anymore)
@router.post("/bids/new", response_model=BidResponse)
async def create_bid(bid: BidCreate, session: Session = Depends(get_session)):
    tender = session.get(Tender, bid.tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    if tender.status != TenderStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Bids can only be created for published tenders")

    user = session.get(Employee, bid.author_id)
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")

    if bid.author_type == BidAuthorType.ORGANIZATION:
        org_responsible = session.exec(select(OrganizationResponsible).where(
            OrganizationResponsible.user_id == user.id
        )).first()

        if not org_responsible:
            raise HTTPException(status_code=403, detail="User is not responsible for any organization")

    new_bid = Bid(
        name=bid.name,
        description=bid.description,
        tender_id=bid.tender_id,
        author_type=bid.author_type,
        author_id=bid.author_id,
        status=BidStatus.CREATED,
        version=1
    )
    session.add(new_bid)
    session.commit()
    session.refresh(new_bid)

    return new_bid


# bid has unique author
@router.get("/bids/my", response_model=List[BidResponse])
async def get_user_bids(
        username: str,
        limit: int = Query(5, le=50),
        offset: int = Query(0, ge=0),
        session: Session = Depends(get_session)
):
    user = session.exec(select(Employee).where(Employee.username == username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")

    query = select(Bid).where(Bid.author_id == user.id)
    query = query.order_by(Bid.name).offset(offset).limit(limit)
    bids = session.exec(query).all()
    return bids


# only responsible for tender's organization can view; sees only published bids for his company's tender
@router.get("/bids/{tender_id}/list", response_model=List[BidResponse])
async def get_bids_for_tender(
        tender_id: uuid.UUID,
        username: str,
        limit: int = Query(5, le=50),
        offset: int = Query(0, ge=0),
        session: Session = Depends(get_session)
):
    user = session.exec(select(Employee).where(Employee.username == username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")

    tender = session.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    is_tender_org_responsible = session.exec(select(OrganizationResponsible).where(
        OrganizationResponsible.user_id == user.id,
        OrganizationResponsible.organization_id == tender.organization_id
    )).first()

    if not is_tender_org_responsible:
        raise HTTPException(status_code=403, detail="You don't have permission to view bids for this tender")

    query = select(Bid).where(Bid.tender_id == tender_id)
    query = query.where(Bid.status == BidStatus.PUBLISHED)

    bids = session.exec(query.order_by(Bid.name).offset(offset).limit(limit)).all()
    return bids


# bid has single author by the task specification
@router.get("/bids/{bid_id}/status", response_model=BidStatus)
async def get_bid_status(
        bid_id: uuid.UUID,
        username: str,
        session: Session = Depends(get_session)
):
    user = session.exec(select(Employee).where(Employee.username == username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")

    bid = session.get(Bid, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")

    if bid.author_id != user.id:
        raise HTTPException(status_code=403, detail="You are not authorized to view the status of this bid")
    return bid.status


# only bid author can change status
@router.put("/bids/{bid_id}/status", response_model=BidResponse)
async def update_bid_status(
        bid_id: uuid.UUID,
        status: BidChangeStatus,
        username: str,
        session: Session = Depends(get_session)
):
    user = session.exec(select(Employee).where(Employee.username == username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")
    bid = session.get(Bid, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")

    if bid.author_id != user.id:
        raise HTTPException(status_code=403, detail="User is not authorized to update the status of this bid")

    tender = session.get(Tender, bid.tender_id)
    if bid.status in {BidStatus.APPROVED, BidStatus.REJECTED} or tender.status == TenderStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Cannot change status after a decision has been made")

    if status == BidChangeStatus.PUBLISHED:
        bid.status = BidStatus.PUBLISHED
    elif status == BidChangeStatus.CREATED:
        bid.status = TenderStatus.CREATED
    elif status == BidChangeStatus.CANCELED:
        bid.status = BidStatus.CANCELED
    else:
        raise HTTPException(status_code=400, detail="Invalid status")

    session.commit()
    session.refresh(bid)

    return bid


# only bid author can change bid
@router.patch("/bids/{bid_id}/edit", response_model=BidResponse)
async def edit_bid(
        bid_id: uuid.UUID,
        bid_update: BidUpdate,
        username: str,
        session: Session = Depends(get_session)
):
    user = session.exec(select(Employee).where(Employee.username == username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")

    bid = session.get(Bid, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")

    if bid.author_id != user.id:
        raise HTTPException(status_code=403, detail="User is not authorized to edit this bid")

    tender = session.get(Tender, bid.tender_id)
    if bid.status in {BidStatus.APPROVED, BidStatus.REJECTED} or tender.status == TenderStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Cannot edit an approved or rejected bid")

    bid_history = BidHistory(
        bid_id=bid.id,
        name=bid.name,
        description=bid.description,
        version=bid.version,
    )
    session.add(bid_history)

    bid_data = bid_update.dict(exclude_unset=True)
    for key, value in bid_data.items():
        setattr(bid, key, value)

    bid.version += 1
    session.commit()
    session.refresh(bid)
    return bid


# only responsible for tender's organization can submit decision
@router.put("/bids/{bid_id}/submit_decision", response_model=BidResponse)
async def submit_bid_decision(
        bid_id: uuid.UUID,
        decision: BidDecision,
        username: str,
        session: Session = Depends(get_session)
):
    user = session.exec(select(Employee).where(Employee.username == username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")

    bid = session.get(Bid, bid_id)
    if not bid or bid.status != BidStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Bid not found")

    tender = session.get(Tender, bid.tender_id)
    org_resp = session.exec(select(OrganizationResponsible).where(
        OrganizationResponsible.user_id == user.id,
        OrganizationResponsible.organization_id == tender.organization_id
    )).first()
    if not org_resp:
        raise HTTPException(status_code=403, detail="User is not responsible for this organization")

    if bid.status in {BidStatus.APPROVED, BidStatus.REJECTED} or tender.status == TenderStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Cannot change status after a decision has been made")

    existing_decision = session.exec(select(BidDecisionRecord).where(
        BidDecisionRecord.bid_id == bid.id,
        BidDecisionRecord.user_id == user.id
    )).first()

    if existing_decision:
        raise HTTPException(status_code=400, detail="You have already submitted a decision for this bid")

    new_decision = BidDecisionRecord(
        bid_id=bid.id,
        user_id=user.id,
        decision=decision
    )
    session.add(new_decision)
    all_decisions = session.exec(select(BidDecisionRecord).where(BidDecisionRecord.bid_id == bid.id)).all()

    responsible_count = session.exec(select(func.count(OrganizationResponsible.id)).where(
        OrganizationResponsible.organization_id == tender.organization_id
    )).first()

    quorum = min(3, responsible_count)
    if any(d.decision == BidDecision.REJECTED for d in all_decisions):
        bid.status = BidStatus.REJECTED
    elif sum(1 for d in all_decisions if d.decision == BidDecision.APPROVED) >= quorum:
        bid.status = BidStatus.APPROVED
        tender.status = TenderStatus.CLOSED

    '''
        if decision == BidDecision.APPROVED:    # this was a version without quorum
            bid.status = BidStatus.APPROVED
            tender.status = TenderStatus.CLOSED
        else:
            bid.status = BidStatus.REJECTED
    '''
    session.commit()
    session.refresh(bid)
    return bid


# only responsible for bid can roll back
@router.put("/bids/{bid_id}/rollback/{version}", response_model=BidResponse)
async def rollback_bid(
        bid_id: uuid.UUID,
        version: int,
        username: str,
        session: Session = Depends(get_session)
):
    user = session.exec(select(Employee).where(Employee.username == username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")

    bid = session.get(Bid, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")

    if bid.author_id != user.id:
        raise HTTPException(status_code=403, detail="User is not the author of this bid")

    tender = session.get(Tender, bid.tender_id)
    if tender.status == TenderStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Cannot rollback a bid for a closed tender")

    if version >= bid.version:
        raise HTTPException(status_code=400, detail="Invalid version for rollback")

    historical_bid = session.exec(
        select(BidHistory)
        .where(BidHistory.bid_id == bid_id, BidHistory.version == version)
    ).first()

    if not historical_bid:
        raise HTTPException(status_code=404, detail="Historical version not found")

    bid_history = BidHistory(
        bid_id=bid.id,
        name=bid.name,
        description=bid.description,
        version=bid.version,
    )
    session.add(bid_history)

    bid.name = historical_bid.name
    bid.description = historical_bid.description
    bid.version += 1

    session.commit()
    session.refresh(bid)
    return bid


@router.put("/bids/{bid_id}/feedback", response_model=BidReviewResponse)
async def submit_bid_feedback(
        bid_id: uuid.UUID,
        feedback: BidReviewCreate,
        username: str,
        session: Session = Depends(get_session)
):
    user = session.exec(select(Employee).where(Employee.username == username)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User does not exist")

    bid = session.get(Bid, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")

    tender = session.get(Tender, bid.tender_id)
    org_resp = session.exec(select(OrganizationResponsible).where(
        OrganizationResponsible.user_id == user.id,
        OrganizationResponsible.organization_id == tender.organization_id
    )).first()

    if not org_resp:
        raise HTTPException(status_code=403, detail="User is not responsible for this organization")

    new_review = BidReview(
        description=feedback.description,
        bid_id=bid.id,
        reviewer_id=user.id
    )
    session.add(new_review)
    session.commit()
    session.refresh(new_review)
    return new_review


@router.get("/bids/{tender_id}/reviews", response_model=List[BidReviewResponse])
async def get_bid_reviews(
        tender_id: uuid.UUID,
        author_username: str,
        requester_username: str,
        limit: int = Query(5, le=50),
        offset: int = Query(0, ge=0),
        session: Session = Depends(get_session)
):
    requester = session.exec(select(Employee).where(Employee.username == requester_username)).first()
    if not requester:
        raise HTTPException(status_code=401, detail="Requester does not exist")

    author = session.exec(select(Employee).where(Employee.username == author_username)).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author does not exist")

    tender = session.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    org_resp = session.exec(select(OrganizationResponsible).where(
        OrganizationResponsible.user_id == requester.id,
        OrganizationResponsible.organization_id == tender.organization_id
    )).first()

    if not org_resp:
        raise HTTPException(status_code=403, detail="Requester is not responsible for this organization")

    author_bid = session.exec(select(Bid).where(
        Bid.tender_id == tender_id,
        Bid.author_id == author.id
    )).first()
    if not author_bid:
        raise HTTPException(status_code=404, detail="Author has not created a bid for this tender")

    query = select(BidReview).join(Bid).where(Bid.author_id == author.id)
    query = query.order_by(BidReview.created_at.desc()).offset(offset).limit(limit)
    reviews = session.exec(query).all()
    return reviews

