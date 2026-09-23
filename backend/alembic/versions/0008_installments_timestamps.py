"""0008 timestamps em installments (drift: model tinha, migration não)."""

from alembic import op

revision = "0008_installments_timestamps"
down_revision = "0007_installments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE installments ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now()")
    op.execute("ALTER TABLE installments ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now()")
    op.execute("ALTER TABLE installments ALTER COLUMN created_at SET NOT NULL")
    op.execute("ALTER TABLE installments ALTER COLUMN updated_at SET NOT NULL")
    op.execute("ALTER TABLE installments ALTER COLUMN created_at SET DEFAULT now()")
    op.execute("ALTER TABLE installments ALTER COLUMN updated_at SET DEFAULT now()")


def downgrade() -> None:
    op.drop_column("installments", "updated_at")
    op.drop_column("installments", "created_at")
