import time
from contextlib import contextmanager

from business.errors import BusinessCheckError


class Deadline:
    def __init__(self, seconds: float = 75):
        self.started = time.monotonic()
        self.ends = self.started + seconds
        self.timings: dict[str, float] = {}
        self.current_phase = "setup"
        self.current_step = "setup"
        self.failed_phase = None
        self.failed_step = None

    def mark(self, step: str):
        self.current_step = step

    def ms(self, maximum: int = 15000) -> int:
        remaining = int((self.ends - time.monotonic()) * 1000)
        if remaining <= 0:
            raise BusinessCheckError("case_deadline_exceeded")
        return max(1, min(remaining, maximum))

    @contextmanager
    def phase(self, name: str):
        self.ms()
        started = time.monotonic()
        self.current_phase = name
        self.current_step = name
        try:
            yield
            self.ms()
        except Exception:
            self.failed_phase = name
            self.failed_step = self.current_step
            raise
        finally:
            self.timings[name] = round(time.monotonic() - started, 3)
