"""0017 qualidade do snapshot da carteira (COMPLETE/INCOMPLETE/UNKNOWN).

Histórico existente vira UNKNOWN (server default): não dá para afirmar
retroativamente que posições sem preço foram tratadas como zero, então nenhum
dado antigo é inventado nem recalculado. Posições/total passam a aceitar null
(snapshot incompleto); caixa continua sempre conhecido.
"""

import sqlalchemy as sa

from alembic import op

revision = "0017_snapshot_status"
down_revision = "0016_price_override"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("portfolio_snapshots", sa.Column("status", sa.String(12), nullable=False, server_default="UNKNOWN"))
    op.add_column("portfolio_snapshots", sa.Column("unpriced", sa.JSON(), nullable=False, server_default="[]"))
    op.create_check_constraint("ck_snap_status", "portfolio_snapshots", "status IN ('COMPLETE','INCOMPLETE','UNKNOWN')")
    op.alter_column("portfolio_snapshots", "positions_value", existing_type=sa.Numeric(14, 2), nullable=True)
    op.alter_column("portfolio_snapshots", "total", existing_type=sa.Numeric(14, 2), nullable=True)


def downgrade() -> None:
    raise RuntimeError(
        "0017 é irreversível: snapshots INCOMPLETE possuem positions_value/total nulos, "
        "que não podem voltar a NOT NULL sem inventar zeros"
    )
