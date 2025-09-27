# Knowledge Base Partitioning

BOOMER uses graph-based partitioning to decompose large knowledge bases into smaller, independent components called **cliques**. This approach significantly improves computational efficiency while maintaining logical consistency.

## Overview

Knowledge base partitioning identifies groups of related entities that form **strongly connected components** in the entity relationship graph. Each component can be solved independently, dramatically reducing the combinatorial explosion that would occur when solving the entire KB at once.

## How Partitioning Works

### Entity Relationship Graph

BOOMER constructs a directed graph where:
- **Nodes** represent entities (concepts, terms, identifiers)
- **Edges** represent relationships between entities

Different fact types create different edge patterns:
- **EquivalentTo**: Creates bidirectional edges (A ↔ B)
- **SubClassOf/ProperSubClassOf**: Creates unidirectional edges (A → B)
- **DisjointWith**: Tracked but doesn't create edges for partitioning

### Strongly Connected Components

A strongly connected component (SCC) is a group of entities where every entity can reach every other entity through directed paths. BOOMER uses NetworkX's `strongly_connected_components()` algorithm to identify these groups.

Examples:
1. **Simple Equivalence Chain**: If A≡B and B≡C, then {A, B, C} form one component
2. **Mixed Relationships**: If A⊆B, B≡C, C⊆D, D≡A, then {A, B, C, D} form one component (all mutually reachable)
3. **Isolated Hierarchies**: If A⊆B and C⊆D with no connections between them, they form separate components

### Automatic Subclustering Strategy

When the solve() function encounters a large KB, it automatically applies a two-phase partitioning strategy:

1. **Initial Threshold Check**: If the KB has more pfacts than `partition_initial_threshold` (default: often the same as `max_pfacts_per_clique`), the KB is partitioned into strongly connected components

2. **Recursive Subclustering**: Each partition is solved recursively:
   - If a partition still exceeds `max_pfacts_per_clique`, it's further subdivided
   - The `partition_initial_threshold` is updated to prevent infinite recursion
   - Each sub-KB is solved independently
   - Solutions are combined to form the final result

This automatic subclustering ensures that even very large KBs can be processed efficiently without manual intervention.

## Benefits of Partitioning

### Computational Efficiency

Without partitioning, a KB with n probabilistic facts requires exploring 2^n combinations. With partitioning:

```
Total combinations = 2^n1 + 2^n2 + ... + 2^nk
```

Where n1, n2, ..., nk are the sizes of individual cliques.

**Example**: A KB with 20 pfacts
- Without partitioning: 2^20 = 1,048,576 combinations
- With 4 cliques of 5 pfacts each: 4 × 2^5 = 128 combinations
- Speedup: 8,192x faster!

### Logical Independence

Each clique represents a logically independent subset of the KB:
- Facts in different cliques don't interact
- Solutions for each clique can be combined without conflicts
- Parallel processing becomes possible

## Clique Size Management

Large cliques can still be computationally expensive. BOOMER provides the `max_pfacts_per_clique` parameter to limit clique sizes.

### How It Works

When a clique exceeds the maximum size:
1. Probabilistic facts are sorted by probability (highest first)
2. Only the top N facts are retained
3. Lower probability facts are pruned

### CLI Usage

```bash
# Limit each clique to maximum 100 probabilistic facts
boomer-cli solve large_kb.json --max-pfacts-per-clique 100

# More aggressive pruning for very large KBs
boomer-cli solve huge_kb.yaml -C 50
```

### Python API

```python
from boomer.splitter import partition_kb
from boomer.search import solve

# Partition with size limit
partitions = partition_kb(kb, max_pfacts_per_clique=100)

# Solve each partition
solutions = []
for partition in partitions:
    solution = solve(partition)
    solutions.append(solution)
```

## Advanced Subclustering Algorithm

### How Subclustering Works

When a clique is still too large after initial partitioning, BOOMER employs an iterative subclustering algorithm:

1. **Sort by Probability**: Pfacts are sorted by probability (highest first)
2. **Iterative Dropping**: Temporarily remove the lowest probability pfacts
3. **Re-evaluate Components**: Check if removing pfacts creates smaller connected components
4. **Component Extraction**: When a suitable component is found, extract it as a sub-KB
5. **Restore and Repeat**: Re-add dropped pfacts and continue with remaining entities

### The split_connected_components Algorithm

The algorithm progressively "chips away" at large cliques:

```python
# Pseudocode for the subclustering strategy
while clique has pfacts:
    dropped_pfacts = []

    while no suitable split found:
        # Analyze current graph structure
        components = find_strongly_connected_components(clique)

        for component in components:
            if min_size <= component_size <= max_size:
                # Found a good sub-clique
                yield component
                break

        if no split:
            # Drop lowest probability pfacts temporarily
            drop lowest probability pfacts (in batches)
            add to dropped_pfacts list

    # Restore dropped pfacts for remaining processing
    restore dropped_pfacts
```

### Key Parameters

- **Step Size**: Number of pfacts to drop at once (default: KB size / 20 + 1)
- **Min PFacts per Clique**: Minimum size for a viable sub-clique (default: 5)
- **Max PFacts per Clique**: Maximum allowed clique size

### Example: Progressive Subclustering

Consider a highly connected KB with 200 pfacts in a single component:

```python
from boomer.model import SearchConfig
from boomer.search import solve

config = SearchConfig(
    max_pfacts_per_clique=50,      # Target maximum size
    partition_initial_threshold=50  # When to start partitioning
)

# The solve() function automatically:
# 1. Detects KB has 200 pfacts > threshold of 50
# 2. Attempts initial partitioning
# 3. If still too large, applies subclustering:
#    - Drops low-probability pfacts in batches of ~10
#    - Checks if this creates smaller components
#    - Extracts components of size 5-50
#    - Continues until all pfacts are assigned
solution = solve(kb, config)
```

## Practical Examples

### Example 1: Disease Mapping with Multiple Systems

Consider mapping between three disease classification systems:

```python
from boomer.model import KB, PFact, EquivalentTo

kb = KB(pfacts=[
    # MONDO to ICD10 mappings
    PFact(fact=EquivalentTo("MONDO:001", "ICD10:A01"), prob=0.9),
    PFact(fact=EquivalentTo("MONDO:001", "ICD10:A02"), prob=0.3),

    # MONDO to SNOMED mappings
    PFact(fact=EquivalentTo("MONDO:001", "SNOMED:123"), prob=0.8),

    # Separate disease cluster
    PFact(fact=EquivalentTo("MONDO:002", "ICD10:B01"), prob=0.9),
    PFact(fact=EquivalentTo("MONDO:002", "SNOMED:456"), prob=0.8),
])

# This creates 2 cliques:
# Clique 1: {MONDO:001, ICD10:A01, ICD10:A02, SNOMED:123}
# Clique 2: {MONDO:002, ICD10:B01, SNOMED:456}
```

### Example 2: Taxonomic Relationships

```python
kb = KB(
    facts=[
        ProperSubClassOf("cat", "mammal"),
        ProperSubClassOf("dog", "mammal"),
        ProperSubClassOf("mammal", "animal"),
    ],
    pfacts=[
        PFact(fact=EquivalentTo("cat", "feline"), prob=0.9),
        PFact(fact=EquivalentTo("dog", "canine"), prob=0.9),

        # Separate plant taxonomy
        PFact(fact=EquivalentTo("rose", "Rosa"), prob=0.9),
        PFact(fact=EquivalentTo("oak", "Quercus"), prob=0.9),
    ]
)

# Creates multiple cliques based on connectivity
```

## Visualizing Partitions

You can inspect how your KB was partitioned:

```python
from boomer.splitter import partition_kb, kb_to_graph
import networkx as nx

# Create the entity graph
graph = kb_to_graph(kb)

# Find strongly connected components
components = list(nx.strongly_connected_components(graph))
print(f"Found {len(components)} cliques")

for i, component in enumerate(components):
    print(f"Clique {i}: {component}")

# Or use the partition function directly
partitions = list(partition_kb(kb))
for i, partition in enumerate(partitions):
    print(f"Partition {i}:")
    print(f"  Entities: {len(partition.pfacts)} pfacts")
    print(f"  Facts: {len(partition.facts)} facts")
```

## Performance Considerations

### When Partitioning Helps Most

1. **Multiple independent mappings**: Different ontology alignments in the same file
2. **Sparse connectivity**: Facts that relate to distinct entity groups
3. **Large knowledge bases**: KBs with hundreds or thousands of facts

### When Partitioning Has Limited Effect

1. **Highly connected KBs**: Where most entities relate to each other
2. **Single large equivalence class**: All entities are potentially equivalent
3. **Dense relationship networks**: Heavy use of transitive relationships

## Configuration Guidelines

### Choosing `max_pfacts_per_clique`

The optimal value depends on:
- **Available memory**: Each clique uses 2^n memory for n pfacts
- **Time constraints**: Larger cliques take exponentially longer
- **Accuracy requirements**: Pruning may remove important low-probability facts

Recommended starting points:
- Small KBs (< 100 pfacts): No limit needed
- Medium KBs (100-1000 pfacts): 100-200
- Large KBs (> 1000 pfacts): 50-100
- Very large KBs: 20-50

### Monitoring Partitioning

Enable verbose output to see partitioning details:

```bash
boomer-cli solve kb.json -vv
```

This will show:
- Number of cliques found
- Size of each clique
- Which facts were pruned (if any)

## Advanced Topics

### Custom Partitioning Strategies

You can implement custom partitioning logic:

```python
from boomer.splitter import partition_kb, extract_sub_kb

def custom_partition(kb, strategy="conservative"):
    if strategy == "conservative":
        # Keep more pfacts per clique
        return partition_kb(kb, max_pfacts_per_clique=200)
    elif strategy == "aggressive":
        # Aggressive pruning for speed
        return partition_kb(kb, max_pfacts_per_clique=30)
    else:
        # No pruning
        return partition_kb(kb)
```

### Parallel Processing

Since cliques are independent, you can process them in parallel:

```python
from concurrent.futures import ProcessPoolExecutor
from boomer.search import solve

def solve_partition(partition):
    return solve(partition)

# Solve all partitions in parallel
partitions = list(partition_kb(kb))
with ProcessPoolExecutor() as executor:
    solutions = list(executor.map(solve_partition, partitions))
```

## How-to Guide: Tuning Subclustering

### Diagnosing When You Need Subclustering

Check if subclustering would help:

```python
from boomer.splitter import kb_to_graph
import networkx as nx

# Analyze your KB structure
graph = kb_to_graph(kb)
components = list(nx.strongly_connected_components(graph))

# Check component sizes
sizes = [len(c) for c in components]
print(f"Number of components: {len(components)}")
print(f"Largest component: {max(sizes)} entities")
print(f"Component size distribution: {sorted(sizes, reverse=True)[:10]}")

# If you have large components (>100 entities), subclustering will help
```

### Choosing the Right Strategy

#### For Speed-Critical Applications

```python
config = SearchConfig(
    max_pfacts_per_clique=30,       # Aggressive limit
    partition_initial_threshold=30   # Start partitioning early
)
```

#### For Accuracy-Critical Applications

```python
config = SearchConfig(
    max_pfacts_per_clique=150,       # Conservative limit
    partition_initial_threshold=100  # Partition only when necessary
)
```

#### For Balanced Performance

```python
config = SearchConfig(
    max_pfacts_per_clique=75,        # Moderate limit
    partition_initial_threshold=50   # Balanced threshold
)
```

### Monitoring Subclustering Progress

Enable verbose logging to track subclustering:

```bash
# Set logging level to see subclustering details
export BOOMER_LOG_LEVEL=INFO
boomer-cli solve large_kb.json -C 50
```

You'll see output like:
```
Partitioning KB into 3 sub-KBs
Solving sub-KB: 45 facts, 89 pfacts
Splitting 89 pfacts into 50 pfacts per clique
Found split: 48 / 89 pfacts
Remaining: 41 pfacts
Sub-solution: pr:0.73 // post:0.95 // 1024 combinations
```

## Reference: Subclustering Parameters

### SearchConfig Parameters

| Parameter | Default | Description | When to Adjust |
|-----------|---------|-------------|----------------|
| `max_pfacts_per_clique` | None | Maximum pfacts per clique | Set when memory/time is limited |
| `partition_initial_threshold` | Same as max_pfacts_per_clique | When to trigger partitioning | Lower for earlier partitioning |
| `max_iterations` | 1000000 | Max search iterations | Increase for complex problems |
| `timeout_seconds` | None | Time limit per solve | Set for production systems |

### partition_kb() Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `kb` | KB | Knowledge base to partition |
| `max_pfacts_per_clique` | Optional[int] | Maximum pfacts per partition |
| `min_pfacts_per_clique` | int (default: 5) | Minimum viable partition size |

### split_connected_components() Internal Parameters

| Parameter | Calculation | Purpose |
|-----------|------------|---------|
| `step_size` | len(kb.pfacts) // 20 + 1 | Pfacts dropped per iteration |
| `dropped_pfacts` | List | Temporarily removed pfacts |
| `is_split` | Boolean | Whether a viable split was found |

## Troubleshooting Subclustering

### Issue: Subclustering Takes Too Long

**Symptoms**: The partitioning phase runs for minutes

**Solutions**:
1. Reduce `max_pfacts_per_clique` to create smaller partitions faster
2. Increase the step_size in the algorithm (requires code modification)
3. Use more aggressive probability filtering before partitioning

### Issue: Important Facts Are Being Dropped

**Symptoms**: Low-probability but important facts missing from solution

**Solutions**:
1. Increase `max_pfacts_per_clique` to retain more facts
2. Pre-boost probabilities of known important facts
3. Use manual partitioning for critical fact groups

### Issue: Memory Exhaustion

**Symptoms**: Out of memory errors during solving

**Solutions**:
1. Reduce `max_pfacts_per_clique` significantly (try 20-30)
2. Enable incremental solving with smaller batches
3. Use the CLI with output streaming instead of in-memory processing

## Best Practices

1. **Start without limits**: First try solving without `max_pfacts_per_clique`
2. **Monitor performance**: Use verbose mode to understand partitioning behavior
3. **Adjust gradually**: If needed, start with high limits and reduce gradually
4. **Validate results**: Ensure pruning doesn't remove critical facts
5. **Document choices**: Record why specific limits were chosen for reproducibility
6. **Test subclustering**: Use smaller test KBs to understand behavior before production