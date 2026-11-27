"""data-mcp: read-only tools over SQLite + Excel."""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `python data_mcp/server.py` from the project root.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP

from data_mcp.datasources import describe_table as describe_table_impl
from data_mcp.datasources import fetch_rows
from data_mcp.datasources import list_tables as list_tables_impl
from data_mcp.datasources import normalize_table
from data_mcp.security import (
    DEFAULT_LIMIT,
    DEFAULT_TIMEOUT_SEC,
    assert_readonly_select,
    ensure_limit,
    run_with_timeout,
)

mcp = FastMCP(
    "data-mcp",
    instructions=(
        "只读数据查询工具。可用表: sales（SQLite 销售明细）、products（Excel 商品成本）。"
        "run_sql 只接受 SELECT/WITH，自动追加 LIMIT，并在 10 秒后超时。"
    ),
)


@mcp.tool()
def list_tables() -> list[dict[str, str]]:
    """列出可查询的数据表及其来源。"""
    return list_tables_impl()


@mcp.tool()
def describe_table(table: str) -> list[dict[str, str]]:
    """查看指定表的字段名、类型和是否可空。"""
    return describe_table_impl(table)


@mcp.tool()
def run_sql(sql: str) -> list[dict]:
    """执行只读 SQL，返回结果行。禁止写操作，自动限制返回行数，超时 10 秒。"""
    cleaned = assert_readonly_select(sql)
    limited = ensure_limit(cleaned, DEFAULT_LIMIT)
    return run_with_timeout(fetch_rows, limited, timeout_sec=DEFAULT_TIMEOUT_SEC)


@mcp.tool()
def sample_rows(table: str, n: int = 5) -> list[dict]:
    """返回指定表的前 N 行样例数据，N 最大为 100。"""
    name = normalize_table(table)
    limit = max(1, min(int(n), 100))
    sql = ensure_limit(f"SELECT * FROM {name}", default_limit=limit)
    return run_with_timeout(fetch_rows, sql, timeout_sec=DEFAULT_TIMEOUT_SEC)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
