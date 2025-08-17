import asyncio
from typing import Dict

# Simple in-memory queues per agent and per run (PoC only)
_agent_queues: Dict[str, asyncio.Queue[str]] = {}
_run_queues: Dict[str, asyncio.Queue[str]] = {}


def queue_for_agent(agent_id: str) -> asyncio.Queue[str]:
    if agent_id not in _agent_queues:
        _agent_queues[agent_id] = asyncio.Queue(maxsize=1000)
    return _agent_queues[agent_id]


def queue_for_run(run_id: str) -> asyncio.Queue[str]:
    if run_id not in _run_queues:
        _run_queues[run_id] = asyncio.Queue(maxsize=1000)
    return _run_queues[run_id]
