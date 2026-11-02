import time
import logging
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("aeroscout")

class StageTimer:
    def __init__(self):
        self.timings: Dict[str, float] = {}
        self._start_time = None
        self._current_stage = None

    def start_stage(self, stage_name: str):
        now = time.perf_counter()
        if self._current_stage and self._start_time:
            self.timings[self._current_stage] = round(now - self._start_time, 3)
            logger.info(f"Stage '{self._current_stage}' completed in {self.timings[self._current_stage]}s")
        self._current_stage = stage_name
        self._start_time = now

    def finish(self) -> Dict[str, float]:
        if self._current_stage and self._start_time:
            now = time.perf_counter()
            self.timings[self._current_stage] = round(now - self._start_time, 3)
            logger.info(f"Stage '{self._current_stage}' completed in {self.timings[self._current_stage]}s")
        return self.timings

