import pytest
from sqlalchemy import func, select

from app.models import DatasetRow
from test_dataset_filter_groups import group, rule
from test_dataset_rows import call, insert, rows  # noqa: F401
from test_datasets import auth, client, error  # noqa: F401
from test_identity_migration import db  # noqa: F401


@pytest.mark.parametrize("operation,expected", [
    ("count", 2), ("empty_count", 1), ("empty_percent", 100.0 / 3),
    ("unique_count", 2), ("sum", 12), ("avg", 6), ("min", 2), ("max", 10),
])
def test_column_summary_uses_filtered_rows_and_sql(client, db, rows, operation, expected):
    insert(client, rows, ticket="A", score=2, title="")
    insert(client, rows, ticket="B", score=10, title="A")
    insert(client, rows, ticket="C", title=None)
    insert(client, rows, ticket="D", score=50, title="ignored")
    tree = group("and", rule("ticket", "not_in", ["D"]),
                 group("or", rule("score", "lt", 20), rule("score", "is_null", None)))
    summary = call(client, "POST", f"{rows}/summary", uid="member", body={
        "filter_tree": tree, "summaries": {"score": operation, "title": "empty_count"},
    })
    assert summary["total"] == 3
    assert summary["values"] == {"score": pytest.approx(expected), "title": 1}
    assert summary["schema_revision"] == 1

    dataset_id = rows.split("/")[-2]
    score = DatasetRow.values["score"].as_float()
    ticket = DatasetRow.values["ticket"].as_string()
    total = func.count()
    count = func.count(score)
    metric = {
        "count": count, "empty_count": total - count, "empty_percent": 100.0 * (total - count) / total,
        "unique_count": func.count(score.distinct()), "sum": func.sum(score),
        "avg": func.avg(score), "min": func.min(score), "max": func.max(score),
    }[operation]
    with db.session() as session:
        expected_sql = session.scalar(select(metric).where(DatasetRow.dataset_id == dataset_id, ticket != "D"))
    assert summary["values"]["score"] == pytest.approx(float(expected_sql))


def test_empty_and_invalid_summaries(client, rows):
    url = f"{rows}/summary"
    insert(client, rows, ticket="A", title="Word", when="2025-02-01T03:00:00Z")
    insert(client, rows, ticket="B", title="word", when="2025-01-01T03:00:00Z")
    summary = call(client, "POST", url, body={"search": "WORD", "summaries": {"title": "unique_count", "when": "min"}})
    assert summary["values"] == {"title": 2, "when": "2025-01-01T03:00:00.000Z"}
    summary = call(client, "POST", url, body={"search": "missing", "summaries": {"score": "sum", "title": "empty_percent"}})
    assert summary["total"] == 0
    assert summary["values"] == {"score": None, "title": None}
    error(client.post(url, headers=auth("other"), json={"summaries": {"score": "sum"}}), 404, "DATASET_NOT_FOUND")
    error(client.post(url, headers=auth("member"), json={"summaries": {"title": "sum"}}), 400, "DATASET_SUMMARY_INVALID")


def test_summary_query_budget_on_ten_thousand_rows(client, db, rows):
    from time import perf_counter
    from sqlalchemy import insert as insert_rows

    dataset_id = rows.split("/")[-2]
    with db.session() as session:
        session.execute(insert_rows(DatasetRow), [
            {"dataset_id": dataset_id, "id": f"perf-{n}", "values": {"score": n % 100, "title": "queue"},
             "revision": 1, "created": 0, "updated": 0}
            for n in range(10_000)
        ])
        session.commit()
    tree = group("and", rule("title", "contains", "QUEUE"),
                 group("or", rule("score", "gte", 90), rule("score", "lt", 10)))
    start = perf_counter()
    summary = call(client, "POST", f"{rows}/summary", body={
        "filter_tree": tree, "summaries": {"score": "avg", "title": "unique_count"},
    })
    elapsed = perf_counter() - start
    print(f"Dataset summary, {db.engine.dialect.name}, 10000 rows: {elapsed:.3f}s")
    assert summary["total"] == 2000
    assert summary["values"] == {"score": pytest.approx(49.5), "title": 1}
