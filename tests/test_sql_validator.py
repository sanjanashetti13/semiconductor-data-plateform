"""SQL safety validator — SELECT-only enforcement."""

from __future__ import annotations

import pytest

from ai.sql_agent.validator import UnsafeSqlError, validate_select_only


def test_allows_simple_select():
    assert validate_select_only("SELECT 1") == "SELECT 1"


def test_allows_cte():
    sql = "WITH x AS (SELECT 1 AS n) SELECT n FROM x"
    assert validate_select_only(sql) == sql


def test_rejects_empty():
    with pytest.raises(UnsafeSqlError):
        validate_select_only("   ")


def test_rejects_multi_statement():
    with pytest.raises(UnsafeSqlError):
        validate_select_only("SELECT 1; DROP TABLE t")


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE dbo.t",
        "DELETE FROM dbo.t",
        "UPDATE dbo.t SET a=1",
        "INSERT INTO dbo.t VALUES (1)",
        "ALTER TABLE dbo.t ADD c INT",
        "CREATE TABLE dbo.t (id INT)",
        "TRUNCATE TABLE dbo.t",
        "EXEC sp_who",
        "EXECUTE sp_who",
        "MERGE INTO dbo.t USING dbo.s ON 1=1 WHEN MATCHED THEN UPDATE SET a=1;",
        "SELECT * INTO dbo.copy FROM dbo.t",
        "BACKUP DATABASE x TO DISK='x.bak'",
        "WAITFOR DELAY '00:00:05'",
    ],
)
def test_rejects_dangerous_statements(sql: str):
    with pytest.raises(UnsafeSqlError):
        validate_select_only(sql)


def test_strips_comments_but_keeps_select():
    sql = "SELECT 1 -- comment\n"
    assert validate_select_only(sql) == "SELECT 1"
