"""0003 accounts + categories."""

import sqlalchemy as sa

from alembic import op

revision = "0003_accounts_categories"
down_revision = "0002_password_resets"
branch_labels = None
depends_on = None

ACCOUNT_TYPES = ("CHECKING", "SAVINGS", "CREDIT_CARD", "CASH", "OTHER")
CATEGORY_TYPES = ("INCOME", "EXPENSE")


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("bank", sa.String(120), nullable=True),
        sa.Column("account_type", sa.String(20), nullable=False),
        sa.Column("initial_balance", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"account_type IN {ACCOUNT_TYPES}", name="ck_accounts_type"),
    )
    op.create_index("ix_accounts_user", "accounts", ["user_id"])
    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"type IN {CATEGORY_TYPES}", name="ck_categories_type"),
        sa.UniqueConstraint("user_id", "name", "type", name="uq_categories_user_name_type"),
    )
    op.create_index("ix_categories_user", "categories", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_categories_user", table_name="categories")
    op.drop_table("categories")
    op.drop_index("ix_accounts_user", table_name="accounts")
    op.drop_table("accounts")
