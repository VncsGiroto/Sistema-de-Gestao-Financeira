"""0007 installments (Épico 4.2)."""

import sqlalchemy as sa

from alembic import op

revision = "0007_installments"
down_revision = "0006_recurring_bills"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "installments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("num_installments", sa.Integer(), nullable=False),
        sa.Column("installment_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("first_due_date", sa.Date(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("num_installments BETWEEN 2 AND 60", name="ck_inst_num"),
        sa.CheckConstraint("total_amount > 0", name="ck_inst_total"),
    )
    op.create_index("ix_inst_user", "installments", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_inst_user", table_name="installments")
    op.drop_table("installments")
