# Brain Ontology Integration Benchmark

This directory contains a comprehensive benchmark for evaluating Boomer-Py's performance on neuroanatomical ontology integration tasks.

## Overview

The brain ontology benchmark tests the system's ability to:
- Integrate cross-species neuroanatomical terminologies (human vs mouse)
- Reconcile clinical terminology (SNOMED CT) with research ontologies (FMA, Allen Brain Atlas)
- Handle historical neuroanatomical terms and modern nomenclature
- Resolve conflicting expert annotations with varying confidence levels

## Files

- `brain_ontology_benchmark.py` - Main benchmark script with complete test suite
- `brain_benchmark_notebook.ipynb` - Interactive Jupyter notebook for exploration
- `README.md` - This file

## Running the Benchmark

### Command Line

```bash
cd analysis
python brain_ontology_benchmark.py
```

This will:
1. Create a brain ontology knowledge base with ~30 probabilistic mappings
2. Run the Boomer-Py solver with optimized partitioning
3. Evaluate results against ground truth
4. Perform scalability analysis
5. Generate detailed reports

### Jupyter Notebook

```bash
jupyter notebook brain_benchmark_notebook.ipynb
```

The notebook provides:
- Interactive exploration of the knowledge base
- Visualization of ontology structure and mapping confidence
- Step-by-step solution analysis
- Performance profiling and scalability plots

## Benchmark Components

### 1. Knowledge Base Structure

The benchmark KB includes:

**Human Brain Anatomy (FMA-based)**
- Hierarchical structure from brain → forebrain → telencephalon → cortical regions
- Major lobes: frontal, temporal, parietal, occipital
- Subcortical structures: hippocampus, amygdala

**Mouse Brain Anatomy (Allen Brain Atlas)**
- Corresponding mouse brain hierarchy
- Isocortex and specialized areas
- Hippocampal formation and amygdalar nuclei

**Clinical Terminology (SNOMED CT)**
- Clinical terms for brain structures
- Mappings to research terminology

**Probabilistic Mappings**
- High-confidence homologies (e.g., human hippocampus ≡ mouse hippocampal formation: 0.92)
- Moderate confidence clinical mappings (e.g., human frontal lobe ≡ frontal lobe structure: 0.82)
- Lower confidence regional mappings (e.g., human frontal lobe ≡ mouse frontal pole: 0.65)
- Potentially incorrect mappings with low probability

### 2. Evaluation Metrics

The benchmark evaluates:

**Performance Metrics**
- Execution time
- Combinations explored vs search space size
- Memory usage
- Partitioning effectiveness

**Solution Quality**
- Confidence score
- Precision/Recall/F1 against ground truth
- Number of accepted/rejected/uncertain mappings

**Scalability Analysis**
- Performance with increasing KB sizes (10-50 pfacts)
- Effect of partitioning thresholds
- Timeout behavior

### 3. Ground Truth

Expert-validated mappings include:
- Cross-species homologies based on developmental and functional correspondence
- Clinical terminology alignments from standard terminologies
- Historical term mappings from neuroanatomy literature

## Results Interpretation

### Expected Outcomes

A successful run should show:
- **High confidence** (>90%) in core cross-species homologies
- **Rejection** of anatomically implausible mappings
- **Execution time** under 5 seconds for the base KB (~30 pfacts)
- **Precision/Recall** >85% against ground truth

### Key Mappings to Verify

Critical mappings that should be accepted:
1. `human_cerebral_cortex ≡ mouse_isocortex` (evolutionary homology)
2. `human_hippocampus ≡ mouse_hippocampal_formation` (functional correspondence)
3. `neocortex ≡ human_cerebral_cortex` (historical terminology)

Mappings that should be rejected:
1. `human_frontal_lobe ≡ mouse_visual_areas` (incorrect regional mapping)
2. `human_hippocampus ≡ mouse_frontal_pole` (anatomically implausible)

## Extending the Benchmark

### Adding New Test Cases

To add new anatomical structures or mappings:

```python
# In brain_ontology_benchmark.py
additional_pfacts = [
    PFact(fact=EquivalentTo(sub="new_structure", equivalent="mapped_term"), prob=0.75),
    # Add more mappings...
]
kb.pfacts.extend(additional_pfacts)
```

### Customizing Search Configuration

Adjust parameters for different trade-offs:

```python
config = SearchConfig(
    max_iterations=200000,        # More thorough search
    timeout_seconds=120,           # Longer timeout
    partition_initial_threshold=20,  # Earlier partitioning
    max_pfacts_per_clique=15,     # Smaller partitions
)
```

## Benchmark Statistics

### Base Configuration
- **Entities**: ~40 neuroanatomical terms
- **Deterministic facts**: ~30 subsumption and disjointness constraints
- **Probabilistic facts**: ~30 uncertain mappings
- **Search space**: 2^30 ≈ 1 billion combinations
- **Typical exploration**: <10,000 combinations with partitioning

### Extended Configuration
- **Additional pfacts**: +20 functional and cellular mappings
- **Search space**: 2^50 ≈ 10^15 combinations
- **Partitions**: 10-15 independent components
- **Typical execution**: 10-30 seconds

## Publications and References

This benchmark is based on neuroanatomical ontologies from:
- **FMA**: Foundational Model of Anatomy (University of Washington)
- **Allen Brain Atlas**: Allen Institute for Brain Science
- **SNOMED CT**: SNOMED International
- **NeuroLex**: Neuroscience Information Framework

Cross-species homologies based on:
- Comparative neuroanatomy literature
- Allen Institute cross-species mapping projects
- Expert curation from neuroanatomists

## Contact

For questions about the benchmark or to contribute additional test cases, please open an issue in the Boomer-Py repository.