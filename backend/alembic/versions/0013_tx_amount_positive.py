"""0013 regra de sinal: normaliza legados negativos e aperta o CHECK para amount > 0."""

from alembic import op

revision = "0013_tx_amount_positive"
down_revision = "0012_account_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Convenção antiga permitia EXPENSE negativo (ex.: -250.50); o tipo é autoritativo.
    op.execute("UPDATE transactions SET amount = abs(amount) WHERE amount < 0")
    op.drop_constraint("ck_tx_amount", "transactions", type_="check")
    op.create_check_constraint("ck_tx_amount", "transactions", "amount > 0")


def downgrade() -> None:
    # Sem reversão de dados: valores normalizados permanecem positivos.
    op.drop_constraint("ck_tx_amount", "transactions", type_="check")
    op.create_check_constraint("ck_tx_amount", "transactions", "amount <> 0")
