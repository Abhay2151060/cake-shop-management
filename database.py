import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from config import MYSQL_URL, SQLITE_URL

logger = logging.getLogger(__name__)

# Attempt to connect to MySQL if configured, fallback gracefully to SQLite
engine = None
try:
    if "mysql" in MYSQL_URL:
        test_engine = create_engine(
            MYSQL_URL,
            connect_args={"connect_timeout": 1},
            pool_pre_ping=True
        )
        with test_engine.connect() as conn:
            pass
        engine = test_engine
        logger.info("Connected to MySQL Database.")
except Exception as e:
    logger.info(f"MySQL not detected or timed out ({e}). Using local SQLite database.")

if engine is None:
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
    logger.info("Using SQLite Database: cherry_blossom.db")

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    import models  # import models to register with Base
    Base.metadata.create_all(bind=engine)
