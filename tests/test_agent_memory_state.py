"""Tests for agent memory and execution state."""

from app.agent.memory import AgentMemory
from app.agent.state import AgentState, AgentStep


def _step(tool: str) -> AgentStep:
    return AgentStep(tool=tool, description=f"Run {tool}", arguments={})


def test_state_walks_steps_in_order() -> None:
    state = AgentState(task="t", steps=[_step("a"), _step("b")])
    assert state.next_step().tool == "a"
    state.mark_current_done()
    assert state.next_step().tool == "b"
    state.mark_current_done()
    assert state.next_step() is None
    assert state.is_finished


def test_state_tracks_completed_and_remaining() -> None:
    state = AgentState(task="t", steps=[_step("a"), _step("b"), _step("c")])
    state.mark_current_done()
    assert state.completed_tools == ["a"]
    assert state.remaining_tools() == ["b", "c"]


def test_state_snapshot_is_json_safe() -> None:
    state = AgentState(task="t", steps=[_step("a")], payload={"leads": [1, 2]})
    snapshot = state.snapshot()
    assert snapshot["task"] == "t"
    assert snapshot["total_steps"] == 1
    assert snapshot["payload_keys"] == ["leads"]


def test_memory_records_transcript_and_tools() -> None:
    memory = AgentMemory()
    memory.begin("find dentists")
    memory.record_tool("google_maps_search", True, "collected 3 leads")
    assert memory.current_task == "find dentists"
    assert memory.completed_tools == ["google_maps_search"]
    assert memory.observations["google_maps_search"]["success"] is True
    assert any(entry["role"] == "user" for entry in memory.transcript)
    assert any(entry["role"] == "tool" for entry in memory.transcript)


def test_memory_begin_resets_previous_run() -> None:
    memory = AgentMemory()
    memory.begin("first task")
    memory.record_tool("a", True, "ok")
    memory.begin("second task")
    assert memory.completed_tools == []
    assert memory.current_task == "second task"


def test_memory_snapshot_is_json_safe() -> None:
    memory = AgentMemory()
    memory.begin("find dentists")
    memory.record_tool("google_maps_search", False, "failed")
    snapshot = memory.snapshot()
    assert snapshot["task"] == "find dentists"
    assert len(snapshot["transcript"]) == 2
    assert snapshot["observations"]["google_maps_search"]["success"] is False
