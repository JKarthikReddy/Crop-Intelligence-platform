"""Shared FastAPI dependencies (auth, pagination, etc.)."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_session(session: DBSession) -> AsyncSession:
    """Provide a database session dependency."""
    return session
