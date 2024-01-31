import logging
import signal
import traceback
from typing import FrameType


def _logging_hundler(signal: int, frame: FrameType) -> None:
    log = logging.getLogger("uvicorn.error")
    log.error(
        "Server received a signale",
        {
            "signal": signal,
            "frame": frame,
            "stack": traceback.format_stack(frame),
        },
    )


def register_signal_handlers() -> None:
    signal.signal(signal.SIGINT, _logging_hundler)
    signal.signal(signal.SIGQUIT, _logging_hundler)
    signal.signal(signal.SIGFPE, _logging_hundler)
    signal.signal(signal.SIGKILL, _logging_hundler)
    signal.signal(signal.SIGTERM, _logging_hundler)
