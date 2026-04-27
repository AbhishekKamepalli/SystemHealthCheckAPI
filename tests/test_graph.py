from app.exceptions import ValidationError400
from app.graph import bfs_traversal, build_graph
from app.models import ComponentInput


def make_components(*names: str) -> list[ComponentInput]:
    return [ComponentInput(name=name, health_check_url=f"http://{name}/health") for name in names]


def test_bfs_traversal_order_is_root_to_dependency():
    graph = build_graph(
        make_components("frontend", "api-service", "database"),
        [("frontend", "api-service"), ("api-service", "database")],
    )

    assert bfs_traversal(graph) == ["frontend", "api-service", "database"]


def test_invalid_dependency_reference_raises_clear_error():
    try:
        build_graph(make_components("frontend"), [("frontend", "missing-service")])
    except ValidationError400 as exc:
        assert str(exc) == "Invalid dependency reference: frontend -> missing-service."
    else:
        raise AssertionError("Expected ValidationError400 to be raised.")


def test_cycle_detection_rejects_cyclic_graph():
    try:
        build_graph(
            make_components("frontend", "api-service"),
            [("frontend", "api-service"), ("api-service", "frontend")],
        )
    except ValidationError400 as exc:
        assert "Cycle detected" in str(exc)
    else:
        raise AssertionError("Expected ValidationError400 to be raised.")
