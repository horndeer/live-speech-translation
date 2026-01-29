from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

# Table des Conversations (Sessions)
class Conversation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    created_at: datetime = Field(default_factory=datetime.now)

    messages: List["Message"] = Relationship(back_populates="conversation")

# Table des Messages
class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id") # Lien vers la session
    
    fr: str
    es: str
    timestamp: datetime
    source_language: str

    conversation: Optional[Conversation] = Relationship(back_populates="messages")