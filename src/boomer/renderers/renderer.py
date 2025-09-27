from dataclasses import dataclass
from boomer.model import Solution, KB
from abc import ABC, abstractmethod
from typing import Optional


@dataclass
class Renderer(ABC):
    """
    Renders a solution in a human-readable format.
    """

    @abstractmethod
    def render(self, solution: Solution, kb: Optional[KB] = None) -> str:
        pass
