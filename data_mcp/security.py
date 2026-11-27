"""Read-only SQL guard: allow only SELECT/WITH, block writes, force LIMIT, time out."""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Any, Callable

DEFAULT_LIMIT = 1000
DEFAULT_TIMEOUT_SEC = 10

_COMMENT_LINE = re.compile(r"--.*?$", re.MULTILINE)
_COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)
_FORBIDDEN = re.compile(
    r"\b("
    r"DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE|ATTACH|DETACH|"
    r"COPY|PRAGMA|INSTALL|LOAD|EXPORT|IMPORT|GRANT|REVOKE|VACUUM|"
    r"CALL|MERGE|REPLACE|UPSERT|EXEC|EXECUTE|INTO"
    r")\b",
    re.IGNORECASE,
)
_LEADING_KEYWORD = re.compile(r"^\(*\s*([A-Za-z]+)")
_TRAILING_LIMIT = re.compile(r"\bLIMIT\s+(\d+)\s*(OFFSET\s+\d+)?\s*$", re.IGNORECASE)


class SqlGuardError(ValueError):
    """Raised when a statement is rejected or times out."""


def normalize_sql(sql: str) -> str:
    cleaned = _COMMENT_BLOCK.sub(" ", sql)
    cleaned = _COMMENT_LINE.sub(" ", cleaned)
    cleaned = cleaned.strip().rstrip(";").strip()
    if not cleaned:
        raise SqlGuardError("SQL 不能为空")
    return cleaned


def assert_readonly_select(sql: str) -> str:
    cleaned = normalize_sql(sql)
    if _FORBIDDEN.search(cleaned):
        raise SqlGuardError("只允许只读查询，已禁止 DROP/DELETE/UPDATE 等写操作或危险语句")
    match = _LEADING_KEYWORD.match(cleaned)
    keyword = match.group(1).upper() if match else ""
    if keyword not in {"SELECT", "WITH"}:
        raise SqlGuardError("只允许 SELECT 或 WITH 查询")
    return cleaned


def ensure_limit(sql: str, default_limit: int = DEFAULT_LIMIT) -> str:
    match = _TRAILING_LIMIT.search(sql)
    if match:
        limit = min(int(match.group(1)), default_limit)
        offset = match.group(2) or ""
        suffix = f" {offset.strip()}" if offset else ""
        return sql[: match.start()] + f"LIMIT {limit}" + suffix
    return f"{sql} LIMIT {default_limit}"


def run_with_timeout(
    func: Callable[..., Any],
    *args: Any,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    **kwargs: Any,
) -> Any:
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout_sec)
        except FuturesTimeout as exc:
            future.cancel()
            raise SqlGuardError(f"查询超时（超过 {timeout_sec} 秒）") from exc
