"""Execution timeline: the event-driven activity log of the agent.

The AgentExecutionLogger is a small publisher-subscriber bus. Every component
that does work (planner, executor, tools, providers, extractors, exporter)
reports what it is about to do, what it did, and what went wrong through this
logger. Subscribers render the stream: the terminal shows the human-readable
timeline, the desktop GUI re-renders the same events. No subscriber ever
touches the agent's internal chain-of-thought.
"""
