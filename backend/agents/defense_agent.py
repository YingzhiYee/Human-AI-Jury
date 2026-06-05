from __future__ import annotations

from backend.agents.base import DeliberationAgent
from backend.models import Stance


class DefenseAgent(DeliberationAgent):
    def __init__(self) -> None:
        super().__init__(name="Defense Agent", stance=Stance.NO)
