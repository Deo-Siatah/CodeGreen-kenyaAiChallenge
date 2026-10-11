from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AuditLog
from repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, repository: AuditRepository | None = None) -> None:
        self.repository = repository or AuditRepository()

    async def write_log(
        self,
        session: AsyncSession,
        actor_type: str,
        actor_id: uuid.UUID | str | None,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | str,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Write an audit entry; the caller owns the transaction commit."""
        log_entry = await self.repository.write_log(
            session,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
        await session.flush()
        return log_entry