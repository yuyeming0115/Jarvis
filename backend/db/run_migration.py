#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.store import DB_PATH, connect, init_db  # noqa: E402


def _print_table_info(table_name: str) -> None:
    with connect() as conn:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    print(f"\n{table_name} 表字段（共 {len(rows)} 个）:")
    for row in rows:
        print(f"  - {row['name']} ({row['type']})")


def main() -> None:
    print(f"数据库路径: {DB_PATH}")
    init_db()
    print("\n[成功] 数据库结构已更新到当前版本。")
    _print_table_info("drafts")
    _print_table_info("prompt_versions")
    _print_table_info("content_reviews")
    _print_table_info("settings")


if __name__ == "__main__":
    main()
