from __future__ import annotations

from backend.agents.base import DeliberationAgent
from backend.models import Stance


class ProsecutorAgent(DeliberationAgent):
    def __init__(self) -> None:
        super().__init__(name="Prosecutor Agent", stance=Stance.YES)
