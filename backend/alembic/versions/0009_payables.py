"""0009 payables: une recurring_bills + installments em contas a pagar.

- Cria `payables` e migra as linhas (VARIABLE -> RECURRING).
- transactions ganha `payable_id` + source PAYABLE.
- Dropa `recurring_bills` e `installments`.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0009_payables"
down_revision = "0008_installments_timestamps"
branch_labels = None
depends_on = None

KINDS = "('FIXED','RECURRING','INSTALLMENT','ONE_TIME')"


def upgrade() -> None:
    op.create_table(
        "payables",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("periodicity", sa.String(10), nullable=True),
        sa.Column("due_day", sa.Integer(), nullable=True),
        sa.Column("next_due", sa.Date(), nullable=True),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("num_installments", sa.Integer(), nullable=True),
        sa.Column("installment_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("first_due_date", sa.Date(), nullable=True),
        sa.Column("paid_ns", JSONB(), server_default="[]", nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("account_id", sa.BigInteger(), nullable=True),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"kind IN {KINDS}", name="ck_pay_kind"),
        sa.CheckConstraint(
            "(kind IN ('FIXED','RECURRING') AND amount IS NOT NULL AND periodicity IS NOT NULL"
            " AND due_day IS NOT NULL AND next_due IS NOT NULL"
            " AND total_amount IS NULL AND num_installments IS NULL AND first_due_date IS NULL)"
            " OR (kind = 'INSTALLMENT' AND total_amount IS NOT NULL AND num_installments IS NOT NULL"
            " AND first_due_date IS NOT NULL AND installment_amount IS NOT NULL"
            " AND amount IS NULL AND periodicity IS NULL AND due_day IS NULL AND next_due IS NULL)"
            " OR (kind = 'ONE_TIME' AND amount IS NOT NULL AND next_due IS NOT NULL"
            " AND periodicity IS NULL AND due_day IS NULL"
            " AND total_amount IS NULL AND num_installments IS NULL AND first_due_date IS NULL)",
            name="ck_pay_shape",
        ),
        sa.CheckConstraint("due_day IS NULL OR due_day BETWEEN 1 AND 31", name="ck_pay_due_day"),
        sa.CheckConstraint("num_installments IS NULL OR num_installments BETWEEN 2 AND 60", name="ck_pay_num"),
    )
    op.create_index("ix_pay_user_next", "payables", ["user_id", "next_due"])

    # recurring_bills -> payables (VARIABLE vira RECURRING: mesmo comportamento)
    op.execute(
        """
        INSERT INTO payables
          (user_id, description, kind, amount, periodicity, due_day, next_due,
           paid_ns, created_at, updated_at)
        SELECT user_id, description,
               CASE WHEN kind = 'VARIABLE' THEN 'RECURRING' ELSE kind END,
               amount, periodicity, due_day, next_due,
               '[]'::jsonb, now(), now()
        FROM recurring_bills
        """
    )
    # installments -> payables
    op.execute(
        """
        INSERT INTO payables
          (user_id, description, kind, total_amount, num_installments,
           installment_amount, first_due_date, account_id, paid_ns, created_at, updated_at)
        SELECT user_id, description, 'INSTALLMENT', total_amount, num_installments,
               installment_amount, first_due_date, account_id, '[]'::jsonb, now(), now()
        FROM installments
        """
    )

    # transactions: rastro da baixa + source novo
    op.add_column("transactions", sa.Column("payable_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_tx_payable", "transactions", "payables", ["payable_id"], ["id"], ondelete="SET NULL")
    op.drop_constraint("ck_tx_source", "transactions", type_="check")
    op.create_check_constraint("ck_tx_source", "transactions", "source IN ('MANUAL','OFX','IMPORT','PAYABLE')")

    op.drop_table("installments")
    op.drop_table("recurring_bills")


def downgrade() -> None:
    op.create_table(
        "recurring_bills",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("periodicity", sa.String(10), nullable=True),
        sa.Column("due_day", sa.Integer(), nullable=True),
        sa.Column("next_due", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "installments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("num_installments", sa.Integer(), nullable=False),
        sa.Column("installment_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("first_due_date", sa.Date(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        INSERT INTO recurring_bills (user_id, description, kind, amount, periodicity, due_day, next_due)
        SELECT user_id, description, kind, amount, periodicity, due_day, next_due
        FROM payables WHERE kind IN ('FIXED','RECURRING','ONE_TIME')
        """
    )
    op.execute(
        """
        INSERT INTO installments
          (user_id, description, total_amount, num_installments, installment_amount, first_due_date, account_id)
        SELECT user_id, description, total_amount, num_installments,
               installment_amount, first_due_date, account_id
        FROM payables WHERE kind = 'INSTALLMENT'
        """
    )
    op.drop_constraint("fk_tx_payable", "transactions", type_="foreignkey")
    op.drop_column("transactions", "payable_id")
    op.drop_constraint("ck_tx_source", "transactions", type_="check")
    op.create_check_constraint("ck_tx_source", "transactions", "source IN ('MANUAL','OFX','IMPORT')")
    op.drop_index("ix_pay_user_next", table_name="payables")
    op.drop_table("payables")
