import pytest
from sqlalchemy import text


@pytest.mark.db
def test_ref01_commits_are_confined_to_a_disposable_schema(postgres_sandbox, db_sessions):
    first, second = db_sessions
    assert first is not second
    first.execute(text("CREATE TABLE ref01_probe (value INTEGER NOT NULL)"))
    first.execute(text("INSERT INTO ref01_probe (value) VALUES (7)"))
    first.commit()
    assert second.execute(text("SELECT value FROM ref01_probe")).scalar_one() == 7
    assert first.execute(text("SELECT pg_backend_pid()")).scalar_one() != second.execute(
        text("SELECT pg_backend_pid()")
    ).scalar_one()
    assert second.execute(text("SELECT current_schema()")).scalar_one() == postgres_sandbox.schema


@pytest.mark.concurrency
def test_ref01_provides_two_independent_sessions(db_sessions):
    first, second = db_sessions
    first_pid = first.execute(text("SELECT pg_backend_pid()")).scalar_one()
    second_pid = second.execute(text("SELECT pg_backend_pid()")).scalar_one()
    assert first_pid != second_pid