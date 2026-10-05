"""0014 ledger canônico de movimentações patrimoniais (épico investimentos↔contas)."""

import sqlalchemy as sa

from alembic import op

revision = "0014_ledger_movements"
down_revision = "0013_tx_amount_positive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ledger_movements",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("from_account_id", sa.BigInteger(), nullable=True),
        sa.Column("to_account_id", sa.BigInteger(), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False, server_default="Transferência"),
        sa.Column("op_id", sa.BigInteger(), nullable=True),
        sa.Column("asset_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["to_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["op_id"], ["investment_ops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("kind IN ('TRANSFER','APORTE','RESGATE','REINVESTIMENTO')", name="ck_led_kind"),
        sa.CheckConstraint("amount > 0", name="ck_led_amount"),
        sa.UniqueConstraint("op_id", name="uq_led_op"),
    )
    op.create_index("ix_led_user", "ledger_movements", ["user_id"])
    op.create_index("ix_led_from", "ledger_movements", ["from_account_id"])
    op.create_index("ix_led_to", "ledger_movements", ["to_account_id"])


def downgrade() -> None:
    op.drop_index("ix_led_to", table_name="ledger_movements")
    op.drop_index("ix_led_from", table_name="ledger_movements")
    op.drop_index("ix_led_user", table_name="ledger_movements")
    op.drop_table("ledger_movements")
