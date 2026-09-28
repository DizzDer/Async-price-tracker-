from alembic import op
import sqlalchemy as sa
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("products", sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("name",sa.String(200),nullable=False), sa.Column("url",sa.String(2048),nullable=False,unique=True),
        sa.Column("selector",sa.String(200),nullable=False), sa.Column("currency",sa.String(3),nullable=False),
        sa.Column("target",sa.Integer(),nullable=False), sa.Column("below",sa.Boolean(),nullable=False),
        sa.Column("active",sa.Boolean(),nullable=False), sa.Column("error",sa.Text(),nullable=True))
    op.create_table("price_points", sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("product_id",sa.Integer(),sa.ForeignKey("products.id"),nullable=False),
        sa.Column("amount",sa.Integer(),nullable=False), sa.Column("observed_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_price_points_product_id","price_points",["product_id"])
    op.create_table("alerts",sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("product_id",sa.Integer(),sa.ForeignKey("products.id"),nullable=False),
        sa.Column("point_id",sa.Integer(),sa.ForeignKey("price_points.id"),nullable=False,unique=True),
        sa.Column("message",sa.Text(),nullable=False), sa.Column("delivered",sa.Boolean(),nullable=False),
        sa.Column("delivery_error",sa.Text(),nullable=True))
    op.create_index("ix_alerts_product_id","alerts",["product_id"])

def downgrade():
    op.drop_table("alerts"); op.drop_table("price_points"); op.drop_table("products")
