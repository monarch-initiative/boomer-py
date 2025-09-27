# Reasoning in BOOMER

BOOMER uses logical reasoning to ensure that the knowledge base is consistent and to derive implicit facts from explicit ones. This page explains how reasoning works in BOOMER.

## Reasoning Principles

BOOMER's reasoning is based on the following principles:

1. **Logical Consistency**: The knowledge base must be logically consistent - there should be no contradictions.
2. **Probabilistic Inference**: Facts have probabilities that inform which facts are more likely to be true.
3. **Satisfiability**: A solution is a set of facts that can all be true together without contradiction.

## The Reasoning Process

At a high level, the reasoning process in BOOMER follows these steps:

1. Start with a set of probabilistic facts
2. Generate possible combinations of truth values for these facts
3. For each combination, check if it's logically consistent (satisfiable)
4. Calculate probabilities for satisfiable combinations
5. Select the most probable satisfiable combination as the solution

## The NxReasoner

BOOMER's primary reasoner is the `NxReasoner`, which uses NetworkX (a graph library) to perform reasoning:

```python
from boomer.reasoners.nx_reasoner import NxReasoner
from boomer.model import KB

# The reasoner is typically used internally by the solver
reasoner = NxReasoner()
kb = KB(...)
result = reasoner.reason(kb, selections)
```

### How the NxReasoner Works

The NxReasoner performs the following operations:

1. **Graph Construction**: Creates a directed graph where nodes are entities and edges represent relationships.
2. **Relationship Inference**: Applies rules to infer relationships between entities.
3. **Cycle Detection**: Identifies cycles in the graph that indicate equivalence.
4. **Consistency Checking**: Ensures there are no logical contradictions.

## Reasoning Rules

BOOMER applies several reasoning rules:

### Subsumption Transitivity

If A is a subclass of B, and B is a subclass of C, then A is a subclass of C.

```
SubClassOf(A, B) ∧ SubClassOf(B, C) → SubClassOf(A, C)
```

### Equivalence Symmetry

If A is equivalent to B, then B is equivalent to A.

```
EquivalentTo(A, B) → EquivalentTo(B, A)
```

### Equivalence Transitivity

If A is equivalent to B, and B is equivalent to C, then A is equivalent to C.

```
EquivalentTo(A, B) ∧ EquivalentTo(B, C) → EquivalentTo(A, C)
```

### Disjointness Constraints

Entities in different disjoint groups cannot be equivalent.

```
MemberOfDisjointGroup(A, G1) ∧ MemberOfDisjointGroup(B, G2) ∧ G1 ≠ G2 → ¬EquivalentTo(A, B)
```

## Satisfaction and Conflict Resolution

When there are conflicting probabilistic facts, BOOMER resolves them by:

1. Identifying all possible combinations of truth values
2. Checking each combination for logical consistency
3. Calculating the probability of each consistent combination
4. Selecting the most probable consistent combination

This approach allows BOOMER to handle conflicts in a principled way, favoring high-probability facts while maintaining logical consistency.

## Example of Reasoning

Consider this simple example:

```python
from boomer.model import KB, PFact, ProperSubClassOf, EquivalentTo
from boomer.search import solve

kb = KB(
    pfacts=[
        PFact(fact=ProperSubClassOf("A", "B"), prob=0.9),
        PFact(fact=ProperSubClassOf("B", "C"), prob=0.9),
        PFact(fact=EquivalentTo(sub="A", equivalent="C"), prob=0.1),
    ]
)

solution = solve(kb)
```

In this case, BOOMER would reason:
- If A is a proper subclass of B, and B is a proper subclass of C, then A must be a proper subclass of C
- A cannot be equivalent to C if A is a proper subclass of C
- Since the probability of A⊂B and B⊂C is high (0.9 each), and the probability of A≡C is low (0.1), the most likely consistent solution is that A⊂B, B⊂C, and A≠C

## Extending the Reasoner

BOOMER's reasoning system is designed to be extensible. You can create custom reasoners by implementing the `Reasoner` interface:

```python
from boomer.reasoners.reasoner import Reasoner
from boomer.model import KB, ReasonerResult

class MyCustomReasoner(Reasoner):
    def reason(self, kb: KB, selections, candidates=None) -> ReasonerResult:
        # Implement your reasoning logic here
        ...
        return result
```

This allows for different reasoning strategies to be employed depending on the specific needs of your application.