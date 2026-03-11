# Supplementary Materials for Boomer-Py

## S1. Extended Algorithm Details

### S1.1 Detailed Reasoning Rules

The NetworkX-based reasoner implements the following inference rules:

#### Equivalence Propagation
For entities a, b, c:
- If a ≡ b and b ≡ c, then a ≡ c (transitivity)
- If a ≡ b and a ⊆ c, then b ⊆ c (substitution)
- If a ≡ b, then a ⊆ b and b ⊆ a (definition)

#### Subsumption Chain
For entities a, b, c:
- If a ⊆ b and b ⊆ c, then a ⊆ c (transitivity)
- If a ⊂ b and b ⊂ c, then a ⊂ c (proper transitivity)
- If a ⊂ b and b ≡ c, then a ⊂ c (mixed inference)

#### Disjointness Constraints
For entities a, b:
- If a ⊥ b and c ⊆ a and d ⊆ b, then c ⊥ d (inheritance)
- If a ≡ b and a ⊥ c, then b ⊥ c (propagation)
- If MemberOfDisjointGroup(a, g) and MemberOfDisjointGroup(b, g), then ¬(a ≡ b)

### S1.2 Probability Calculations

#### Joint Probability
For a set of selections S = {(f₁, v₁), (f₂, v₂), ..., (fₙ, vₙ)} where fᵢ is a fact with probability pᵢ and vᵢ is its truth value:

P(S) = ∏ᵢ P(fᵢ = vᵢ) where P(fᵢ = true) = pᵢ and P(fᵢ = false) = 1 - pᵢ

#### Posterior Probability
For a fact f given all solutions {S₁, S₂, ..., Sₘ}:

P(f = true | consistent) = Σᵢ P(Sᵢ) × 𝟙(f = true in Sᵢ) / Σⱼ P(Sⱼ)

#### Confidence Score
For the best solution S* and next-best S':

confidence = 1 / (1 + exp(-log(P(S*) / P(S'))))

## S2. Implementation Optimizations

### S2.1 Memoization Strategy

The system employs multiple levels of caching:

1. **Reasoner result cache**: Stores logical inferences for fact combinations
2. **Graph reachability cache**: Caches path existence queries in subsumption graphs
3. **Unsatisfiability cache**: Maintains sets of proven inconsistent fact combinations

### S2.2 Memory Management

For large knowledge bases, the implementation uses:

- **Lazy evaluation**: Graph structures built on-demand
- **Incremental updates**: Graphs modified rather than rebuilt
- **Garbage collection hints**: Explicit cleanup of large intermediate structures

### S2.3 Parallel Processing Opportunities

While the current implementation is single-threaded, the architecture supports parallelization:

```python
# Parallel partition solving (future work)
from concurrent.futures import ProcessPoolExecutor

def solve_parallel(kb: KB, config: SearchConfig) -> Solution:
    sub_kbs = list(partition_kb(kb))

    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(solve, sub_kb, config) for sub_kb in sub_kbs]
        sub_solutions = [f.result() for f in futures]

    return combine_solutions(sub_solutions)
```

## S3. Extended Experimental Results

### S3.1 Synthetic Benchmark Generation

We generate synthetic benchmarks with controlled properties:

```python
def generate_ladder_kb(n_levels: int, prob_correct: float = 0.9) -> KB:
    """Generate a ladder-shaped ontology with n levels."""
    pfacts = []
    for i in range(n_levels):
        for j in range(i+1, n_levels):
            # Correct subsumption
            pfacts.append(PFact(
                ProperSubClassOf(f"L{i}", f"L{j}"),
                prob_correct if j == i+1 else prob_correct * 0.8
            ))
            # Incorrect equivalence
            pfacts.append(PFact(
                EquivalentTo(f"L{i}", f"L{j}"),
                (1 - prob_correct) * 0.5
            ))
    return KB(pfacts=pfacts)
```

### S3.2 Brain Ontology Alignment: Full Grid Search Results

We evaluated Boomer-Py on a brain ontology alignment benchmark comprising six Allen Brain Atlas ontologies (EMAPA, HBA, DHBA, MBA, DMBA, PBA) with 2,688 ground truth EquivalentTo facts derived from 1,288 UBERON cross-reference cliques. A grid search over 72 parameter configurations was performed.

#### Metric Ranges Across All 72 Configurations

| Metric | Min | Max | Mean |
|--------|-----|-----|------|
| Precision | 0.41 | 0.80 | 0.64 |
| Recall | 0.23 | 0.48 | 0.39 |
| F1 | 0.36 | 0.54 | 0.48 |

#### Full Grid Search Results

| Config | max_clique | max_solutions | pr_filter | TP | FP | FN | Precision | Recall | F1 |
|--------|-----------|---------------|-----------|------|------|------|-----------|--------|----|
| 0 | 5 | 10 | 0.00 | 1021 | 584 | 1665 | 0.636 | 0.380 | 0.476 |
| 1 | 5 | 10 | 0.20 | 1021 | 584 | 1665 | 0.636 | 0.380 | 0.476 |
| 2 | 5 | 10 | 0.40 | 993 | 504 | 1693 | 0.663 | 0.370 | 0.475 |
| 3 | 5 | 10 | 0.60 | 988 | 494 | 1698 | 0.667 | 0.368 | 0.474 |
| 4 | 5 | 10 | 0.80 | 911 | 303 | 1775 | 0.750 | 0.339 | 0.467 |
| 5 | 5 | 10 | 0.95 | 641 | 166 | 2045 | 0.794 | 0.239 | 0.367 |
| 6 | 5 | 50 | 0.00 | 1021 | 584 | 1665 | 0.636 | 0.380 | 0.476 |
| 7 | 5 | 50 | 0.20 | 1021 | 584 | 1665 | 0.636 | 0.380 | 0.476 |
| 8 | 5 | 50 | 0.40 | 1010 | 559 | 1676 | 0.644 | 0.376 | 0.475 |
| 9 | 5 | 50 | 0.60 | 979 | 487 | 1707 | 0.668 | 0.364 | 0.472 |
| 10 | 5 | 50 | 0.80 | 902 | 273 | 1784 | 0.768 | 0.336 | 0.467 |
| 11 | 5 | 50 | 0.95 | 615 | 159 | 2071 | 0.795 | 0.229 | 0.355 |
| 12 | 5 | 100 | 0.00 | 1021 | 584 | 1665 | 0.636 | 0.380 | 0.476 |
| 13 | 5 | 100 | 0.20 | 1021 | 584 | 1665 | 0.636 | 0.380 | 0.476 |
| 14 | 5 | 100 | 0.40 | 1010 | 559 | 1676 | 0.644 | 0.376 | 0.475 |
| 15 | 5 | 100 | 0.60 | 979 | 487 | 1707 | 0.668 | 0.364 | 0.472 |
| 16 | 5 | 100 | 0.80 | 902 | 273 | 1784 | 0.768 | 0.336 | 0.467 |
| 17 | 5 | 100 | 0.95 | 615 | 159 | 2071 | 0.795 | 0.229 | 0.355 |
| 18 | 5 | 200 | 0.00 | 1021 | 584 | 1665 | 0.636 | 0.380 | 0.476 |
| 19 | 5 | 200 | 0.20 | 1021 | 584 | 1665 | 0.636 | 0.380 | 0.476 |
| 20 | 5 | 200 | 0.40 | 1010 | 559 | 1676 | 0.644 | 0.376 | 0.475 |
| 21 | 5 | 200 | 0.60 | 979 | 487 | 1707 | 0.668 | 0.364 | 0.472 |
| 22 | 5 | 200 | 0.80 | 902 | 273 | 1784 | 0.768 | 0.336 | 0.467 |
| 23 | 5 | 200 | 0.95 | 615 | 159 | 2071 | 0.795 | 0.229 | 0.355 |
| 24 | 10 | 10 | 0.00 | 1186 | 816 | 1500 | 0.592 | 0.442 | 0.506 |
| 25 | 10 | 10 | 0.20 | 1186 | 816 | 1500 | 0.592 | 0.442 | 0.506 |
| 26 | 10 | 10 | 0.40 | 1181 | 811 | 1505 | 0.593 | 0.440 | 0.505 |
| 27 | 10 | 10 | 0.60 | 1166 | 617 | 1520 | 0.654 | 0.434 | 0.522 |
| 28 | 10 | 10 | 0.80 | 1127 | 462 | 1559 | 0.709 | 0.420 | 0.527 |
| 29 | 10 | 10 | 0.95 | 921 | 316 | 1765 | 0.745 | 0.343 | 0.470 |
| 30 | 10 | 50 | 0.00 | 1234 | 776 | 1452 | 0.614 | 0.459 | 0.526 |
| 31 | 10 | 50 | 0.20 | 1234 | 776 | 1452 | 0.614 | 0.459 | 0.526 |
| 32 | 10 | 50 | 0.40 | 1220 | 736 | 1466 | 0.624 | 0.454 | 0.526 |
| 33 | 10 | 50 | 0.60 | 1153 | 564 | 1533 | 0.672 | 0.429 | 0.524 |
| 34 | 10 | 50 | 0.80 | 1112 | 421 | 1574 | 0.725 | 0.414 | 0.527 |
| 35 | 10 | 50 | 0.95 | 890 | 260 | 1796 | 0.774 | 0.331 | 0.464 |
| 36 | 10 | 100 | 0.00 | 1233 | 777 | 1453 | 0.613 | 0.459 | 0.525 |
| 37 | 10 | 100 | 0.20 | 1233 | 777 | 1453 | 0.613 | 0.459 | 0.525 |
| 38 | 10 | 100 | 0.40 | 1222 | 665 | 1464 | 0.648 | 0.455 | 0.534 |
| 39 | 10 | 100 | 0.60 | 1153 | 562 | 1533 | 0.672 | 0.429 | 0.524 |
| 40 | 10 | 100 | 0.80 | 1110 | 412 | 1576 | 0.729 | 0.413 | 0.528 |
| 41 | 10 | 100 | 0.95 | 888 | 246 | 1798 | 0.783 | 0.331 | 0.465 |
| 42 | 10 | 200 | 0.00 | 1233 | 777 | 1453 | 0.613 | 0.459 | 0.525 |
| 43 | 10 | 200 | 0.20 | 1233 | 775 | 1453 | 0.614 | 0.459 | 0.525 |
| 44 | 10 | 200 | 0.40 | 1219 | 625 | 1467 | 0.661 | 0.454 | 0.538 |
| 45 | 10 | 200 | 0.60 | 1148 | 565 | 1538 | 0.670 | 0.427 | 0.522 |
| 46 | 10 | 200 | 0.80 | 1105 | 419 | 1581 | 0.725 | 0.411 | 0.525 |
| 47 | 10 | 200 | 0.95 | 866 | 235 | 1820 | 0.787 | 0.322 | 0.457 |
| 48 | 25 | 10 | 0.00 | 929 | 961 | 1757 | 0.492 | 0.346 | 0.406 |
| 49 | 25 | 10 | 0.20 | 929 | 775 | 1757 | 0.545 | 0.346 | 0.423 |
| 50 | 25 | 10 | 0.40 | 928 | 771 | 1758 | 0.546 | 0.345 | 0.423 |
| 51 | 25 | 10 | 0.60 | 924 | 666 | 1762 | 0.581 | 0.344 | 0.432 |
| 52 | 25 | 10 | 0.80 | 910 | 521 | 1776 | 0.636 | 0.339 | 0.442 |
| 53 | 25 | 10 | 0.95 | 763 | 400 | 1923 | 0.656 | 0.284 | 0.396 |
| 54 | 25 | 50 | 0.00 | 1257 | 1322 | 1429 | 0.487 | 0.468 | 0.477 |
| 55 | 25 | 50 | 0.20 | 1257 | 1322 | 1429 | 0.487 | 0.468 | 0.477 |
| 56 | 25 | 50 | 0.40 | 1233 | 1250 | 1453 | 0.497 | 0.459 | 0.477 |
| 57 | 25 | 50 | 0.60 | 1188 | 1002 | 1498 | 0.542 | 0.442 | 0.487 |
| 58 | 25 | 50 | 0.80 | 1060 | 735 | 1626 | 0.591 | 0.395 | 0.473 |
| 59 | 25 | 50 | 0.95 | 840 | 550 | 1846 | 0.604 | 0.313 | 0.412 |
| 60 | 25 | 100 | 0.00 | 1282 | 1304 | 1404 | 0.496 | 0.477 | 0.486 |
| 61 | 25 | 100 | 0.20 | 1276 | 1300 | 1410 | 0.495 | 0.475 | 0.485 |
| 62 | 25 | 100 | 0.40 | 1251 | 1169 | 1435 | 0.517 | 0.466 | 0.490 |
| 63 | 25 | 100 | 0.60 | 1192 | 973 | 1494 | 0.551 | 0.444 | 0.491 |
| 64 | 25 | 100 | 0.80 | 1075 | 732 | 1611 | 0.595 | 0.400 | 0.479 |
| 65 | 25 | 100 | 0.95 | 820 | 534 | 1866 | 0.606 | 0.305 | 0.406 |
| 66 | 25 | 200 | 0.00 | 1288 | 1298 | 1398 | 0.498 | 0.480 | 0.489 |
| 67 | 25 | 200 | 0.20 | 1285 | 1291 | 1401 | 0.499 | 0.478 | 0.488 |
| 68 | 25 | 200 | 0.40 | 1256 | 1123 | 1430 | 0.528 | 0.468 | 0.496 |
| 69 | 25 | 200 | 0.60 | 1182 | 965 | 1504 | 0.551 | 0.440 | 0.489 |
| 70 | 25 | 200 | 0.80 | 1106 | 747 | 1580 | 0.597 | 0.412 | 0.487 |
| 71 | 25 | 200 | 0.95 | 800 | 522 | 1886 | 0.605 | 0.298 | 0.399 |

### S3.3 Sensitivity Analysis: Parameter Effects

#### Effect of pr_filter on Precision-Recall Trade-off

Aggregated across all max_clique and max_solutions values:

| pr_filter | Mean Precision | Mean Recall | Mean F1 |
|-----------|---------------|-------------|---------|
| 0.00 | 0.579 | 0.426 | 0.487 |
| 0.20 | 0.584 | 0.426 | 0.488 |
| 0.40 | 0.601 | 0.420 | 0.491 |
| 0.60 | 0.630 | 0.404 | 0.490 |
| 0.80 | 0.697 | 0.379 | 0.488 |
| 0.95 | 0.728 | 0.288 | 0.409 |

The pr_filter parameter shows the strongest effect: increasing from 0.0 to 0.95 raises mean precision by 15 percentage points (0.579 → 0.728) while reducing mean recall by 14 points (0.426 → 0.288).

#### Effect of max_pfacts_per_clique

| max_clique | Mean F1 | Best F1 | Mean Precision | Mean Recall |
|-----------|---------|---------|----------------|-------------|
| 5 | 0.454 | 0.476 | 0.691 | 0.345 |
| 10 | 0.513 | 0.538 | 0.668 | 0.423 |
| 25 | 0.459 | 0.496 | 0.550 | 0.404 |

max_clique=10 provides the best balance. At 5, partitioning is too aggressive — entities are isolated from supporting context. At 25, larger partitions introduce more false positives.

## S4. Case Studies

### S4.1 Brain Ontology Alignment Pipeline

The brain ontology alignment benchmark follows a complete end-to-end pipeline:

1. **Ontology retrieval**: Six Allen Brain Atlas ontologies (EMAPA, HBA, DHBA, MBA, DMBA, PBA) retrieved via OAK from semsql SQLite databases
2. **OBO export**: Each ontology exported to simplified OBO format with is_a relationships and synonyms
3. **Knowledge base construction**: OBO files parsed into a BOOMER KB with 9,835 is_a relationships across all six ontologies
4. **Lexical matching**: Eight matching rules applied via OAK lexmatch, generating candidate EquivalentTo mappings with calibrated prior probabilities
5. **Ptable conversion**: Lexmatch SSSOM output converted to ptable format for BOOMER input
6. **Solving**: Grid search across 72 parameter configurations
7. **Evaluation**: Solutions compared against 2,688 ground truth equivalences from 1,288 UBERON cross-reference cliques

Ground truth derivation: UBERON contains cross-references (xrefs) to species-specific brain atlases. For each UBERON term with brain-related descendants, we extracted all xrefs to the six target ontologies and generated pairwise EquivalentTo facts within each clique.

The complete pipeline is documented in `analysis/brain/Prepare.ipynb` and `analysis/brain/Makefile`.

### S4.2 CL+BTO Cell Type Alignment

The Cell Ontology (CL) and BRENDA Tissue Ontology (BTO) alignment demonstrates module extraction for tractability:

1. **Input**: CL (19,026 terms) and BTO (6,566 terms) downloaded from OBO Foundry
2. **Label matching**: 856 candidate EquivalentTo mappings generated with prior=0.70
3. **Merging**: Combined KB with 90,474 hard facts and 32,861 pfacts
4. **Module extraction**: Neighborhood around CL:0000066 (epithelial cell) with --max-hops 1, yielding 345 facts and 50 pfacts
5. **Solving**: max_pfacts_per_clique=20, timeout=120s, partitioned into 29 sub-problems
6. **Results**: 49 accepted mappings, with posterior boosts up to 0.94 for structurally supported equivalences

The tutorial is documented in `docs/tutorial/real-world-alignment.ipynb`.

### S4.3 Cross-lingual Terminology Alignment

Alignment of medical terms across English, Spanish, and French:

Configuration:
```python
kb = KB(
    pfacts=[
        # High confidence for within-language synonyms
        PFact(EquivalentTo("heart", "cardiac_organ"), 0.95),
        PFact(EquivalentTo("coeur", "organe_cardiaque"), 0.95),
        PFact(EquivalentTo("corazón", "órgano_cardíaco"), 0.95),

        # Lower confidence for cross-language mappings
        PFact(EquivalentTo("heart", "coeur"), 0.85),
        PFact(EquivalentTo("heart", "corazón"), 0.85),
        PFact(EquivalentTo("coeur", "corazón"), 0.80),
    ],
    facts=[
        # Prevent same-language false equivalences
        MemberOfDisjointGroup("heart", "en"),
        MemberOfDisjointGroup("cardiac_organ", "en"),
        MemberOfDisjointGroup("coeur", "fr"),
        MemberOfDisjointGroup("organe_cardiaque", "fr"),
    ]
)
```

## S5. User Guide

### S5.1 Installation

```bash
# Using pip
pip install boomer-py

# Using uv (recommended)
uv add boomer

# Development installation
git clone https://github.com/username/boomer-py.git
cd boomer-py
uv sync
```

### S5.2 Python API Examples

#### Basic Usage

```python
from boomer.model import KB, PFact, EquivalentTo
from boomer.search import solve

# Create knowledge base
kb = KB(pfacts=[
    PFact(fact=EquivalentTo(sub="A", equivalent="B"), prob=0.9),
    PFact(fact=EquivalentTo(sub="B", equivalent="C"), prob=0.8),
])

# Solve with default configuration
solution = solve(kb)

# Access results
for spfact in solution.solved_pfacts:
    if spfact.truth_value:
        print(f"{spfact.pfact.fact}: {spfact.posterior_prob:.2f}")
```

#### Advanced Configuration

```python
from boomer.model import SearchConfig

config = SearchConfig(
    max_iterations=100000,
    timeout_seconds=30,
    partition_initial_threshold=50,
    max_pfacts_per_clique=25,
)

solution = solve(kb, config)
```

#### Custom Reasoning

```python
from boomer.reasoners import get_reasoner
from boomer.model import Grounding

# Get reasoner instance
reasoner = get_reasoner("boomer.reasoners.nx_reasoner.NxReasoner")

# Manual reasoning
selections = [(0, True), (1, False)]  # First fact true, second false
result = reasoner.reason(kb, selections)

print(f"Satisfiable: {result.satisfiable}")
print(f"Entailed: {result.entailed_selections}")
```

### S5.3 Command-Line Interface

#### Input Format Examples

**YAML Format:**
```yaml
pfacts:
  - fact:
      fact_type: EquivalentTo
      sub: term1
      equivalent: term2
    prob: 0.85
```

**TSV Format:**
```
EquivalentTo	term1	term2	0.85
ProperSubClassOf	term1	term3	0.90
```

#### Output Interpretation

The solution output includes:
- **Truth values**: Whether each fact is accepted (true) or rejected (false)
- **Posterior probabilities**: Updated probabilities after reasoning
- **Confidence score**: Certainty in the solution (0-1)
- **Statistics**: Number of combinations explored, time elapsed

### S5.4 Troubleshooting

Common issues and solutions:

1. **Out of memory**: Reduce `max_pfacts_per_clique` parameter
2. **Timeout**: Increase `timeout_seconds` or reduce KB size
3. **No solutions found**: Check for logical contradictions in facts
4. **Low confidence**: May indicate ambiguous or conflicting evidence

## S6. Future Work Details

### S6.1 Probabilistic Rule Support

Extending the model to support Horn rules with uncertainty:

```python
class ProbabilisticRule(BaseModel):
    """Rule: if (body) then (head) with probability."""
    body: List[Fact]
    head: Fact
    probability: float
```

### S6.2 Incremental Reasoning

Supporting dynamic KB updates:

```python
class IncrementalSolver:
    def __init__(self, kb: KB):
        self.kb = kb
        self.solution = solve(kb)
        self.cache = {}

    def add_fact(self, pfact: PFact) -> Solution:
        # Reuse previous solution as starting point
        # Only re-solve affected partitions
        affected_partitions = self.identify_affected(pfact)
        return self.partial_solve(affected_partitions)
```

### S6.3 Explanation Generation

Providing human-readable explanations for solutions:

```python
def explain_solution(solution: Solution, kb: KB) -> str:
    explanation = []
    for spfact in solution.solved_pfacts:
        if spfact.truth_value:
            # Find supporting evidence
            support = find_supporting_facts(spfact.pfact.fact, kb)
            explanation.append(
                f"{spfact.pfact.fact} accepted because:\n"
                f"  - Prior probability: {spfact.pfact.prob}\n"
                f"  - Supporting facts: {support}\n"
                f"  - No contradictions found"
            )
    return "\n".join(explanation)
```