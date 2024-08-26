from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from database.models import Base

from config_reader import config


engine = create_async_engine(config.DATABASE_URL, echo=False)
session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def create_db():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def drop_db():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
