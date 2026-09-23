"""0004 transactions (import_id entra no Épico 3, nullable)."""

import sqlalchemy as sa

from alembic import op

revision = "0004_transactions"
down_revision = "0003_accounts_categories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("source", sa.String(20), server_default="MANUAL", nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("type IN ('INCOME','EXPENSE')", name="ck_tx_type"),
        sa.CheckConstraint("source IN ('MANUAL','OFX','IMPORT')", name="ck_tx_source"),
        sa.CheckConstraint("amount <> 0", name="ck_tx_amount"),
        sa.UniqueConstraint("user_id", "source", "external_id", name="uq_tx_user_source_external"),
    )
    op.create_index("ix_tx_user_date", "transactions", ["user_id", sa.text("date DESC")])
    op.create_index("ix_tx_acct_date_amt", "transactions", ["account_id", "date", "amount"])
    op.create_index("ix_tx_category", "transactions", ["category_id"])


def downgrade() -> None:
    op.drop_index("ix_tx_category", table_name="transactions")
    op.drop_index("ix_tx_acct_date_amt", table_name="transactions")
    op.drop_index("ix_tx_user_date", table_name="transactions")
    op.drop_table("transactions")
