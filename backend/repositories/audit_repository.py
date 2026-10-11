"""Append-only audit trail.

No Cypher predecessor existed. Deliberately write-only: see the class
docstring.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AuditLog


class AuditRepository:
    """Stateless: the session is supplied per call.

    Intentionally offers no update and no delete. An audit trail that can be
    rewritten is not a record of anything, and models/audit.py deliberately
    omits TimestampMixin's updated_at for the same reason. If you need a way to
    retract a mistaken entry, add a new compensating row — do not add a mutator
    here. (This note exists because "audit logs should be editable, just add an
    update method" is a reasonable-sounding request that this class should
    decline.)
    """

    async def write_log(
        self,
        session: AsyncSession,
        *,
        actor_type: str,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | str,
        actor_id: uuid.UUID | str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Append one audit entry.

        `details` is free-form JSONB and `entity_id` is deliberately not a
        foreign key: the trail has to outlive the row it describes, so nothing
        here may cascade or reference a live entity.
        """
        log = AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
        session.add(log)
        # flush only — the audit row must land in the same transaction as the
        # change it records, or the trail can claim something that was rolled
        # back. Committing the caller's transaction is the caller's call.
        await session.flush()
        return log
