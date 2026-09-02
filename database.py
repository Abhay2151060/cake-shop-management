import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from config import MYSQL_URL, SQLITE_URL

logger = logging.getLogger(__name__)

# Use the configured SQL database when one is supplied via environment,
# otherwise fall back to the bundled local SQLite database.
engine = None
if MYSQL_URL:
    try:
        connect_args = {"connect_timeout": 3} if "mysql" in MYSQL_URL else {}
        test_engine = create_engine(
            MYSQL_URL,
            connect_args=connect_args,
            pool_pre_ping=True
        )
        with test_engine.connect():
            pass
        engine = test_engine
        logger.info("Connected to the configured SQL database.")
    except Exception as e:
        logger.warning("Configured database unavailable (%s). Falling back to local SQLite.", e)

if engine is None:
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
    logger.info("Using SQLite Database: cherry_blossom.db")

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()

if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        """SQLite ignores FOREIGN KEY constraints unless enabled per connection."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        # scoped_session keeps a registry per thread; remove() closes the session
        # AND clears the registry so a stale session is never handed out again.
        SessionLocal.remove()

def init_db():
    import models  # import models to register with Base
    Base.metadata.create_all(bind=engine)
