"""0010 investments: assets + investment_ops (Épico 7.1, livro de operações)."""

from alembic import op
import sqlalchemy as sa

revision = "0010_investments"
down_revision = "0009_payables"
branch_labels = None
depends_on = None

CLASSES = "('RENDA_FIXA','RENDA_VARIAVEL','FUNDOS','CRIPTO','OUTROS')"
KINDS = "('APORTE','RESGATE','RENDIMENTO')"


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("name", sa.String(120), nullable=True),
        sa.Column("asset_class", sa.String(20), nullable=False),
        sa.Column("subtype", sa.String(20), nullable=False),
        sa.Column("custodian", sa.String(80), nullable=True),
        sa.Column("currency", sa.String(3), server_default="BRL", nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"asset_class IN {CLASSES}", name="ck_asset_class"),
        sa.UniqueConstraint("user_id", "ticker", name="uq_assets_user_ticker"),
    )
    op.create_index("ix_assets_user", "assets", ["user_id"])
    op.create_table(
        "investment_ops",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=True),
        sa.Column("price", sa.Numeric(18, 8), nullable=True),
        sa.Column("fees", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("transaction_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"kind IN {KINDS}", name="ck_op_kind"),
        sa.CheckConstraint("amount > 0", name="ck_op_amount"),
        sa.CheckConstraint("fees >= 0", name="ck_op_fees"),
    )
    op.create_index("ix_ops_asset_date", "investment_ops", ["asset_id", "date"])


def downgrade() -> None:
    op.drop_index("ix_ops_asset_date", table_name="investment_ops")
    op.drop_table("investment_ops")
    op.drop_index("ix_assets_user", table_name="assets")
    op.drop_table("assets")
