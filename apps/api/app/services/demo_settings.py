"""Hidden demo-panel settings (F17). In memory, because there is one process and a reset clears them."""

from __future__ import annotations

from dataclasses import asdict, dataclass

DEFAULT_SIM_SPEED_MPS = 1.5


@dataclass
class DemoSettings:
    force_cached_ai: bool = False
    sim_speed_mps: float = DEFAULT_SIM_SPEED_MPS

    def as_dict(self) -> dict:
        return asdict(self)

    def reset(self) -> None:
        self.force_cached_ai = False
        self.sim_speed_mps = DEFAULT_SIM_SPEED_MPS


demo_settings = DemoSettings()
