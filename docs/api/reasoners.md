# Reasoners API Reference

This page documents the reasoners used in BOOMER.

## Reasoner Interface

```python
@dataclass
class Reasoner(ABC):
    """Abstract base class for reasoners."""
    
    @abstractmethod
    def reason(self, kb: KB, selections: List[Grounding], candidates: List[Grounding] | None = None) -> ReasonerResult:
        """
        Perform reasoning on a knowledge base with a set of selections.
        
        Args:
            kb: The knowledge base to reason over
            selections: Current selections (facts with truth values)
            candidates: Optional list of candidate facts to consider
            
        Returns:
            A ReasonerResult with entailed selections and unsatisfiable facts
        """
        pass
```

## ReasonerResult

```python
@dataclass
class ReasonerResult:
    """
    Result of reasoning.
    
    Attributes:
        unsatisfiable_facts: List of facts that make the KB unsatisfiable
        entailed_selections: List of selections entailed by the KB and current selections
    """
    unsatisfiable_facts: List[Fact]
    entailed_selections: List[Grounding]

    @property
    def satisfiable(self) -> bool:
        """Return True if the knowledge base is satisfiable with the given selections."""
        return len(self.unsatisfiable_facts) == 0
```

## NxReasoner

```python
class NxReasoner(Reasoner):
    """
    Reasoner that uses a networkx graph to reason about the KB.
    
    This reasoner builds a directed graph representing the relationships
    between entities and performs reasoning operations on this graph.
    """

    def reason(self, kb: KB, selections: List[Grounding], candidates: List[PFactIndex] | None = None) -> ReasonerResult:
        """
        Perform reasoning using NetworkX graph operations.
        
        Args:
            kb: The knowledge base to reason over
            selections: Current selections (facts with truth values)
            candidates: Optional list of candidate facts to consider
            
        Returns:
            A ReasonerResult with entailed selections and unsatisfiable facts
        """
```

## Utility Functions

### get_reasoner

```python
def get_reasoner(reasoner_class: str) -> Reasoner:
    """
    Get a reasoner instance by class name.
    
    Args:
        reasoner_class: The fully qualified class name of the reasoner
        
    Returns:
        An instance of the specified reasoner
        
    Raises:
        ImportError: If the reasoner class cannot be imported
        AttributeError: If the reasoner class cannot be found in the module
    """
```

### filter_unsats

```python
def filter_unsats(fact_states: List[Tuple[bool, PFactIndex, Fact]]) -> List[Fact]:
    """
    Filter unsatisfiable facts from fact states.
    
    Args:
        fact_states: List of (truth_value, index, fact) tuples
        
    Returns:
        List of unsatisfiable facts
    """
```

## Usage Example

```python
from boomer.model import KB, PFact, EquivalentTo
from boomer.reasoners.nx_reasoner import NxReasoner
from boomer.reasoners import get_reasoner

# Create a knowledge base
kb = KB(
    pfacts=[
        PFact(fact=EquivalentTo(sub="A", equivalent="B"), prob=0.9),
        PFact(fact=EquivalentTo(sub="B", equivalent="C"), prob=0.8),
    ]
)

# Create a reasoner directly
reasoner = NxReasoner()

# Or get a reasoner by class name
reasoner = get_reasoner("boomer.reasoners.nx_reasoner.NxReasoner")

# Define some selections (fact index, truth value)
selections = [(0, True), (1, False)]  # A=B is true, B=C is false

# Perform reasoning
result = reasoner.reason(kb, selections)

# Check if the result is satisfiable
if result.satisfiable:
    print("The knowledge base is satisfiable with the given selections")
    print("Entailed selections:", result.entailed_selections)
else:
    print("The knowledge base is unsatisfiable with the given selections")
    print("Unsatisfiable facts:", result.unsatisfiable_facts)
```

## Creating Custom Reasoners

To create a custom reasoner, implement the `Reasoner` interface:

```python
from boomer.reasoners.reasoner import Reasoner, ReasonerResult
from boomer.model import KB, Grounding, Fact

class MyCustomReasoner(Reasoner):
    def reason(self, kb: KB, selections: List[Grounding], candidates: List[Grounding] | None = None) -> ReasonerResult:
        # Implement your reasoning logic here
        # ...
        
        # Return a ReasonerResult with:
        # 1. Unsatisfiable facts (empty list if satisfiable)
        # 2. Entailed selections
        return ReasonerResult(
            unsatisfiable_facts=[],
            entailed_selections=selections
        )
```