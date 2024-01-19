import asyncio
import os
import sys
import traceback
from asyncio import AbstractEventLoop
from typing import Any

import structlog
from prometheus_client import Gauge

METRIC_LABELS = ["pid"]

__all__ = ["monitor_server_resources"]

log = structlog.stdlib.get_logger("server_resources")

AI_GATEWAY_THREADS_COUNT = Gauge(
    "ai_gateway_threads_count",
    "The number of active threads in the server",
    METRIC_LABELS,
)

AI_GATEWAY_TASKS_COUNT = Gauge(
    "ai_gateway_tasks_count",
    "The number of asyncio tasks in the server",
    METRIC_LABELS,
)


async def monitor_server_resources(loop: AbstractEventLoop, interval: int):
    """
    Monitor the server resources.

    This task runs in the main event loop, meaning the web server will stop responding during the execution.
    Keep it light-weight, or consider running them in a separate thread in daemon mode.

    args:
        loop: The main event loop where the server is running.
        interval: Frequency of the server resource scanning.
    """
    while loop.is_running():
        await asyncio.sleep(interval)

        pid = os.getpid()

        threads_count, thread_backtraces = _get_threads_details()
        tasks_count, tasks_details = _get_tasks_details(loop)

        AI_GATEWAY_THREADS_COUNT.labels(pid=pid).set(threads_count)
        AI_GATEWAY_TASKS_COUNT.labels(pid=pid).set(tasks_count)

        log.info(
            "Server resources",
            pid=pid,
            threads_count=threads_count,
            threads_stacktrace=thread_backtraces,
            tasks_count=tasks_count,
            tasks_details=tasks_details,
        )

def _get_threads_details():
    backtraces = []
    for thread_id, stack in sys._current_frames().items():
        thread_info: dict[str, Any] = {"thread_id": thread_id}
        lines: list[dict] = []

        for filename, lineno, name, line in traceback.extract_stack(stack):
            line_info = {"filename": filename, "lineno": lineno, "name": name}
            if line:
                line_info["line"] = line.strip()
            lines.append(line_info)

        thread_info["lines"] = lines
        backtraces.append(thread_info)

    threads_count = len(backtraces)

    return (threads_count, backtraces)

def _get_tasks_details(loop: AbstractEventLoop):
    tasks_details: dict[str, Any] = {}
    tasks_count = 0

    for task in asyncio.all_tasks(loop):
        tasks_count += 1

        stack = task.get_stack(limit=1)[0]
        summary = traceback.extract_stack(stack)
        
        key = f"{summary[0].filename}-{summary[0].lineno}-{summary[0].name}"
        if summary[0].line:
            key += f"-{summary[0].line}"

        if key in tasks_details:
            tasks_details[key]["count"] += 1
            continue

        tasks_details[key] = {}
        tasks_details[key]["first_frame"] = key
        tasks_details[key]["count"] = 1
        tasks_details[key]["sampled_full_stack"] = task.get_stack()

    flattened_list = []
    for _, details in tasks_details.items():
        flattened_list.append(details)

    return (tasks_count, flattened_list)
