"""0018 alíquota esperada de IR por ativo (líquido estimado; só exibição).

Coluna anulável sem default: ativos existentes ficam NULL (= estimativa automática
pela classe). Reversível: drop da constraint + coluna não perde nenhum dado
essencial (a alíquota pode ser informada de novo).
"""

import sqlalchemy as sa

from alembic import op

revision = "0018_asset_tax_rate"
down_revision = "0017_snapshot_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("tax_rate", sa.Numeric(5, 2), nullable=True))
    op.create_check_constraint("ck_asset_tax_rate", "assets", "tax_rate IS NULL OR (tax_rate >= 0 AND tax_rate <= 100)")


def downgrade() -> None:
    op.drop_constraint("ck_asset_tax_rate", "assets", type_="check")
    op.drop_column("assets", "tax_rate")
