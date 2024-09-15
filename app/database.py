from sqlmodel import SQLModel, Session
from app.models import Tender, Bid, BidReview, TenderHistory, BidHistory, BidDecisionRecord
from sqlmodel import create_engine

DB_HOST = "rc1b-5xmqy6bq501kls4m.mdb.yandexcloud.net"
DB_PORT = "6432"
DB_NAME = "cnrprod1725722501-team-78701"
DB_USER = "cnrprod1725722501-team-78701"
DB_PASSWORD = "cnrprod1725722501-team-78701"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

DATABASE_URL += "?target_session_attrs=read-write"

engine = create_engine(DATABASE_URL)

JDBC_URL = f"jdbc:postgresql://{DB_HOST}:{DB_PORT}/{DB_NAME}?targetServerType=primary"


def get_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    SQLModel.metadata.create_all(engine, tables=[Tender.__table__, Bid.__table__,
                                                 BidReview.__table__, TenderHistory.__table__, BidHistory.__table__,
                                                 BidDecisionRecord.__table__])
