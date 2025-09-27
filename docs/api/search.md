# Search API Reference

This page documents the search functionality in BOOMER.

## Main Functions

### solve

```python
def solve(kb: KB, config: SearchConfig | None = None) -> Solution:
    """
    Solve a knowledge base to find the most probable consistent interpretation.
    
    Args:
        kb: The knowledge base to solve
        config: Search configuration (optional)
        
    Returns:
        A Solution object containing the solved facts
        
    Raises:
        ValueError: If no solutions are found
    """
```

### search

```python
def search(kb: KB, config: SearchConfig) -> Iterator[TreeNode]:
    """
    Search for solutions for the knowledge base.
    
    Args:
        kb: The knowledge base to search
        config: Search configuration
        
    Yields:
        TreeNode: Generated search tree nodes
    """
```

## Helper Functions

### calc_prob_unselected

```python
def calc_prob_unselected(kb: KB, node: TreeNode) -> float:
    """
    Calculate the probability of unselected facts.
    
    Args:
        kb: Knowledge base
        node: Current search tree node
        
    Returns:
        The probability of unselected facts
    """
```

### extend_node

```python
def extend_node(node: TreeNode, kb: KB, selection: Grounding, reasoner: Reasoner) -> TreeNode:
    """
    Extend a node with a new selection.
    
    Args:
        node: The node to extend
        kb: Knowledge base
        selection: The selection to add
        reasoner: The reasoner to use
        
    Returns:
        A new node with the selection added
    """
```

### node_remaining_selections_iter

```python
def node_remaining_selections_iter(node: TreeNode, kb: KB) -> Iterator[Grounding]:
    """
    Iterate over the remaining selections for a node.
    
    Args:
        node: The current node
        kb: Knowledge base
        
    Yields:
        Possible selections for the node
    """
```

### all_node_extensions

```python
def all_node_extensions(node: TreeNode, kb: KB, vt: VisitationTracker, reasoner: Reasoner) -> Iterator[TreeNode]:
    """
    Generate all valid extensions of a node.
    
    Args:
        node: The node to extend
        kb: Knowledge base
        vt: Visitation tracker to avoid duplicates
        reasoner: The reasoner to use
        
    Yields:
        Extended nodes
    """
```

### pr_selection_best

```python
def pr_selection_best(kb: KB, selection: Grounding) -> Tuple[float, bool]:
    """
    Calculate the probability of a selection.
    
    Args:
        kb: Knowledge base of facts and probabilistic facts.
        selection: A selected fact
        
    Returns:
        The probability of the selection and its truth value.
    """
```

## Supporting Classes

### VisitationTracker

```python
@dataclass
class VisitationTracker:
    """
    Tracks visited nodes and unsatisfiable combinations.
    
    Attributes:
        visited: Set of visited selection combinations
        unsatisfiable_combos: Set of known unsatisfiable combinations
    """
    visited: Set[Set[Grounding]] 
    unsatisfiable_combos: Set[Set[Grounding]]
```

## Usage Example

```python
from boomer.model import KB, PFact, EquivalentTo, SearchConfig
from boomer.search import solve

# Create a knowledge base
kb = KB(
    pfacts=[
        PFact(fact=EquivalentTo(sub="A", equivalent="B"), prob=0.9),
        PFact(fact=EquivalentTo(sub="B", equivalent="C"), prob=0.8),
        PFact(fact=EquivalentTo(sub="A", equivalent="C"), prob=0.7),
    ]
)

# Create a search configuration
config = SearchConfig(
    max_iterations=100000,
    max_candidate_solutions=1000,
    timeout_seconds=10
)

# Solve the knowledge base
solution = solve(kb, config)

# Print results
print(f"Confidence: {solution.confidence}")
print(f"Time taken: {solution.time_elapsed} seconds")
print(f"Timed out: {solution.timed_out}")

# Print the truth values and posterior probabilities of facts
for spf in solution.solved_pfacts:
    print(f"{spf.truth_value}: {spf.pfact.fact} (posterior: {spf.posterior_prob})")
```