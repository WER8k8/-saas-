"""119 — 补齐 provenance_metadata 漂移列 + 创建 domestic_inquiries 表

背景（2026-09-20 实测根因）：
- `GET /api/v1/analytics/traffic` 与 `GET /api/v1/analytics/` 长期返回 500。
  进程内复现（TestClient，os.chdir 到 backend 以命中 .env）得到真实栈：
    sqlalchemy.exc.ProgrammingError
      psycopg2.errors.UndefinedColumn:
        column inquiries.provenance_metadata does not exist
    调用链：
      app/api/v1/routes/analytics.py:337  get_traffic_data
      -> services/traffic_analytics_service.py:599  build_platform_board
      -> :514 build_board -> :310 _load_board_inquiries（ORM 全列 SELECT）
- 根因不是路由逻辑，而是 **ORM 模型与物理库漂移**：多个模型声明了
  `provenance_metadata = Column(JSON)`，但从未有迁移把它落到 PG。
  由于 ORM 查询是一次性 SELECT 全列，任意一处缺列即整条查询炸掉。
- 全库体检（脚本 backend/_drift_check.py）结果：
    · 缺列 11 处（11 张表各缺 1 列，全部为 provenance_metadata JSON）
    · 缺表 1 张（domestic_inquiries，模型在 app/models/domestic.py）
    · alembic heads == current == 118_add_company_rfm_tags（版本号本身无漂移）

本迁移：
1. 幂等地为 11 张表补 provenance_metadata(JSON, nullable)。
2. 幂等地创建 domestic_inquiries 表及其索引。
幂等设计原因：该库历史上存在 bootstrap 脚本直接建表的情况，
    纯 add_column 在生产重放可能撞 AlreadyExists。

依赖：down_revision = 118_add_company_rfm_tags
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "119_align_provenance_metadata_domestic_inquiries"
down_revision: Union[str, None] = "118_add_company_rfm_tags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 体检确认缺 provenance_metadata 列的 11 张表
_TARGET_TABLES = (
    "contact_events",
    "experience_records",
    "inquiries",
    "invoices",
    "knowledge_bases",
    "logistics_shipments",
    "payments",
    "pipelines",
    "prospect_leads",
    "purchase_orders",
    "whatsapp_messages",
)


def _add_json_column_if_missing(table: str) -> None:
    """表存在且尚未有该列时补列；已存在则跳过（幂等）。"""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns(table)}
    if "provenance_metadata" in existing:
        return
    op.add_column(
        table,
        sa.Column("provenance_metadata", sa.JSON(), nullable=True),
    )


def upgrade() -> None:
    for t in _TARGET_TABLES:
        _add_json_column_if_missing(t)

    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "domestic_inquiries" in insp.get_table_names():
        return

    op.create_table(
        "domestic_inquiries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("buyer_name", sa.String(200), nullable=False),
        sa.Column("buyer_type", sa.String(50), nullable=False, server_default="engineering"),
        sa.Column("contact_name", sa.String(100), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("contact_wechat", sa.String(100), nullable=True),
        sa.Column("external_userid", sa.String(100), nullable=True),
        sa.Column("product_category", sa.String(100), nullable=True, server_default="瓷砖"),
        sa.Column("quantity_m2", sa.Float(), nullable=False, server_default="0"),
        sa.Column("project_name", sa.String(300), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("source_channel", sa.String(50), nullable=True, server_default="wechat"),
        sa.Column("stage", sa.String(50), nullable=False, server_default="inquiry"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="CNY"),
        sa.Column("vat_type", sa.String(20), nullable=False, server_default="general"),
        sa.Column("vat_rate", sa.Float(), nullable=False, server_default="0.13"),
        sa.Column("logistics_type", sa.String(50), nullable=True, server_default="domestic_freight"),
        sa.Column("quote_amount_rmb", sa.Float(), nullable=True, server_default="0"),
        sa.Column("won_amount_rmb", sa.Float(), nullable=True, server_default="0"),
        sa.Column("lost_reason", sa.String(500), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("utm_source", sa.String(200), nullable=True),
        sa.Column("utm_medium", sa.String(120), nullable=True),
        sa.Column("utm_campaign", sa.String(200), nullable=True),
        sa.Column("provenance_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_domestic_inquiries_tenant_id", "domestic_inquiries", ["tenant_id"])
    op.create_index("ix_domestic_inquiries_buyer_type", "domestic_inquiries", ["buyer_type"])
    op.create_index("ix_domestic_inquiries_contact_phone", "domestic_inquiries", ["contact_phone"])
    op.create_index("ix_domestic_inquiries_external_userid", "domestic_inquiries", ["external_userid"])
    op.create_index("ix_domestic_inquiries_city", "domestic_inquiries", ["city"])
    op.create_index("ix_domestic_inquiries_stage", "domestic_inquiries", ["stage"])
    op.create_index("ix_domestic_inquiries_utm_source", "domestic_inquiries", ["utm_source"])
    op.create_index("ix_domestic_inquiries_deleted_at", "domestic_inquiries", ["deleted_at"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "domestic_inquiries" in insp.get_table_names():
        for ix in (
            "ix_domestic_inquiries_deleted_at",
            "ix_domestic_inquiries_utm_source",
            "ix_domestic_inquiries_stage",
            "ix_domestic_inquiries_city",
            "ix_domestic_inquiries_external_userid",
            "ix_domestic_inquiries_contact_phone",
            "ix_domestic_inquiries_buyer_type",
            "ix_domestic_inquiries_tenant_id",
        ):
            try:
                op.drop_index(ix, table_name="domestic_inquiries")
            except Exception:
                pass
        op.drop_table("domestic_inquiries")

    for t in _TARGET_TABLES:
        if t not in insp.get_table_names():
            continue
        existing = {c["name"] for c in insp.get_columns(t)}
        if "provenance_metadata" in existing:
            op.drop_column(t, "provenance_metadata")
