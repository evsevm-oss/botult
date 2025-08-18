from __future__ import annotations

"""stage8: add meal status and idempotency fields

Revision ID: 0002_stage8_meal_status_idempotency
Revises: 0001_init_schema
Create Date: 2025-08-18
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_stage8_meal_status_idempotency"
down_revision = "0001_init_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE meal_status AS ENUM ('draft','confirmed')")
    op.add_column("meals", sa.Column("status", sa.Enum(name="meal_status"), server_default=sa.text("'draft'"), nullable=False))
    op.add_column("meals", sa.Column("source_chat_id", sa.BigInteger(), nullable=True))
    op.add_column("meals", sa.Column("source_message_id", sa.BigInteger(), nullable=True))
    op.add_column("meals", sa.Column("source_update_id", sa.BigInteger(), nullable=True))
    op.create_unique_constraint("uq_meals_user_update", "meals", ["user_id", "source_update_id"]) 
    op.create_unique_constraint("uq_meals_user_chat_msg", "meals", ["user_id", "source_chat_id", "source_message_id"]) 


def downgrade() -> None:
    op.drop_constraint("uq_meals_user_chat_msg", "meals", type_="unique")
    op.drop_constraint("uq_meals_user_update", "meals", type_="unique")
    op.drop_column("meals", "source_update_id")
    op.drop_column("meals", "source_message_id")
    op.drop_column("meals", "source_chat_id")
    op.drop_column("meals", "status")
    op.execute("DROP TYPE meal_status")


