from dataclasses import dataclass
from typing import List
from abc import ABC, abstractmethod
from boomer.model import *


@dataclass
class ReasonerResult:
    unsatisfiable_facts: List[Fact]
    entailed_selections: List[Grounding] # index into pfacts in kb
    entailed_hypotheses: List[Tuple[PFact, bool]] | None = None

    @property
    def satisfiable(self) -> bool:
        return len(self.unsatisfiable_facts) == 0


@dataclass
class Reasoner(ABC):
    """
    Base class for all reasoners, which calculate entailed facts and satisfiability of a KB.
    """
    state: ReasonerState | None = None

    @abstractmethod
    def reason(
        self,
        kb: KB,
        selections: List[Grounding] | None = None,
        #candidates: List[Grounding] | None = None,
    ) -> ReasonerResult:
        """
        Reason about a KB.

        Args:
            kb: The knowledge base to reason about.
            selections: The selections to reason about.
            candidates: The candidates to reason about.

        Returns:
            A ReasonerResult object containing the unsatisfiable facts, entailed selections, and entailed hypotheses.
        """
        pass
