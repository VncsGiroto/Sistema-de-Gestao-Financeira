"""0015 vínculo ativo→conta, kind REINVESTIMENTO e snapshots da carteira."""

import sqlalchemy as sa

from alembic import op

revision = "0015_asset_account"
down_revision = "0014_ledger_movements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("account_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_assets_account", "assets", "accounts", ["account_id"], ["id"], ondelete="RESTRICT")
    op.drop_constraint("uq_assets_user_ticker", "assets", type_="unique")
    op.create_unique_constraint("uq_assets_user_ticker_account", "assets", ["user_id", "ticker", "account_id"])
    op.drop_constraint("ck_op_kind", "investment_ops", type_="check")
    op.create_check_constraint(
        "ck_op_kind", "investment_ops", "kind IN ('APORTE','RESGATE','RENDIMENTO','REINVESTIMENTO')"
    )
    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("cash", sa.Numeric(14, 2), nullable=False),
        sa.Column("positions_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "date", name="uq_snap_user_date"),
    )
    op.create_index("ix_snap_user_date", "portfolio_snapshots", ["user_id", "date"])


def downgrade() -> None:
    op.drop_index("ix_snap_user_date", table_name="portfolio_snapshots")
    op.drop_table("portfolio_snapshots")
    op.drop_constraint("ck_op_kind", "investment_ops", type_="check")
    op.create_check_constraint("ck_op_kind", "investment_ops", "kind IN ('APORTE','RESGATE','RENDIMENTO')")
    op.drop_constraint("uq_assets_user_ticker_account", "assets", type_="unique")
    op.create_unique_constraint("uq_assets_user_ticker", "assets", ["user_id", "ticker"])
    op.drop_constraint("fk_assets_account", "assets", type_="foreignkey")
    op.drop_column("assets", "account_id")
