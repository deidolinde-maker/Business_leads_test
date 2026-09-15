import time
from contextlib import contextmanager

from business.errors import BusinessCheckError


class Deadline:
    def __init__(self, seconds: float = 75):
        self.started = time.monotonic()
        self.ends = self.started + seconds
        self.timings: dict[str, float] = {}

    def ms(self, maximum: int = 15000) -> int:
        remaining = int((self.ends - time.monotonic()) * 1000)
        if remaining <= 0:
            raise BusinessCheckError("case_deadline_exceeded")
        return max(1, min(remaining, maximum))

    @contextmanager
    def phase(self, name: str):
        self.ms()
        started = time.monotonic()
        try:
            yield
            self.ms()
        finally:
            self.timings[name] = round(time.monotonic() - started, 3)
