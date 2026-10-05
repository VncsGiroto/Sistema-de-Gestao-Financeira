"""0016 override manual de preço (MANUAL_OVERRIDE) para RF com contrato."""

from alembic import op

revision = "0016_price_override"
down_revision = "0015_asset_account"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_price_source", "asset_prices", type_="check")
    op.create_check_constraint(
        "ck_price_source", "asset_prices", "source IN ('BRAPI','MANUAL','ACCRUAL','MANUAL_OVERRIDE')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM asset_prices WHERE source = 'MANUAL_OVERRIDE'")
    op.drop_constraint("ck_price_source", "asset_prices", type_="check")
    op.create_check_constraint("ck_price_source", "asset_prices", "source IN ('BRAPI','MANUAL','ACCRUAL')")
