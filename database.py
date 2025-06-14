from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, select, update, insert
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from config import DATABASE_URL, MAX_DOWNLOADS_PER_USER

engine = create_async_engine(DATABASE_URL)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    user_id = Column(BigInteger, primary_key=True, index=True)
    download_count = Column(Integer, default=0)
    last_reset = Column(DateTime, default=datetime.utcnow)
    language_code = Column(String)

async def setup_database():
    """Создает таблицы в базе данных."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_user_locale(user_id: int) -> str | None:
    """Получает язык пользователя из БД."""
    async with async_session_maker() as session:
        result = await session.execute(select(User.language_code).where(User.user_id == user_id))
        return result.scalar_one_or_none()

async def update_user_language(user_id: int, lang_code: str):
    """Обновляет или создает пользователя с новым языком."""
    async with async_session_maker() as session:
        stmt = update(User).where(User.user_id == user_id).values(language_code=lang_code)
        result = await session.execute(stmt)
        if result.rowcount == 0:
            stmt = insert(User).values(user_id=user_id, language_code=lang_code)
            await session.execute(stmt)
        await session.commit()

async def check_and_update_limit(user_id: int) -> bool:
    """Проверяет и обновляет лимиты скачиваний."""
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        
        now = datetime.utcnow()
        
        if user:
            if user.last_reset is None or now - user.last_reset > timedelta(days=1):
                user.download_count = 1
                user.last_reset = now
            elif user.download_count >= MAX_DOWNLOADS_PER_USER:
                return False
            else:
                user.download_count += 1
        else:
            user = User(user_id=user_id, download_count=1, last_reset=now)
            session.add(user)
            
        await session.commit()
        return True