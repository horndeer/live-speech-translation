from models import Conversation, Message
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime
import logging
import os

DEV_MODE = os.environ.get("DEV_MODE", "False") == "True"

logger = logging.getLogger(__name__)
if DEV_MODE:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

# 1. Configuration
# Note: On garde create_async_engine de SQLAlchemy car SQLModel ne l'expose pas encore
DATABASE_URL = "sqlite+aiosqlite:///./database.db"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)


# 2. Initialisation (Création des tables)
async def init_db():
    async with engine.begin() as conn:
        # Ici on utilise bien SQLModel pour créer la structure
        await conn.run_sync(SQLModel.metadata.create_all)


# 3. La Fabrique de Session (Le "Factory")
# On configure le factory pour qu'il produise des sessions SQLModel
async_session_factory = sessionmaker(
    bind=engine,
    class_=AsyncSession,  # On utilise la session SQLModel importée plus haut
    expire_on_commit=False,
)


# 4. Fonction utilitaire pour récupérer une session
# À utiliser dans main.py ou crud.py
async def get_session():
    async with async_session_factory() as session:
        yield session


# Helper pour avoir une session rapidement


async def create_conversation(title: str):
    async with async_session_factory() as session:
        conv = Conversation(title=title)
        session.add(conv)
        await session.commit()
        await session.refresh(conv),
        return conv


async def add_message(
    conversation_id: int, fr: str, es: str, source_language: str, timestamp: datetime
):
    async with async_session_factory() as session:
        msg = Message(
            conversation_id=conversation_id,
            fr=fr,
            es=es,
            source_language=source_language,
            timestamp=timestamp,
        )
        session.add(msg)
        await session.commit()
        await session.refresh(msg)
        logger.debug(f"Message sauvegardé: {msg.id}")


async def get_conversations():
    async with async_session_factory() as session:
        statement = select(Conversation).order_by(Conversation.created_at.desc())
        result = await session.exec(statement)
        return result.all()
    
async def get_conversation_by_id(conversation_id: int):
    async with async_session_factory() as session:
        statement = select(Conversation).where(Conversation.id == conversation_id)
        result = await session.exec(statement)
        return result.one_or_none()
    
async def get_last_conversation():
    async with async_session_factory() as session:
        statement = select(Conversation).order_by(Conversation.created_at.desc())
        result = await session.exec(statement)
        return result.first()

async def get_conversation_list():
    convs = await get_conversations()
    return [
        {"id": conv.id, "title": conv.title}
        for conv in sorted(convs, key=lambda x: x.created_at, reverse=True)
    ]


async def get_messages_by_conversation(conversation_id: int):
    async with async_session_factory() as session:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp)
        )
        result = await session.exec(statement)
        return result.all()
