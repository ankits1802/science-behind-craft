from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_voice_session_binding"
down_revision: str | Sequence[str] | None = "0005_region_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TRANSPORT_CHECK = "VoiceSession_transport_check"


def upgrade() -> None:
    op.add_column(
        "VoiceSession", sa.Column("transport", sa.String(length=16), server_default="RELAY", nullable=False)
    )
    op.add_column("VoiceSession", sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "VoiceSession",
        sa.Column("maxDurationSeconds", sa.Integer(), server_default=sa.text("600"), nullable=False),
    )
    op.create_check_constraint(op.f(TRANSPORT_CHECK), "VoiceSession", "transport IN ('AGENT', 'RELAY')")


def downgrade() -> None:
    op.drop_constraint(op.f(TRANSPORT_CHECK), "VoiceSession", type_="check")
    op.drop_column("VoiceSession", "maxDurationSeconds")
    op.drop_column("VoiceSession", "expiresAt")
    op.drop_column("VoiceSession", "transport")
