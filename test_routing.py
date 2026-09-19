"""Focused routing checks for the shared skill and Needle 2 registry."""

import skills
import tools


def test_catalog_contains_needle2():
    needle = next(item for item in skills.catalog() if item["skill"] == "needle")
    assert "run_needle2_file_agent" in needle["tools"]


def test_route_logger_receives_tool_lifecycle():
    events = []
    tools.set_route_logger(lambda skill, name, phase, detail: events.append((skill, name, phase)))
    try:
        result = tools.execute_tool("get_current_time", {})
    finally:
        tools.set_route_logger(None)

    assert result
    assert events == [
        ("system", "get_current_time", "start"),
        ("system", "get_current_time", "done"),
    ]


def test_needle2_tool_is_callable():
    result = tools.execute_tool("run_needle2_file_agent", {"query": "list recent files"})
    assert isinstance(result, str)
    assert result.strip()


if __name__ == "__main__":
    test_catalog_contains_needle2()
    test_route_logger_receives_tool_lifecycle()
    test_needle2_tool_is_callable()
    print("Routing tests passed: skills, route lifecycle, Needle 2")
