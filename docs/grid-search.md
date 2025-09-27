# Grid Search

Grid search is a systematic method for finding optimal hyperparameters for BOOMER's probabilistic reasoning. It automatically explores different parameter combinations to identify the configuration that produces the best results.

## Overview

Grid search helps answer questions like:

- What's the optimal clique size limit for my knowledge base?
- How many candidate solutions should I explore?
- What timeout values give the best accuracy/performance trade-off?
- Which probability filters work best for my data?

## How Grid Search Works

1. **Define a parameter grid**: Specify which parameters to vary and their values
2. **Run BOOMER with each combination**: Systematically try all combinations
3. **Evaluate results**: Compare solutions using metrics like F1 score
4. **Select best configuration**: Identify the parameters that work best

## Grid Configuration Format

Grid search configurations use YAML or JSON to specify parameter combinations:

### Basic Structure

```yaml
# grid_config.yaml
configurations:
  - {}  # Base configuration (uses defaults)

configuration_matrix:
  max_pfacts_per_clique: [50, 100, 150]
  max_candidate_solutions: [100, 500, 1000]
  timeout_seconds: [10, 30, 60]
  pr_filter: [0.2, 0.5, 0.8]
```

This creates 3 × 3 × 3 × 3 = 81 different parameter combinations to test.

### Advanced Configuration

You can specify multiple base configurations with different defaults:

```yaml
configurations:
  # Conservative configuration
  - max_iterations: 10000
    max_candidate_solutions: 100

  # Aggressive configuration
  - max_iterations: 100000
    max_candidate_solutions: 1000

configuration_matrix:
  max_pfacts_per_clique: [100, 200]
  timeout_seconds: [30, 60]
```

This creates 2 base configs × 2 × 2 = 8 combinations.

## CLI Usage

### Basic Grid Search

```bash
# Run grid search on a knowledge base
boomer-cli grid-search kb.yaml grid_config.yaml -o results.json

# With evaluation against gold standard
boomer-cli grid-search kb.yaml grid_config.yaml \
  --eval-kb-file gold_standard.yaml \
  -o results.json

# Save intermediate results
boomer-cli grid-search kb.yaml grid_config.yaml \
  --eval-kb-file gold.yaml \
  --output-dir grid_results/ \
  -o final_results.json
```

### Input/Output Formats

```bash
# Different format combinations
boomer-cli grid-search kb.ptable.tsv grid.json \
  -e gold.json \
  -O yaml \
  -o results.yaml

# Explicit format specification
boomer-cli grid-search kb.data grid.data \
  --kb-format json \
  --grid-format yaml \
  --eval-kb-format ptable \
  -o results.json
```

## Python API

### Basic Usage

```python
from boomer.search import grid_search
from boomer.model import GridSearch, SearchConfig
from boomer.io import load_kb

# Load knowledge base
kb = load_kb('kb.yaml')

# Define grid search
grid = GridSearch(
    configurations=[SearchConfig()],  # Base config
    configuration_matrix={
        'max_pfacts_per_clique': [50, 100, 150],
        'max_candidate_solutions': [100, 500],
        'timeout_seconds': [10, 30]
    }
)

# Run grid search
results = grid_search(kb, grid)

# Find best configuration
best_result = max(results.results, key=lambda r: r.evaluation.f1 if r.evaluation else 0)
print(f"Best F1: {best_result.evaluation.f1}")
print(f"Best config: {best_result.search_config}")
```

### With Evaluation

```python
from boomer.search import grid_search
from boomer.io import load_kb

# Load KBs
kb = load_kb('kb.yaml')
gold_kb = load_kb('gold_standard.yaml')

# Run grid search with evaluation
grid = GridSearch(
    configurations=[SearchConfig()],
    configuration_matrix={
        'max_pfacts_per_clique': [100, 200],
        'timeout_seconds': [30, 60]
    }
)

results = grid_search(kb, grid, eval_kb=gold_kb)

# Analyze results
for result in results.results:
    if result.evaluation:
        print(f"Config: {result.search_config}")
        print(f"  Precision: {result.evaluation.precision:.3f}")
        print(f"  Recall: {result.evaluation.recall:.3f}")
        print(f"  F1 Score: {result.evaluation.f1:.3f}")
```

## Parameters to Optimize

### Core Search Parameters

**max_pfacts_per_clique**
- Controls computational complexity per clique
- Lower values: Faster but may prune important facts
- Higher values: More accurate but slower
- Typical range: 50-200

**max_candidate_solutions**
- Number of solution candidates to explore
- Lower values: Faster, may miss optimal solution
- Higher values: More thorough, slower
- Typical range: 100-1000

**timeout_seconds**
- Maximum time per solve operation
- Prevents runaway computations
- Typical range: 10-300 seconds

**max_iterations**
- Maximum search iterations
- Safety limit for complex KBs
- Typical range: 10,000-1,000,000

### Filtering Parameters

**pr_filter**
- Probability threshold for filtering low-probability facts
- Values: 0.0 (no filtering) to 1.0 (only certainties)
- Typical range: 0.1-0.8

## Evaluation Metrics

When a gold standard KB is provided, grid search calculates:

### Precision
Fraction of predicted facts that are correct:
```
Precision = True Positives / (True Positives + False Positives)
```

### Recall
Fraction of gold facts that were found:
```
Recall = True Positives / (True Positives + False Negatives)
```

### F1 Score
Harmonic mean of precision and recall:
```
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

## Output Format

Grid search results include all tested configurations and their outcomes:

```json
{
  "configurations": [{}],
  "configuration_matrix": {
    "max_pfacts_per_clique": [100, 150],
    "timeout_seconds": [30, 60]
  },
  "results": [
    {
      "search_config": {
        "max_pfacts_per_clique": 100,
        "timeout_seconds": 30,
        "max_candidate_solutions": 100
      },
      "solution": {
        "confidence": 0.923,
        "time_elapsed": 2.34
      },
      "evaluation": {
        "precision": 0.95,
        "recall": 0.88,
        "f1": 0.91,
        "true_positives": 88,
        "false_positives": 5,
        "false_negatives": 12
      }
    }
  ]
}
```

## Practical Examples

### Example 1: Optimizing for Speed

Find the fastest configuration that maintains acceptable accuracy:

```yaml
# speed_optimization.yaml
configurations:
  - {}

configuration_matrix:
  max_pfacts_per_clique: [30, 50, 70]  # Lower values for speed
  max_candidate_solutions: [50, 100]     # Fewer candidates
  timeout_seconds: [5, 10]               # Strict timeouts
  pr_filter: [0.3, 0.5, 0.7]            # Filter low-prob facts
```

### Example 2: Optimizing for Accuracy

Find the most accurate configuration regardless of speed:

```yaml
# accuracy_optimization.yaml
configurations:
  - {}

configuration_matrix:
  max_pfacts_per_clique: [150, 200, 300]  # Higher limits
  max_candidate_solutions: [500, 1000]     # More candidates
  timeout_seconds: [60, 120, 300]          # Generous timeouts
  pr_filter: [0.0, 0.1, 0.2]              # Minimal filtering
```

### Example 3: Balanced Optimization

Balance speed and accuracy:

```yaml
# balanced_optimization.yaml
configurations:
  - max_iterations: 100000

configuration_matrix:
  max_pfacts_per_clique: [75, 100, 125]
  max_candidate_solutions: [200, 300, 400]
  timeout_seconds: [20, 30, 40]
  pr_filter: [0.2, 0.3, 0.4]
```

## Analyzing Results

### Finding the Best Configuration

```python
import json
import pandas as pd

# Load results
with open('grid_results.json') as f:
    results = json.load(f)

# Convert to DataFrame for analysis
records = []
for r in results['results']:
    record = {
        'max_pfacts': r['search_config']['max_pfacts_per_clique'],
        'timeout': r['search_config']['timeout_seconds'],
        'f1': r['evaluation']['f1'] if r.get('evaluation') else 0,
        'time': r['solution']['time_elapsed']
    }
    records.append(record)

df = pd.DataFrame(records)

# Find best F1 score
best_f1 = df.loc[df['f1'].idxmax()]
print(f"Best F1 configuration: {best_f1}")

# Find fastest acceptable (F1 > 0.8)
acceptable = df[df['f1'] > 0.8]
fastest = acceptable.loc[acceptable['time'].idxmin()]
print(f"Fastest acceptable: {fastest}")
```

### Visualizing Trade-offs

```python
import matplotlib.pyplot as plt

# Plot F1 vs computation time
plt.scatter(df['time'], df['f1'])
plt.xlabel('Time (seconds)')
plt.ylabel('F1 Score')
plt.title('Accuracy vs Speed Trade-off')
plt.show()

# Plot parameter effects
fig, axes = plt.subplots(1, 2, figsize=(12, 4))

# Effect of clique size
axes[0].boxplot([df[df['max_pfacts'] == v]['f1']
                 for v in df['max_pfacts'].unique()])
axes[0].set_xlabel('Max PFacts per Clique')
axes[0].set_ylabel('F1 Score')

# Effect of timeout
axes[1].boxplot([df[df['timeout'] == v]['f1']
                 for v in df['timeout'].unique()])
axes[1].set_xlabel('Timeout (seconds)')
axes[1].set_ylabel('F1 Score')

plt.tight_layout()
plt.show()
```

## Best Practices

### 1. Start with Coarse Grid
Begin with widely spaced parameter values:
```yaml
max_pfacts_per_clique: [50, 100, 200]
```

Then refine around the best region:
```yaml
max_pfacts_per_clique: [80, 90, 100, 110, 120]
```

### 2. Use Representative Data
- Test on a subset that represents your full dataset
- Include both easy and difficult cases
- Ensure gold standard is high quality

### 3. Consider Multiple Metrics
- Don't optimize solely for F1 score
- Consider computation time for production use
- Monitor memory usage for large KBs

### 4. Document Results
Record:
- The grid configuration used
- The best parameters found
- The evaluation metrics achieved
- The dataset characteristics

### 5. Validate on Hold-out Data
- Don't use the same data for grid search and final evaluation
- Split your gold standard: 70% for grid search, 30% for validation
- Verify that optimal parameters generalize

## Troubleshooting

### Grid Search Takes Too Long

1. Reduce the parameter space:
   ```yaml
   # Instead of:
   max_pfacts_per_clique: [50, 75, 100, 125, 150]
   # Try:
   max_pfacts_per_clique: [50, 100, 150]
   ```

2. Use stricter timeouts:
   ```yaml
   timeout_seconds: [5, 10, 15]  # Instead of [30, 60, 120]
   ```

3. Test on a smaller KB subset first

### Poor F1 Scores Across All Configurations

1. Check your gold standard quality
2. Verify the KB and gold standard alignment
3. Consider if the problem is inherently difficult
4. Try wider parameter ranges

### Memory Issues

1. Reduce `max_pfacts_per_clique`
2. Limit `max_candidate_solutions`
3. Process large KBs in batches

## Advanced Usage

### Custom Evaluation Metrics

Implement custom scoring in your analysis:

```python
def custom_score(result):
    """Weighted score favoring precision over recall"""
    if not result.get('evaluation'):
        return 0
    eval = result['evaluation']
    # Weight precision 2x more than recall
    return (2 * eval['precision'] + eval['recall']) / 3

# Find best by custom metric
best = max(results['results'], key=custom_score)
```

### Parallel Grid Search

For large grids, parallelize the search:

```python
from concurrent.futures import ProcessPoolExecutor
from boomer.search import solve

def evaluate_config(kb, config):
    solution = solve(kb, config)
    return solution

configs = expand_grid(grid)  # Expand all combinations
with ProcessPoolExecutor() as executor:
    solutions = list(executor.map(
        lambda c: evaluate_config(kb, c),
        configs
    ))
```