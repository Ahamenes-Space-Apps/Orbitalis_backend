"""SQLite connection, WAL pragmas, migrations and write_tx.

Purpose: Single entry point for the disposable ORBITALIS database.
Inputs: A filesystem path (``":memory:"`` allowed for tests).
Outputs: ``Database`` with ``connect()``, ``write_tx()`` and ``close()``.
Called by: ``main.py`` at startup, repositories for reads, every writer via
``write_tx`` (SDD §7.5 — the one sanctioned write path).
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib import resources
from pathlib import Path

import aiosqlite

_MIGRATIONS_PACKAGE = "orbitalis.store.migrations"
_PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA foreign_keys=ON",
    "PRAGMA busy_timeout=5000",
)
_MIGRATION_RE = re.compile(r"^(\d+)_.*\.sql$")


def _migration_files() -> list[tuple[int, str]]:
    """Return ``(version, sql_text)`` pairs sorted by version."""
    files: list[tuple[int, str]] = []
    for entry in resources.files(_MIGRATIONS_PACKAGE).iterdir():
        match = _MIGRATION_RE.match(entry.name)
        if match:
            files.append((int(match.group(1)), entry.read_text(encoding="utf-8")))
    return sorted(files)


class Database:
    """Async SQLite handle with WAL, forward-only migrations, one writer."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._write_conn: aiosqlite.Connection | None = None
        self._write_lock = asyncio.Lock()

    async def connect(self) -> None:
        """Open the single writer connection, apply pragmas and migrations."""
        conn = await aiosqlite.connect(self.path)
        for pragma in _PRAGMAS:
            await conn.execute(pragma)
        await self._migrate(conn)
        await conn.commit()
        self._write_conn = conn

    async def _migrate(self, conn: aiosqlite.Connection) -> None:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
        )
        cur = await conn.execute("SELECT version FROM schema_migrations")
        applied = {row[0] for row in await cur.fetchall()}
        for version, sql in _migration_files():
            if version in applied:
                continue
            await conn.executescript(sql)
            await conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))

    @asynccontextmanager
    async def write_tx(self) -> AsyncIterator[aiosqlite.Connection]:
        """The one sanctioned write path: serialized transaction (SDD §7.5)."""
        if self._write_conn is None:
            raise RuntimeError("Database.connect() must be called before write_tx()")
        async with self._write_lock:
            try:
                await self._write_conn.execute("BEGIN IMMEDIATE")
                yield self._write_conn
                await self._write_conn.commit()
            except BaseException:
                await self._write_conn.rollback()
                raise

    async def read(self) -> aiosqlite.Connection:
        """Open a short-lived read connection with the same pragmas."""
        conn = await aiosqlite.connect(self.path)
        for pragma in _PRAGMAS:
            await conn.execute(pragma)
        return conn

    async def close(self) -> None:
        if self._write_conn is not None:
            await self._write_conn.close()
            self._write_conn = None


async def open_database(path: str | Path) -> Database:
    """Connect and migrate; the normal startup entry point."""
    db = Database(path)
    await db.connect()
    return db
