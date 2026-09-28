"""0011 preços: asset_prices + termos de RF em assets (Épico 7.2b)."""

from alembic import op
import sqlalchemy as sa

revision = "0011_prices"
down_revision = "0010_investments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("rate_type", sa.String(20), nullable=True))
    op.add_column("assets", sa.Column("rate", sa.Numeric(10, 4), nullable=True))
    op.add_column("assets", sa.Column("maturity_date", sa.Date(), nullable=True))
    op.create_check_constraint(
        "ck_asset_rate", "assets", "rate_type IN ('CDI_PCT','PREFIXADO','IPCA_MAIS')"
    )
    op.create_table(
        "asset_prices",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("price", sa.Numeric(18, 8), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("source IN ('BRAPI','MANUAL','ACCRUAL')", name="ck_price_source"),
        sa.UniqueConstraint("asset_id", "date", "source", name="uq_price_asset_date_source"),
    )
    op.create_index("ix_prices_asset_date", "asset_prices", ["asset_id", "date"])


def downgrade() -> None:
    op.drop_index("ix_prices_asset_date", table_name="asset_prices")
    op.drop_table("asset_prices")
    op.drop_constraint("ck_asset_rate", "assets", type_="check")
    op.drop_column("assets", "maturity_date")
    op.drop_column("assets", "rate")
    op.drop_column("assets", "rate_type")
