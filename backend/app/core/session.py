import asyncio
import json
from typing import Dict, AsyncGenerator

# In-memory SSE queues keyed by session_id
_queues: Dict[str, asyncio.Queue] = {}


def create_session(session_id: str) -> None:
    _queues[session_id] = asyncio.Queue()


async def emit(session_id: str, event: dict) -> None:
    q = _queues.get(session_id)
    if q:
        await q.put(event)


async def close_session(session_id: str) -> None:
    """Put sentinel — stream_events drains and removes the queue."""
    q = _queues.get(session_id)
    if q:
        await q.put(None)


async def stream_events(session_id: str) -> AsyncGenerator[str, None]:
    # Wait up to 10s for the session to be created (handles the race where
    # the client connects before the background task has called create_session)
    for _ in range(100):
        if session_id in _queues:
            break
        await asyncio.sleep(0.1)

    q = _queues.get(session_id)
    if not q:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Session not found or expired'})}\n\n"
        return

    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=300.0)
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Planning timed out after 5 minutes'})}\n\n"
                break
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"
    finally:
        _queues.pop(session_id, None)
