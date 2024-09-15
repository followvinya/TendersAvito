from sqlalchemy import String, Integer, ForeignKey, Enum, DateTime, UUID, Column, MetaData
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid
from enum import Enum as PyEnum

metadata = MetaData()
Base = declarative_base()


class OrganizationType(PyEnum):
    IE = "IE"
    LLC = "LLC"
    JSC = "JSC"


class TenderStatus(PyEnum):
    CREATED = "Created"
    PUBLISHED = "Published"
    CLOSED = "Closed"


class TenderServiceType(PyEnum):
    CONSTRUCTION = "Construction"
    DELIVERY = "Delivery"
    MANUFACTURE = "Manufacture"


class BidStatus(PyEnum):
    CREATED = "Created"
    PUBLISHED = "Published"
    CANCELED = "Canceled"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class BidAuthorType(PyEnum):
    ORGANIZATION = "Organization"
    USER = "User"


class BidChangeStatus(PyEnum):
    CREATED = "Created"
    PUBLISHED = "Published"
    CANCELED = "Canceled"


class BidDecision(PyEnum):
    APPROVED = "Approved"
    REJECTED = "Rejected"


class Employee(Base):
    __tablename__ = 'employee'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, index=True)
    first_name = Column(String(50))
    last_name = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Organization(Base):
    __tablename__ = 'organization'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100))
    description = Column(String, nullable=True)
    type = Column(Enum(OrganizationType))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrganizationResponsible(Base):
    __tablename__ = 'organization_responsible'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organization.id'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('employee.id'))


class Tender(Base):
    __tablename__ = 'tender'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100))
    description = Column(String(500))
    service_type = Column(Enum(TenderServiceType))
    status = Column(Enum(TenderStatus), default=TenderStatus.CREATED)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organization.id'))
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class Bid(Base):
    __tablename__ = 'bid'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100))
    description = Column(String(500))
    status = Column(Enum(BidStatus), default=BidStatus.CREATED)
    tender_id = Column(UUID(as_uuid=True), ForeignKey('tender.id'))
    author_type = Column(Enum(BidAuthorType))
    author_id = Column(UUID(as_uuid=True))
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class BidReview(Base):
    __tablename__ = 'bid_review'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description = Column(String(1000))
    bid_id = Column(UUID(as_uuid=True), ForeignKey('bid.id'))
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey('employee.id'))
    created_at = Column(DateTime, default=datetime.utcnow)


class TenderHistory(Base):
    __tablename__ = 'tender_history'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey('tender.id'))
    name = Column(String(100))
    description = Column(String(500))
    service_type = Column(Enum(TenderServiceType))
    version = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class BidHistory(Base):
    __tablename__ = 'bid_history'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bid_id = Column(UUID(as_uuid=True), ForeignKey('bid.id'))
    name = Column(String(100))
    description = Column(String(500))
    version = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class BidDecisionRecord(Base):
    __tablename__ = 'bid_decision_record'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bid_id = Column(UUID(as_uuid=True), ForeignKey('bid.id'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('employee.id'))
    decision = Column(Enum(BidDecision))
    created_at = Column(DateTime, default=datetime.utcnow)