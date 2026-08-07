"""
Database Session Module
Configures the SQLAlchemy asynchronous engine and session maker for SQLite.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config.settings import settings
from app.database.base import Base

# Create the async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.ENVIRONMENT == "development"),
    # SQLite specific connection args
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# Create a configured "Session" class
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    """
    Dependency to get the database session.
    Yields an AsyncSession and ensures it is closed after use.
    """
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    """
    Initialize the database, creating all tables.
    (Note: In a production environment, use Alembic for migrations instead.)
    """
    # Import models so they register with Base.metadata
    import app.models.user  # noqa: F401
    import app.models.chat  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

