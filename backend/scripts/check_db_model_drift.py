# -*- coding: utf-8 -*-
"""全库 ORM 模型 ↔ 物理库 漂移体检：列出所有 缺表 / 缺列。

用法（务必从 backend 目录或用 backend/.venv 的解释器运行）：

    .\\.venv\\Scripts\\python.exe scripts\\check_db_model_drift.py

背景：2026-09-20 用它抓到一起 P0 —— 11 张表缺 `provenance_metadata`(JSON)、
缺 `domestic_inquiries` 表，导致 `/api/v1/analytics/traffic` 长期 500。
根因是 ORM 模型加了列但没有配套迁移，而 ORM 查询是一次性 SELECT 全列，
任意一处缺列都会让整条查询炸掉。**建议每次改 models/ 后跑一次。**

注意：必须在 os.chdir 到 backend 之后再 import app，
否则 pydantic-settings 找不到 .env 会静默回退到 SQLite（体检结果也就不可信）。
"""
import os
import sys

# 向上找到含 `app` 包的那一层（backend 根），使脚本放在任意子目录都能跑
_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = _HERE
while _BACKEND and not os.path.isdir(os.path.join(_BACKEND, "app")):
    _parent = os.path.dirname(_BACKEND)
    if _parent == _BACKEND:
        break
    _BACKEND = _parent

os.chdir(_BACKEND)
sys.path.insert(0, _BACKEND)

from sqlalchemy import inspect  # noqa: E402

import app.models  # noqa: F401,E402  # 触发所有模型注册
from app.core.database import Base  # noqa: E402
from app.db.session import engine  # noqa: E402

insp = inspect(engine)
db_tables = set(insp.get_table_names())

missing_tables = []
missing_cols = {}

for tbl in Base.metadata.sorted_tables:
    name = tbl.name
    if name not in db_tables:
        missing_tables.append(name)
        continue
    actual = {c["name"] for c in insp.get_columns(name)}
    declared = {c.name for c in tbl.columns}
    gap = sorted(declared - actual)
    if gap:
        type_map = {}
        for c in gap:
            type_map[c] = str(tbl.columns[c].type)
        missing_cols[name] = type_map

print("=" * 78)
print("A. 缺失的表：", len(missing_tables))
print("=" * 78)
for t in missing_tables:
    print("  -", t)

print()
print("=" * 78)
print("B. 缺失的列：", sum(len(v) for v in missing_cols.values()), "列 /", len(missing_cols), "表")
print("=" * 78)
for t, cols in sorted(missing_cols.items()):
    print(f"  [{t}]")
    for c, ty in cols.items():
        print(f"      - {c}  ({ty})")

print()
print("=" * 78)
print("C. Alembic 版本状态")
print("=" * 78)
try:
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.runtime.migration import MigrationContext

    cfg = Config(os.path.join(_BACKEND, "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    print("heads  :", heads)
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        cur = ctx.get_current_heads()
        print("current:", cur)
except Exception as e:
    print("alembic check failed:", type(e).__name__, e)
