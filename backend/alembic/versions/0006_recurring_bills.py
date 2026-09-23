"""0006 recurring_bills (Épico 4.1)."""

import sqlalchemy as sa

from alembic import op

revision = "0006_recurring_bills"
down_revision = "0005_imports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recurring_bills",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("periodicity", sa.String(10), nullable=True),
        sa.Column("due_day", sa.Integer(), nullable=True),
        sa.Column("next_due", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("kind IN ('FIXED','VARIABLE','ONE_TIME','RECURRING')", name="ck_bills_kind"),
        sa.CheckConstraint("periodicity IN ('MONTHLY','WEEKLY','YEARLY')", name="ck_bills_periodicity"),
        sa.CheckConstraint("due_day BETWEEN 1 AND 31", name="ck_bills_due_day"),
    )
    op.create_index("ix_bills_user_next", "recurring_bills", ["user_id", "next_due"])


def downgrade() -> None:
    op.drop_index("ix_bills_user_next", table_name="recurring_bills")
    op.drop_table("recurring_bills")
