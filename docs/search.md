# Search in BOOMER

BOOMER uses search algorithms to find the most probable consistent interpretation of a knowledge base. This page explains how the search process works and how to configure it.

## Search Overview

The goal of the search is to find the optimal combination of truth values for all probabilistic facts in the knowledge base, where:

1. The combination is logically consistent (satisfiable)
2. The combination has the highest probability among all satisfiable combinations

## The Search Algorithm

BOOMER's search algorithm is essentially a tree-based search that explores possible combinations of truth values for probabilistic facts:

1. **Initialization**: Start with an empty set of selections
2. **Expansion**: Select a probabilistic fact and consider both its true and false values
3. **Reasoning**: Apply logical reasoning to derive entailed facts
4. **Pruning**: Discard unsatisfiable branches early
5. **Scoring**: Calculate the probability of each satisfiable combination
6. **Selection**: Return the most probable satisfiable combination as the solution

## Search Configuration

You can configure the search behavior using the `SearchConfig` class:

```python
from boomer.model import SearchConfig
from boomer.search import solve

config = SearchConfig(
    max_iterations=1000000,
    max_candidate_solutions=10000,
    timeout_seconds=30
)

solution = solve(kb, config)
```

### Configuration Parameters

- **max_iterations**: Maximum number of search iterations to perform
- **max_candidate_solutions**: Maximum number of solutions to collect
- **timeout_seconds**: Maximum time in seconds to run the search
- **reasoner_class**: The reasoner implementation to use

## Search Functions

BOOMER provides two main search functions:

### `search(kb, config)`

The low-level search function that yields tree nodes as they are explored:

```python
from boomer.search import search

# Iterate through nodes in the search tree
for node in search(kb, config):
    if node.terminal:
        print(f"Found terminal node with probability: {node.pr}")
```

### `solve(kb, config)`

The high-level function that performs the search and returns a complete solution:

```python
from boomer.search import solve

# Get the complete solution
solution = solve(kb, config)
print(f"Confidence: {solution.confidence}")
print(f"Posterior probability: {solution.posterior_prob}")
```

## The Solution

The result of the search is a `Solution` object that contains:

- **solved_pfacts**: List of probabilistic facts with their truth values and posterior probabilities
- **confidence**: Confidence in the best solution (higher means stronger preference for this solution)
- **prior_prob**: Prior probability of the solution
- **posterior_prob**: Posterior probability of the solution
- **number_of_combinations**: Number of combinations explored
- **number_of_satisfiable_combinations**: Number of satisfiable combinations found
- **time_elapsed**: Time taken to find the solution
- **timed_out**: Whether the search timed out

## Automatic Partitioning and Subclustering

When `solve()` encounters a large KB, it automatically applies partitioning:

1. **Threshold Check**: If KB size exceeds `partition_initial_threshold`, partitioning begins
2. **Graph-based Partitioning**: KB is split into strongly connected components
3. **Recursive Subclustering**: Large components are further subdivided if needed
4. **Independent Solving**: Each partition is solved separately
5. **Solution Combination**: Individual solutions are merged into the final result

This happens transparently - you just call `solve()` and BOOMER handles the complexity:

```python
# BOOMER automatically partitions this large KB
large_kb = KB(pfacts=[...])  # 1000+ pfacts
solution = solve(large_kb, SearchConfig(max_pfacts_per_clique=100))
# Behind the scenes: partitions into manageable chunks, solves each, combines results
```

## Next Steps

- Learn about [Partitioning](partitioning.md) to understand how BOOMER handles large KBs efficiently
- Explore [Grid Search](grid-search.md) to find optimal search parameters
- See [Examples](examples.md) for practical usage patterns

## Search Strategies

### Depth-First vs. Breadth-First

BOOMER uses a depth-first search strategy by default, which means it explores one branch of the tree as far as possible before backtracking. This is efficient for finding satisfiable solutions quickly.

### Probability-Guided Search

The search is guided by probabilities, preferentially exploring branches that are more likely to lead to high-probability solutions.

### Pruning

To make the search more efficient, BOOMER uses pruning strategies:

1. **Early Termination**: Stop exploring a branch if it's already unsatisfiable
2. **Duplicate Detection**: Avoid exploring the same state multiple times
3. **Timeout**: Stop the search after a specified time limit

## Performance Considerations

The search space grows exponentially with the number of probabilistic facts, so performance can be a concern for large knowledge bases. Consider the following tips:

1. **Limit the number of probabilistic facts** to those that are most relevant
2. **Use timeouts** to ensure the search completes in a reasonable time
3. **Adjust max_candidate_solutions** to balance thoroughness and performance
4. **Start with a small sample** to get a sense of the runtime before scaling up

## Example

Here's a complete example of configuring and running a search:

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

# Configure the search
config = SearchConfig(
    max_iterations=100000,
    max_candidate_solutions=1000,
    timeout_seconds=10
)

# Solve the knowledge base
solution = solve(kb, config)

# Print results
print(f"Solution found with confidence: {solution.confidence}")
print(f"Time taken: {solution.time_elapsed} seconds")
print(f"Timed out: {solution.timed_out}")

# Print the truth values and posterior probabilities of facts
for spf in solution.solved_pfacts:
    print(f"{spf.truth_value}: {spf.pfact.fact} (posterior: {spf.posterior_prob})")
```

This example demonstrates how to create a knowledge base with probabilistic facts, configure the search, and analyze the results.