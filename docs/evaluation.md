# Evaluation

BOOMER provides comprehensive evaluation capabilities to assess the quality of predicted facts against ground truth data. This is useful for benchmarking reasoner performance, testing hypothesis generation strategies, and comparing different search configurations.

## Core Concepts

### Evaluation Metrics

BOOMER computes standard classification metrics for fact prediction:

- **True Positives (TP)**: Facts correctly predicted that exist in ground truth
- **False Positives (FP)**: Facts predicted but not in ground truth
- **False Negatives (FN)**: Facts in ground truth but not predicted
- **Precision**: TP / (TP + FP) - measures accuracy of positive predictions
- **Recall**: TP / (TP + FN) - measures coverage of ground truth
- **F1-score**: Harmonic mean of precision and recall

### Fact Normalization

During evaluation, facts are normalized to ensure consistent comparison:
- `EquivalentTo` facts are canonicalized (entities sorted alphabetically)
- Duplicate facts are automatically deduplicated
- Facts can be filtered by type for focused evaluation

## Programmatic Evaluation

### Using the evaluate_facts Function

The `evaluate_facts` function in `boomer.evaluator` provides the core evaluation logic:

```python
from boomer.evaluator import evaluate_facts
from boomer.model import SubClassOf, EquivalentTo

# Define ground truth and predictions
gold_facts = [
    SubClassOf(sub="Cat", sup="Animal"),
    SubClassOf(sub="Dog", sup="Animal"),
    EquivalentTo(sub="Cat", equivalent="Feline")
]

predicted_facts = [
    SubClassOf(sub="Cat", sup="Animal"),  # True positive
    SubClassOf(sub="Bird", sup="Animal"),  # False positive
    # Missing Dog->Animal (False negative)
]

# Evaluate all facts
stats = evaluate_facts(gold_facts, predicted_facts)
print(f"Precision: {stats.precision:.2f}")
print(f"Recall: {stats.recall:.2f}")
print(f"F1: {stats.f1:.2f}")

# Evaluate only specific fact types
equiv_stats = evaluate_facts(
    gold_facts,
    predicted_facts,
    types=["EquivalentTo"]
)
```

### EvalStats Object

The evaluation returns an `EvalStats` object containing:

```python
class EvalStats:
    tp: int                    # Count of true positives
    fp: int                    # Count of false positives
    fn: int                    # Count of false negatives
    tp_list: list[Fact]        # Actual true positive facts
    fp_list: list[Fact]        # Actual false positive facts
    fn_list: list[Fact]        # Actual false negative facts
    precision: float           # Precision score
    recall: float              # Recall score
    f1: float                  # F1 score
```

## CLI Evaluation Commands

### evaluate Command

Evaluate a solution file against ground truth:

```bash
# Basic evaluation
uv run python -m boomer.cli evaluate ground_truth.json solution.json

# Filter by posterior probability threshold
uv run python -m boomer.cli evaluate ground_truth.yaml solution.yaml --pr-filter 0.8

# Evaluate only EquivalentTo facts
uv run python -m boomer.cli evaluate kb.json solution.json --equiv-only

# Specify formats explicitly
uv run python -m boomer.cli evaluate kb.yaml solution.json \
    --kb-format yaml --solution-format json
```

Output shows detailed metrics:
```
Evaluating 150 facts and 120 predicted facts; types: []
Evaluation results:
  True positives:  95
  False positives: 25
  False negatives: 55
  Precision:       0.7917
  Recall:          0.6333
  F1-score:        0.7037
```

### Grid Search with Evaluation

Grid search automatically evaluates each configuration when an evaluation KB is provided:

```bash
# Grid search with automatic evaluation
uv run python -m boomer.cli grid-search train.json grid_config.yaml \
    --eval-kb-file test.json \
    --output results.json

# Filter predictions by probability for evaluation
uv run python -m boomer.cli grid-search train.yaml grid.yaml \
    --eval-kb-file test.yaml \
    --pr-filters 0.5,0.7,0.9
```

The grid search results include evaluation metrics for each configuration:

```json
{
  "results": [
    {
      "config": {
        "max_hypotheses": 100,
        "alpha": 0.1
      },
      "evaluation": {
        "tp": 45,
        "fp": 10,
        "fn": 15,
        "precision": 0.818,
        "recall": 0.750,
        "f1": 0.783
      },
      "pr_filter": 0.7
    }
  ]
}
```

## Evaluation Strategies

### Reasoning Extension

BOOMER's evaluator automatically extends predictions through reasoning before comparison. This ensures that implied facts are considered:

```python
# If prediction contains A->B and B->C
# The evaluator will also consider A->C (transitivity)
# This prevents false negatives for logically entailed facts
```

### Type-Specific Evaluation

Focus evaluation on specific fact types to measure performance on particular reasoning tasks:

```python
# Evaluate only equivalence reasoning
stats = evaluate_facts(gold, predicted, types=["EquivalentTo"])

# Evaluate subclass and disjointness reasoning
stats = evaluate_facts(gold, predicted,
                      types=["SubClassOf", "DisjointWith"])
```

### Probability Thresholding

Filter predictions by posterior probability to find optimal confidence thresholds:

```python
# Test multiple thresholds
for threshold in [0.5, 0.7, 0.9]:
    filtered = [f for f in predictions
                if f.posterior_prob >= threshold]
    stats = evaluate_facts(gold, filtered)
    print(f"Threshold {threshold}: F1={stats.f1:.3f}")
```

## Best Practices

### Creating Evaluation Datasets

1. **Split your data**: Keep training and test sets separate
2. **Include diverse fact types**: Test all reasoning capabilities
3. **Add negative examples**: Include facts that should NOT be inferred
4. **Document assumptions**: Note any implicit knowledge required

### Interpreting Results

- **High precision, low recall**: Conservative predictions, missing some facts
- **Low precision, high recall**: Over-predicting, many false positives
- **Balanced F1**: Good overall performance
- **Check fact lists**: Examine `tp_list`, `fp_list`, `fn_list` for patterns

### Optimization Workflow

1. Start with grid search to find promising configurations
2. Analyze false positives/negatives to understand errors
3. Adjust hypothesis generation or probability thresholds
4. Re-evaluate on held-out test set

## Examples

### Evaluating Animal Ontology

```python
from boomer.datasets import animals
from boomer.reasoners import NxReasoner
from boomer.evaluator import evaluate_facts

# Load dataset and split
kb = animals.kb
train_facts = kb.facts[:50]
test_facts = kb.facts[50:]

# Run reasoning
reasoner = NxReasoner()
solution = reasoner.reason(KB(facts=train_facts))

# Extract predictions
predictions = [sp.pfact.fact for sp in solution.solved_pfacts
               if sp.truth_value and sp.posterior_prob > 0.7]

# Evaluate
stats = evaluate_facts(test_facts, predictions)
print(f"Animal ontology F1: {stats.f1:.3f}")
```

### Comparative Evaluation

```python
# Compare different reasoner configurations
configs = [
    {"alpha": 0.05, "beta": 0.01},
    {"alpha": 0.1, "beta": 0.05},
    {"alpha": 0.2, "beta": 0.1}
]

results = []
for config in configs:
    reasoner = NxReasoner(**config)
    solution = reasoner.reason(kb)
    predictions = extract_predictions(solution)
    stats = evaluate_facts(gold, predictions)
    results.append((config, stats))

# Find best configuration
best = max(results, key=lambda x: x[1].f1)
print(f"Best config: {best[0]} with F1={best[1].f1:.3f}")
```

## Related Documentation

- [Search Documentation](search.md) - Grid search and optimization
- [Grid Search Documentation](grid-search.md) - Detailed grid search usage
- [Datasets](../src/boomer/datasets/) - Example datasets for evaluation