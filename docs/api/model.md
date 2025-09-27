# Model API Reference

This page documents the core data model classes used in BOOMER.

## Knowledge Base

```python
class KB:
    """
    A knowledge base is a collection of facts and probabilistic facts.
    
    Attributes:
        facts: A list of deterministic facts (certainty of 1.0)
        pfacts: A list of probabilistic facts with assigned probabilities
        name: Optional name of the knowledge base
        description: Optional description of the knowledge base contents
        comments: Optional comments about the knowledge base (e.g., source, usage notes)
    """
    def normalize(self):
        """Ensure all facts are ordered by probability, highest first."""
        
    def number_of_combinations(self) -> int:
        """Return the number of combinations of the facts."""
        
    def pfact_index(self, fact: Fact) -> Optional[int]:
        """Return the index of the fact in the pfacts list."""
```

## Facts

### BaseFact

```python
@dataclass(frozen=True)
class BaseFact(ABC):
    """Base class for all facts."""
    pass
```

### SubClassOf

```python
@dataclass(frozen=True)
class SubClassOf(BaseFact):
    """
    A subclass relationship between two entities.
    
    Attributes:
        sub: The subclass entity identifier
        sup: The superclass entity identifier
    """
    sub: EntityIdentifier
    sup: EntityIdentifier
```

### ProperSubClassOf

```python
@dataclass(frozen=True)
class ProperSubClassOf(BaseFact):
    """
    A proper subclass of a class is a subclass of a class that is not the same as the class itself.
    
    Attributes:
        sub: The subclass entity identifier
        sup: The superclass entity identifier
    """
    sub: EntityIdentifier
    sup: EntityIdentifier
```

### EquivalentTo

```python
@dataclass(frozen=True)
class EquivalentTo(BaseFact):
    """
    An equivalence relationship between two entities.
    
    Attributes:
        sub: The subject entity identifier
        equivalent: The equivalent entity identifier
    """
    sub: str
    equivalent: EntityIdentifier
```

### NotInSubsumptionWith

```python
@dataclass(frozen=True)
class NotInSubsumptionWith(BaseFact):
    """
    Indicates that two entities are not in a subsumption relationship.
    
    Attributes:
        sub: The subject entity identifier
        sibling: The sibling entity identifier
    """
    sub: EntityIdentifier
    sibling: EntityIdentifier
```

### MemberOfDisjointGroup

```python
@dataclass(frozen=True)
class MemberOfDisjointGroup:
    """
    Indicates that an entity belongs to a disjoint group.
    
    Attributes:
        sub: The entity identifier
        group: The disjoint group identifier
    """
    sub: EntityIdentifier
    group: str
```

## Probabilistic Facts

### PFact

```python
@dataclass
class PFact:
    """
    A probabilistic fact is a fact and a probability.
    
    Attributes:
        fact: The fact (SubClassOf, EquivalentTo, etc.)
        prob: The probability of the fact (0.0 to 1.0)
    """
    fact: Fact
    prob: float
```

## Search Configuration

```python
class SearchConfig(BaseModel):
    """
    A search configuration is a configuration for a search.
    
    Attributes:
        reasoner_class: The class name of the reasoner to use
        max_iterations: Maximum number of iterations in the search
        max_candidate_solutions: Maximum number of candidate solutions to generate
        timeout_seconds: Maximum time in seconds to allow search to run (None means no timeout)
    """
    reasoner_class: str
    max_iterations: int = 1000000
    max_candidate_solutions: int = 10000
    timeout_seconds: Optional[float] = None
```

## Solution

```python
@dataclass
class Solution:
    """
    A solution is a grounding of probabilistic facts.
    
    Attributes:
        ground_pfacts: List of tuples of (PFact, bool) representing grounded facts
        solved_pfacts: List of SolvedPFact objects
        number_of_combinations: The number of explicitly explored combinations
        number_of_satisfiable_combinations: Number of satisfiable combinations found
        number_of_combinations_explored_including_implicit: Total combinations explored
        confidence: Confidence in the solution (0.0 to 1.0)
        prior_prob: Prior probability of the solution
        posterior_prob: Posterior probability of the solution
        proportion_of_combinations_explored: Proportion of combinations explored
        time_started: Timestamp when the search started
        time_finished: Timestamp when the search finished
        timed_out: Whether the search timed out
    """
    
    @property
    def time_elapsed(self) -> Optional[float]:
        """
        Returns the elapsed time in seconds between start and finish.
        Returns None if either time_started or time_finished is not set.
        """
```

### SolvedPFact

```python
@dataclass
class SolvedPFact:
    """
    A solved probabilistic fact with truth value and posterior probability.
    
    Attributes:
        pfact: The original probabilistic fact
        truth_value: Whether the fact is considered true in the solution
        posterior_prob: The posterior probability of the fact
    """
    pfact: PFact
    truth_value: bool
    posterior_prob: float
```

## Tree Node

```python
@dataclass
class TreeNode:
    """
    A node in the search tree.
    
    Attributes:
        parent: Parent node
        depth: Depth in the search tree
        selection: The selected grounding
        asserted_selections: List of explicitly asserted selections
        selections: List of all selections (asserted + derived)
        pr_selected: Probability of the selections
        pr: Overall probability
        terminal: Whether this is a terminal node
    """
    
    @property
    def satifiable(self) -> bool:
        """Return True if the solution at this node is satisfiable."""
        
    @property
    def identifier(self) -> NodeIdentifier:
        """Return a unique identifier for the node."""
```

## Type Aliases

```python
NodeIdentifier = str
EntityIdentifier = str
PFactIndex = int
Grounding = Tuple[PFactIndex, bool]
Fact = SubClassOf | ProperSubClassOf | EquivalentTo | NotInSubsumptionWith
```