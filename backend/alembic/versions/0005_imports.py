"""0005 imports + import_items + transactions.import_id (Épico 3)."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0005_imports"
down_revision = "0004_transactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "imports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(20), server_default="OFX", nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="RECEIVED", nullable=False),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("imported_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duplicate_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('RECEIVED','PROCESSING','VALIDATED','IMPORTED','FAILED')", name="ck_imports_status"
        ),
    )
    op.create_index("ix_imports_user", "imports", ["user_id"])
    op.create_table(
        "import_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("import_id", sa.BigInteger(), nullable=False),
        sa.Column("row_no", sa.Integer(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("verdict", sa.String(20), server_default="NEW", nullable=False),
        sa.Column("matched_transaction_id", sa.BigInteger(), nullable=True),
        sa.Column("decision", sa.String(20), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["import_id"], ["imports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["matched_transaction_id"], ["transactions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("verdict IN ('NEW','EXACT_DUPLICATE','FUZZY_CANDIDATE','INVALID')", name="ck_items_verdict"),
        sa.CheckConstraint("decision IN ('KEEP_BOTH','DISCARD_IMPORTED','MERGED')", name="ck_items_decision"),
    )
    op.create_index("ix_items_import", "import_items", ["import_id"])
    op.add_column("transactions", sa.Column("import_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_tx_import", "transactions", "imports", ["import_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_tx_import", "transactions", type_="foreignkey")
    op.drop_column("transactions", "import_id")
    op.drop_index("ix_items_import", table_name="import_items")
    op.drop_table("import_items")
    op.drop_index("ix_imports_user", table_name="imports")
    op.drop_table("imports")
