from pydantic import BaseModel, Field, ConfigDict
from app.models import TenderStatus, TenderServiceType, BidStatus, BidAuthorType
from datetime import datetime
import uuid


class TenderCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: str = Field(..., max_length=500)
    service_type: TenderServiceType
    organization_id: uuid.UUID
    creator_username: str


class TenderResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    status: TenderStatus
    service_type: TenderServiceType
    version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenderUpdate(BaseModel):
    name: str = Field(None, max_length=100)
    description: str = Field(None, max_length=500)
    service_type: TenderServiceType = None


class BidCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: str = Field(..., max_length=500)
    tender_id: uuid.UUID
    author_type: BidAuthorType
    author_id: uuid.UUID


class BidResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: BidStatus
    author_type: BidAuthorType
    author_id: uuid.UUID
    version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BidUpdate(BaseModel):
    name: str = Field(None, max_length=100)
    description: str = Field(None, max_length=500)


class BidReviewCreate(BaseModel):
    description: str = Field(..., max_length=1000)


class BidReviewResponse(BaseModel):
    id: uuid.UUID
    description: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
