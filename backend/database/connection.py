"""
Database connection and session management.
Supports SQLite (default) and MySQL.
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    db_type = os.getenv("DATABASE_TYPE", "sqlite")
    
    if db_type == "mysql":
        host = os.getenv("MYSQL_HOST", "localhost")
        port = os.getenv("MYSQL_PORT", "3306")
        db = os.getenv("MYSQL_DATABASE", "supplychain_ai")
        user = os.getenv("MYSQL_USER", "root")
        password = os.getenv("MYSQL_PASSWORD", "")
        return f"mysql+aiomysql://{user}:{password}@{host}:{port}/{db}"
    
    # Default: SQLite
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./supplychain.db")
    if db_url.startswith("sqlite:///"):
        db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    return db_url


DATABASE_URL = get_database_url()

connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize the database: create all tables and seed data if empty."""
    from database.models import (
        Product, Warehouse, Supplier, SupplierProduct,
        Sale, Inventory, Customer, TransportRoute, Shipment
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created.")
    
    # Seed sample data if empty
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, func
        result = await session.execute(select(func.count()).select_from(Product))
        count = result.scalar()
        if count == 0:
            logger.info("Seeding database with sample data...")
            from database.seed import seed_all
            await seed_all(session)
            logger.info("Sample data seeded.")
