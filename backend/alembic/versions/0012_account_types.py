"""0012 tipos de conta: remove CREDIT_CARD (converte para OTHER), adiciona INVESTMENT."""

from alembic import op

revision = "0012_account_types"
down_revision = "0011_prices"
branch_labels = None
depends_on = None

OLD_TYPES = "('CHECKING','SAVINGS','CREDIT_CARD','CASH','OTHER')"
NEW_TYPES = "('CHECKING','SAVINGS','CASH','INVESTMENT','OTHER')"


def upgrade() -> None:
    op.execute("UPDATE accounts SET account_type = 'OTHER' WHERE account_type = 'CREDIT_CARD'")
    op.drop_constraint("ck_accounts_type", "accounts", type_="check")
    op.create_check_constraint("ck_accounts_type", "accounts", f"account_type IN {NEW_TYPES}")


def downgrade() -> None:
    # Sem reversão de dados: linhas convertidas para OTHER permanecem OTHER.
    op.drop_constraint("ck_accounts_type", "accounts", type_="check")
    op.create_check_constraint("ck_accounts_type", "accounts", f"account_type IN {OLD_TYPES}")
