# Data Model

BOOMER is built on a structured data model that represents probabilistic facts and their relationships. Understanding this model is key to using BOOMER effectively.

## Core Components

### Knowledge Base (KB)

The `KB` class is the central container for all knowledge in BOOMER. It holds both deterministic facts and probabilistic facts.

```python
from boomer.model import KB

kb = KB(
    name="My Knowledge Base",
    description="This is a sample knowledge base",
    facts=[...],  # Deterministic facts
    pfacts=[...],  # Probabilistic facts
    comments="Additional information about this KB"
)
```

#### Properties:
- `name`: Identifier for the knowledge base
- `description`: Human-readable description
- `facts`: List of deterministic facts (100% certainty)
- `pfacts`: List of probabilistic facts (with associated probabilities)
- `comments`: Additional metadata or notes

### Facts

Facts represent logical assertions about entities. BOOMER supports several types of facts:

#### SubClassOf

Represents a taxonomic relationship where one class is a subclass of another.

```python
from boomer.model import SubClassOf

fact = SubClassOf(sub="Mammal", sup="Animal")
```

#### ProperSubClassOf

Similar to SubClassOf, but enforces that the subclass is not equivalent to the superclass.

```python
from boomer.model import ProperSubClassOf

fact = ProperSubClassOf(sub="Dog", sup="Mammal")
```

#### EquivalentTo

Represents that two entities are equivalent or identical.

```python
from boomer.model import EquivalentTo

fact = EquivalentTo(sub="Human", equivalent="Homo sapiens")
```

#### NotInSubsumptionWith

Indicates that two entities are not in a subsumption relationship (neither is a subclass of the other).

```python
from boomer.model import NotInSubsumptionWith

fact = NotInSubsumptionWith(sub="Fish", sibling="Mammal")
```

#### MemberOfDisjointGroup

Indicates that an entity belongs to a disjoint group, meaning it cannot be equivalent to any other entity in a different disjoint group.

```python
from boomer.model import MemberOfDisjointGroup

fact = MemberOfDisjointGroup(sub="MONDO:0000001", group="MONDO")
```

### Probabilistic Facts (PFacts)

A probabilistic fact combines a fact with a probability value representing the certainty of that fact.

```python
from boomer.model import PFact, EquivalentTo

pfact = PFact(
    fact=EquivalentTo(sub="Disease", equivalent="Disorder"),
    prob=0.8  # 80% certainty
)
```

## Search Configuration

The `SearchConfig` class controls how BOOMER searches for solutions:

```python
from boomer.model import SearchConfig

config = SearchConfig(
    max_iterations=1000000,
    max_candidate_solutions=10000,
    timeout_seconds=30,
    reasoner_class="boomer.reasoners.nx_reasoner.NxReasoner"
)
```

#### Properties:
- `max_iterations`: Maximum number of search iterations
- `max_candidate_solutions`: Maximum number of solutions to consider
- `timeout_seconds`: Maximum time in seconds to run the search
- `reasoner_class`: The reasoner implementation to use

## Solution

The `Solution` class represents the result of solving a knowledge base:

```python
# The solve function returns a Solution object
from boomer.search import solve

solution = solve(kb, config)

print(f"Confidence: {solution.confidence}")
print(f"Prior probability: {solution.prior_prob}")
print(f"Posterior probability: {solution.posterior_prob}")
```

#### Properties:
- `solved_pfacts`: List of `SolvedPFact` objects with truth values and posterior probabilities
- `confidence`: Confidence in the best solution (0-1)
- `prior_prob`: Prior probability of the solution
- `posterior_prob`: Posterior probability of the solution
- `number_of_combinations`: Number of combinations explored
- `number_of_satisfiable_combinations`: Number of satisfiable combinations found
- `time_started`, `time_finished`, `time_elapsed`: Timing information
- `timed_out`: Whether the search timed out

### SolvedPFact

Each probabilistic fact in the solution is represented by a `SolvedPFact` that includes the original fact, its determined truth value, and its posterior probability.

```python
# Accessing solved facts
for spf in solution.solved_pfacts:
    if spf.truth_value and spf.posterior_prob > 0.8:
        print(f"High confidence: {spf.pfact.fact} (posterior: {spf.posterior_prob})")
```

## Data Flow

The typical flow of data in BOOMER is:

1. Create or load a `KB` with facts and probabilistic facts
2. Configure the search with `SearchConfig`
3. Run `solve()` to get a `Solution`
4. Analyze the `solved_pfacts` for results

This structured approach allows BOOMER to represent complex knowledge with uncertainty and find the most probable consistent interpretation.