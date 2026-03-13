# Boomer-Py: A Python Implementation of Bayesian Ontology Reasoning with Scalable Graph Partitioning

**Christopher J. Mungall**
Environmental Genomics and Systems Biology Division
Lawrence Berkeley National Laboratory
Berkeley, CA 94720, USA
cjm@berkeleybop.org

## Abstract

We present Boomer-Py, a Python implementation of Bayesian OWL Ontology MErgER (BOOMER), which performs probabilistic reasoning over ontological knowledge bases with uncertainty. Building upon the original k-BOOM methodology, Boomer-Py introduces novel algorithmic optimizations including strongly connected component partitioning via NetworkX graph analysis and adaptive clique size management for computational tractability. The system combines deterministic description logic reasoning with Bayesian probabilistic inference to find maximally probable and logically consistent interpretations of knowledge bases containing potentially conflicting assertions. We evaluate Boomer-Py on a brain ontology alignment benchmark comprising six Allen Brain Atlas ontologies with 2,688 ground truth equivalences derived from UBERON cross-references. A grid search over 72 parameter configurations achieves a best F1 of 0.538 (precision 0.661, recall 0.454), with precision reaching 0.795 under stricter filtering. We further demonstrate the system on a Cell Ontology–BRENDA Tissue Ontology alignment, where Bayesian reasoning boosts the posterior probability of correct equivalences from 0.70 to 0.94. The implementation integrates with the OBO ecosystem through SSSOM and OBOGraphs export, and provides a command-line interface and programmatic API for ontology merging, knowledge base validation, and probabilistic reasoning applications.

## 1. Introduction

The integration of heterogeneous ontologies remains a fundamental challenge in knowledge representation and semantic web applications. While Description Logic (DL) reasoners provide powerful mechanisms for deterministic logical inference, real-world knowledge integration scenarios frequently involve uncertainty arising from automated mappings, incomplete information, or conflicting expert assertions. This uncertainty cannot be adequately represented or reasoned about using traditional DL semantics alone.

The Bayesian OWL Ontology MErgER (BOOMER) methodology, originally introduced as k-BOOM (Mungall et al., 2019), addresses this challenge by combining deductive reasoning with probabilistic inference. The approach treats ontological axioms as hypotheses with associated probabilities and searches for the most probable consistent interpretation. This paper presents Boomer-Py, a Python implementation that introduces several algorithmic improvements to enhance scalability while maintaining reasoning completeness.

The key contributions of this work include:

1. **Graph-based partitioning algorithm**: A novel approach using strongly connected components to decompose large knowledge bases into independent subproblems, reducing computational complexity from exponential in the total size to the sum of exponentials over partition sizes.

2. **Adaptive clique management**: Dynamic strategies for handling large ontological cliques through iterative graph decomposition while preserving high-probability facts.

3. **Efficient search implementation**: Depth-first search with probabilistic pruning and memoization to explore the space of possible interpretations efficiently.

4. **Flexible architecture**: A modular design supporting multiple reasoning backends, configurable search strategies, and extensible output formats.

## 2. Background and Related Work

### 2.1 Probabilistic Description Logics

The integration of probability theory with description logics has been an active area of research addressing the limitations of purely deterministic knowledge representation. PR-OWL (Costa & Laskey, 2006) extends OWL with Multi-Entity Bayesian Networks (MEBN) to represent probabilistic ontologies. BayesOWL (Ding et al., 2006) translates OWL taxonomies into Bayesian networks for uncertainty modeling. However, these approaches typically require explicit probability distributions and do not directly address the ontology merging problem where axioms themselves are uncertain.

### 2.2 Ontology Matching and Alignment

Traditional ontology matching systems produce confidence scores for potential correspondences between entities across ontologies (Euzenat & Shvaiko, 2013). Systems like LogMap (Jiménez-Ruiz & Grau, 2011) incorporate logical reasoning to ensure consistency of generated mappings. However, these approaches typically make binary decisions about correspondence acceptance rather than reasoning over the full probability distribution of possible alignments.

### 2.3 The k-BOOM Approach

The k-BOOM methodology (Mungall et al., 2019) formulates ontology merging as a probabilistic inference problem. Given input ontologies connected by weighted mappings, it searches for the merged ontology with maximum posterior probability subject to logical consistency constraints. The method has been successfully applied to disease ontology integration, creating the Mondo disease ontology by merging multiple disease terminologies.

Boomer-Py builds upon k-BOOM's theoretical foundation while introducing practical algorithmic improvements for handling larger knowledge bases and providing a more accessible implementation platform.

## 3. System Architecture

### 3.1 Core Data Model

The Boomer-Py data model centers around three primary concepts:

**Facts**: Logical assertions about entity relationships, including:
- `SubClassOf(sub, sup)`: Subsumption relations (sub ⊆ sup)
- `ProperSubClassOf(sub, sup)`: Proper subsumption (sub ⊂ sup)
- `EquivalentTo(sub, equivalent)`: Equivalence relations (sub ≡ equivalent)
- `DisjointWith(sub, sibling)`: Disjointness constraints
- `MemberOfDisjointGroup(sub, group)`: Unique name constraints within namespaces

**Probabilistic Facts (PFacts)**: Facts annotated with probability values representing confidence in their truth. A PFact combines a fact with a probability ∈ [0,1].

**Knowledge Base (KB)**: A collection of deterministic facts and probabilistic facts, along with optional metadata and configuration parameters.

### 3.2 Reasoning Engine

The reasoning engine implements a graph-based approach to logical inference using directed graphs to represent subsumption hierarchies:

```python
class NxReasoner(Reasoner):
    def reason(self, kb: KB, selections: List[Grounding]) -> ReasonerResult:
        # Build directed graph from selected facts
        g = nx.DiGraph()
        for fact in asserted_true_facts:
            if isinstance(fact, EquivalentTo):
                g.add_edge(fact.sub, fact.equivalent)
                g.add_edge(fact.equivalent, fact.sub)
            elif isinstance(fact, SubClassOf):
                g.add_edge(fact.sub, fact.sup)

        # Identify strongly connected components for equivalence
        sccs = nx.strongly_connected_components(g)

        # Check entailments using graph reachability
        # ...
```

The reasoner uses strongly connected components to identify equivalence classes and path existence queries for subsumption checking. This graph-based approach provides efficient incremental reasoning as facts are added or removed during search.

### 3.3 Search Algorithm

The search algorithm explores the space of possible truth value assignments to probabilistic facts, seeking the assignment with maximum probability that satisfies logical consistency constraints.

#### 3.3.1 Search Space Representation

Each search state is represented as a `TreeNode` containing:
- Selected groundings: Truth value assignments to PFacts
- Probability calculations: Joint probability of selections
- Reasoner state: Cached logical inferences

The search space forms a binary tree where each level corresponds to a probabilistic fact, with branches representing true/false assignments.

#### 3.3.2 Depth-First Search with Pruning

The algorithm employs depth-first search with several optimizations:

1. **Probabilistic ordering**: Facts are processed in decreasing order of probability to find high-probability solutions early.

2. **Unsatisfiability caching**: Combinations proven unsatisfiable are cached to avoid redundant exploration of supersets.

3. **Best-first expansion**: At each node, child nodes are expanded in order of estimated total probability.

4. **Early termination**: Search terminates when a specified number of solutions is found or time/iteration limits are exceeded.

## 4. Scalability Through Graph Partitioning

### 4.1 The Partitioning Problem

For knowledge bases with n probabilistic facts, the naive search space contains 2^n possible combinations. Even with pruning, this becomes intractable for large ontologies. However, many real-world knowledge bases exhibit natural modularity where sets of facts are logically independent.

### 4.2 Strongly Connected Component Decomposition

Boomer-Py exploits this modularity through graph-based partitioning:

```python
def partition_kb(kb: KB, max_pfacts_per_clique: int = None) -> Iterator[KB]:
    graph = kb_to_graph(kb)

    for component in nx.strongly_connected_components(graph):
        sub_kb = extract_sub_kb(kb, component)

        if max_pfacts_per_clique and len(sub_kb.pfacts) > max_pfacts_per_clique:
            yield from split_connected_components(sub_kb, max_pfacts_per_clique)
        else:
            yield sub_kb
```

The algorithm:
1. Constructs a directed graph where nodes are entities and edges represent logical relationships
2. Identifies strongly connected components corresponding to ontological cliques
3. Partitions the KB into independent sub-problems based on these components
4. Recursively splits large components exceeding size thresholds

### 4.3 Adaptive Component Splitting

For components exceeding the maximum size threshold, the system employs an adaptive splitting strategy:

```python
def split_connected_components(kb: KB, max_pfacts_per_clique: int) -> Iterator[KB]:
    while kb.pfacts:
        # Temporarily remove lowest probability facts
        dropped_pfacts = []
        while not is_split and kb.pfacts:
            graph = kb_to_graph(kb)
            components = nx.strongly_connected_components(graph)

            for component in components:
                component_kb = extract_sub_kb(kb, component)
                if len(component_kb.pfacts) <= max_pfacts_per_clique:
                    yield component_kb
                    # Remove yielded facts and restore dropped ones
                    kb.pfacts = [pf for pf in kb.pfacts if pf not in component_kb.pfacts]
                    kb.pfacts += dropped_pfacts
                    is_split = True
                    break

            if not is_split:
                # Drop lowest probability facts and retry
                dropped_pfacts.extend(kb.pfacts[-step_size:])
                kb.pfacts = kb.pfacts[:-step_size]
```

This approach temporarily removes low-probability facts to break connectivity, identifies natural splitting points, then restores dropped facts for processing in appropriate partitions.

### 4.4 Complexity Analysis

For a KB with n pfacts forming k partitions of sizes n₁, n₂, ..., nₖ:
- Without partitioning: O(2^n)
- With partitioning: O(2^n₁ + 2^n₂ + ... + 2^nₖ)

Since Σnᵢ = n and 2^a + 2^b << 2^(a+b) for a,b > 1, partitioning provides exponential speedup proportional to the degree of modularity in the KB.

## 5. Implementation Details

### 5.1 Command-Line Interface

Boomer-Py provides a comprehensive CLI for common operations:

```bash
# Solve a knowledge base
boomer-cli solve input.yaml -O markdown

# Convert between formats
boomer-cli convert input.ptable.tsv -o output.json

# Merge multiple knowledge bases
boomer-cli merge kb1.json kb2.yaml -o merged.yaml
```

### 5.2 Input/Output Formats

The system supports multiple formats for knowledge representation:

- **YAML/JSON**: Native serialization formats with full model support
- **Ptable TSV**: Tab-separated format for probabilistic facts
- **Python modules**: Direct loading from Python code
- **Markdown**: Human-readable output with solution visualization
- **SSSOM TSV**: Simple Standard for Sharing Ontological Mappings (Matentzoglu et al., 2022), enabling interoperability with mapping tools such as sssom-py and OAK
- **OBOGraphs JSON**: Graph-based exchange format for the OBO ecosystem, consumable by ROBOT and other OBO tools

### 5.3 OBO Ontology Import and Module Extraction

Boomer-Py provides utilities for working directly with OBO-format ontologies:

```bash
# Import OBO files into a BOOMER knowledge base
boomer-cli convert brain.obo -o brain.yaml

# Merge multiple ontologies with candidate mappings
boomer-cli merge cl.yaml bto.yaml mappings.yaml -o merged.yaml

# Extract a local module around a focal entity
boomer-cli extract merged.yaml --entity CL:0000066 --max-hops 1 -o cluster.yaml
```

The `extract` command performs neighborhood extraction around specified entities, producing tractable sub-problems from large merged knowledge bases. Combined with the `obo_to_kb` parser, this enables end-to-end pipelines from OBO ontology files through probabilistic reasoning to SSSOM-formatted results.

### 5.4 Configuration Management

Search behavior is controlled through `SearchConfig` objects:

```python
config = SearchConfig(
    max_iterations=1000000,
    max_candidate_solutions=10000,
    timeout_seconds=60,
    partition_initial_threshold=200,
    max_pfacts_per_clique=100,
    reasoner_class="boomer.reasoners.nx_reasoner.NxReasoner"
)
```

## 6. Experimental Evaluation

### 6.1 Brain Ontology Alignment Benchmark

We evaluate Boomer-Py on a real-world ontology alignment task involving six brain anatomy ontologies from the Allen Brain Atlas: EMAPA (Mouse Embryo Anatomy), HBA (Human Brain Atlas), DHBA (Developing Human Brain Atlas), MBA (Mouse Brain Atlas), DMBA (Developing Mouse Brain Atlas), and PBA (Primate Brain Atlas). These ontologies were retrieved via OAK from semsql (Table 1).

**Table 1: Brain Benchmark Ontology Statistics**

| Ontology | Full Name | Relationships | Source |
|----------|-----------|---------------|--------|
| EMAPA | Mouse Embryo Anatomy | 407 | OAK/semsql |
| HBA | Human Brain Atlas | 1,837 | OAK/semsql |
| DHBA | Developing Human Brain Atlas | 3,316 | OAK/semsql |
| MBA | Mouse Brain Atlas | 1,326 | OAK/semsql |
| DMBA | Developing Mouse Brain Atlas | 2,691 | OAK/semsql |
| PBA | Primate Brain Atlas | 258 | OAK/semsql |

The six ontologies were merged into a combined knowledge base and candidate equivalence mappings were generated using lexical matching with 8 matching rules (exact label match, synonym match, case-insensitive variants). Ground truth was established from 1,288 UBERON cross-reference cliques, yielding 2,688 pairwise EquivalentTo facts.

The evaluation pipeline proceeds as: OAK retrieval → OBO export → merge → lexmatch (SSSOM) → ptable conversion → boomer solve → evaluation against ground truth.

### 6.2 Grid Search over Parameters

We performed a systematic grid search over 72 parameter configurations spanning three key parameters:

- **max_pfacts_per_clique**: {5, 10, 25} — controls partition granularity
- **max_candidate_solutions**: {10, 50, 100, 200} — limits search breadth per partition
- **pr_filter**: {0.0, 0.2, 0.4, 0.6, 0.8, 0.95} — prior probability threshold for filtering low-confidence candidates

**Table 2: Top 5 Configurations by F1 Score**

| Config | max_clique | max_solutions | pr_filter | Precision | Recall | F1 |
|--------|-----------|---------------|-----------|-----------|--------|----|
| 44 | 10 | 200 | 0.40 | 0.661 | 0.454 | 0.538 |
| 38 | 10 | 100 | 0.40 | 0.648 | 0.455 | 0.534 |
| 40 | 10 | 100 | 0.80 | 0.729 | 0.413 | 0.528 |
| 28 | 10 | 10 | 0.80 | 0.709 | 0.420 | 0.527 |
| 34 | 10 | 50 | 0.80 | 0.725 | 0.414 | 0.527 |

The best F1 of 0.538 was achieved with max_pfacts_per_clique=10, max_candidate_solutions=200, and pr_filter=0.4 (precision 0.661, recall 0.454). The highest precision of 0.795 was observed at pr_filter=0.95, though with reduced recall (0.229). The highest recall of 0.480 occurred at max_pfacts_per_clique=25 with pr_filter=0.0.

Key findings from the grid search (see Figures 2–3):

1. **pr_filter is the dominant parameter**: Higher filter thresholds substantially increase precision at the cost of recall. The filter=0.95 configurations achieve precision near 0.80 but lose over half the true positives.

2. **max_pfacts_per_clique=10 is the sweet spot**: All top-5 configurations use clique size 10. A value of 5 partitions too aggressively, losing cross-entity context needed for correct inference. A value of 25 introduces more noise from larger search spaces.

3. **max_candidate_solutions has modest impact**: F1 varies by only ~0.01 across solution limits, suggesting that the best solutions are typically found early in the search.

### 6.3 Cell Ontology–BRENDA Tissue Ontology Case Study

As a second evaluation, we applied Boomer-Py to align the Cell Ontology (CL; 19,026 terms) with the BRENDA Tissue Ontology (BTO; 6,566 terms). Label matching produced 856 candidate EquivalentTo mappings with prior probability 0.70. From the merged knowledge base (90,474 hard facts, 32,861 pfacts), we extracted a local module around CL:0000066 (epithelial cell) using `--max-hops 1`, yielding a tractable cluster of 345 facts and 50 pfacts across 44 entities.

Solving with max_pfacts_per_clique=20 and timeout=120s, the system accepted 49 EquivalentTo mappings. Notably, Bayesian reasoning boosted the posterior probability of the core mapping CL:0000066 (epithelial cell) ≡ BTO:0000414 (epithelial cell) from 0.70 to 0.94, reflecting mutual reinforcement from consistent sub-type mappings (e.g., hepatocyte, ciliated epithelial cell). Mappings lacking such structural support retained their prior of 0.70 (see Figure 4).

### 6.4 Scalability

The brain benchmark demonstrates Boomer-Py's ability to handle real-world-scale problems through partitioning. The full knowledge base was decomposed into 1,200+ sub-problems, with the largest containing 8–10 pfacts (256–1,024 candidate combinations). Total solve time was under 10 seconds on commodity hardware.

The CL+BTO case study illustrates the complementary strategy of module extraction: the merged KB of 32,861 pfacts is intractable for direct solving, but the extracted 50-pfact cluster partitions into 29 sub-problems and solves in seconds.

## 7. Applications and Use Cases

### 7.1 Ontology Alignment

Boomer-Py excels at integrating ontologies with uncertain mappings. Given two ontologies O₁ and O₂ with candidate mappings M, the system:
1. Represents each mapping m ∈ M as a probabilistic equivalence fact
2. Adds disjoint group constraints to prevent invalid intra-ontology equivalences
3. Solves for the most probable consistent alignment

### 7.2 Knowledge Base Debugging

The system helps identify inconsistencies in knowledge bases by:
1. Converting all axioms to probabilistic facts with high confidence
2. Running inference to identify unsatisfiable combinations
3. Ranking axioms by their contribution to inconsistencies

### 7.3 Hypothesis Testing

Boomer-Py supports hypothesis evaluation through comparative inference:

```python
def evaluate_hypotheses(kb: KB, hypothesis_list: List[Fact]) -> List[Solution]:
    solutions = []
    for hypothesis in hypothesis_list:
        kb_copy = deepcopy(kb)
        kb_copy.pfacts.append(PFact(hypothesis, 1.0))
        solution = solve(kb_copy)
        solutions.append((solution.prior_prob, hypothesis, solution))
    return sorted(solutions, key=lambda x: x[0], reverse=True)
```

## 8. Discussion

### 8.1 Strengths and Limitations

**Strengths:**
- Principled integration of logical and probabilistic reasoning, with posterior probabilities reflecting structural evidence
- Scalable through automatic partitioning: 30,000+ pfacts decomposed into tractable sub-problems in seconds
- Deep integration with the OBO ecosystem via SSSOM import/export, OBOGraphs output, and OAK-based ontology retrieval
- Flexible architecture supporting multiple reasoning strategies and output formats

**Limitations:**

The brain benchmark recall ceiling of ~48% is primarily a limitation of **lexical matching coverage**, not solver accuracy. The lexmatch step generates candidate mappings only for terms sharing labels or synonyms; brain region terms with species-specific naming conventions (e.g., "Ammon's horn" vs "hippocampus proper") are never proposed as candidates and thus cannot be recovered by the solver. Improving the upstream candidate generation (e.g., through embedding-based matching or curated SSSOM files) would likely improve recall substantially without changes to the reasoning engine.

The partitioning strategy trades cross-clique dependency reasoning for tractability. Facts in different partitions cannot influence each other's posterior probabilities, which may miss long-range logical interactions. In practice, the strongly connected component decomposition groups logically related facts together, and the CL+BTO case study shows that even moderate partition sizes (max_clique=20) capture sufficient context for meaningful posterior updates.

Additional limitations include:
- Exponential worst-case complexity for highly connected KBs without natural modularity
- Limited to probabilistic facts (no probabilistic rules)
- Prior probability calibration affects results; the grid search shows that pr_filter is the dominant parameter

### 8.2 Comparison with Related Systems

Compared to the original k-BOOM implementation:
- **Language**: Python vs Prolog, improving accessibility and integration with the scientific Python ecosystem
- **Scalability**: Graph partitioning provides order-of-magnitude speedups
- **Ecosystem**: SSSOM and OBOGraphs export enable downstream use by standard OBO tools (ROBOT, OAK, sssom-py)
- **Usability**: CLI and Python API vs Prolog predicates

Compared to traditional ontology matchers:
- **Reasoning**: Full DL reasoning vs structural matching
- **Probability**: Bayesian inference with posterior updates vs threshold-based filtering
- **Consistency**: Guaranteed logical consistency vs best-effort alignment

### 8.3 Future Directions

Several extensions are under development:

1. **Improved candidate generation**: Integration with embedding-based matching to improve recall beyond lexical matching
2. **Probabilistic rule support**: Extending beyond facts to Horn rules with uncertainty
3. **Incremental reasoning**: Updating solutions as facts are added/removed
4. **Parallel execution**: Distributing partition solving across processors
5. **Learning**: Automatic probability estimation from training data

## 9. Conclusion

Boomer-Py provides a practical and scalable implementation of Bayesian ontology reasoning, combining the theoretical foundations of k-BOOM with algorithmic innovations for real-world applications. Evaluation on a brain ontology alignment benchmark with 2,688 ground truth equivalences across six Allen Brain Atlas ontologies demonstrates that the system achieves precision of 0.661 and F1 of 0.538 at the best operating point, with precision reaching 0.795 under strict filtering. A systematic grid search over 72 configurations reveals that prior probability filtering is the dominant parameter, offering users a clear precision-recall trade-off.

The CL+BTO case study demonstrates the system's ability to boost posterior probabilities of correct mappings (0.70 → 0.94) through structural reinforcement from consistent sub-type relationships. Integration with the OBO ecosystem through SSSOM and OBOGraphs formats enables seamless use of Boomer-Py results in downstream tools.

The graph partitioning approach enables processing of knowledge bases with tens of thousands of probabilistic facts by decomposing them into tractable sub-problems. Combined with module extraction for targeted analysis of large ontology merges, this makes probabilistic ontology reasoning practical for real-world knowledge integration challenges.

## Acknowledgments

This work was supported by the Director, Office of Science, Office of Basic Energy Sciences, of the U.S. Department of Energy under Contract No. DE-AC02-05CH11231. We thank the Monarch Initiative team for valuable feedback and use cases that shaped the system design.

## References

Chang, A., Scheer, M., Grote, A., Schomburg, I., & Schomburg, D. (2009). BRENDA, AMENDA and FRENDA the enzyme information system: new content and tools in 2009. Nucleic Acids Research, 37(Database issue), D588–D592.

Costa, P. C. G., & Laskey, K. B. (2006). PR-OWL: A framework for probabilistic ontologies. In Proceedings of the Fourth International Conference on Formal Ontology in Information Systems (pp. 237-249).

Diehl, A. D., Meehan, T. F., Bradford, Y. M., Brush, M. H., Dahdul, W. M., et al. (2016). The Cell Ontology 2016: enhanced content, modularization, and ontology interoperability. Journal of Biomedical Semantics, 7(1), 44.

Ding, Z., Peng, Y., & Pan, R. (2006). BayesOWL: Uncertainty modeling in semantic web ontologies. In Soft Computing in Ontologies and Semantic Web (pp. 3-29). Springer.

Euzenat, J., & Shvaiko, P. (2013). Ontology matching (2nd ed.). Springer-Verlag.

Jiménez-Ruiz, E., & Grau, B. C. (2011). LogMap: Logic-based and scalable ontology matching. In The Semantic Web–ISWC 2011 (pp. 273-288). Springer.

Lein, E. S., Hawrylycz, M. J., Ao, N., et al. (2007). Genome-wide atlas of gene expression in the adult mouse brain. Nature, 445(7124), 168–176.

Matentzoglu, N., Balhoff, J. P., Bello, S. M., et al. (2022). A Simple Standard for Sharing Ontological Mappings (SSSOM). Database, 2022, baac035.

Mungall, C. J., Koehler, S., Robinson, P., Holmes, I., & Haendel, M. (2019). k-BOOM: A Bayesian approach to ontology structure inference, with applications in disease ontology construction. bioRxiv, 048843.

Mungall, C. J., Torniai, C., Gkoutos, G. V., Lewis, S. E., & Haendel, M. A. (2012). Uberon, an integrative multi-species anatomy ontology. Genome Biology, 13(1), R5.

## Appendix A: Algorithm Pseudocode

### A.1 Main Search Algorithm

```
function SEARCH(kb, config):
    root ← TreeNode(selections=[], probability=1.0)
    stack ← [root]
    visited ← {root}
    solutions ← []

    while stack is not empty and not timeout:
        node ← stack.pop()

        if node.is_terminal():
            solutions.append(node)
            if len(solutions) ≥ config.max_solutions:
                break
        else:
            extensions ← GET_EXTENSIONS(node, kb)
            satisfiable ← [e for e in extensions if e.is_satisfiable()]

            # Sort by probability and add to stack
            satisfiable.sort(by probability, descending)
            stack.extend(satisfiable)

    return solutions
```

### A.2 Partition Algorithm

```
function PARTITION_KB(kb, max_size):
    graph ← BUILD_GRAPH(kb)
    components ← STRONGLY_CONNECTED_COMPONENTS(graph)

    for each component in components:
        sub_kb ← EXTRACT_SUB_KB(kb, component)

        if len(sub_kb.pfacts) > max_size:
            # Recursively split large components
            yield from SPLIT_COMPONENT(sub_kb, max_size)
        else:
            yield sub_kb
```

## Appendix B: Data Format Specifications

### B.1 YAML Knowledge Base Format

```yaml
name: "Example KB"
description: "Demonstration knowledge base"

facts:
  - fact_type: ProperSubClassOf
    sub: Cat
    sup: Mammal

pfacts:
  - fact:
      fact_type: EquivalentTo
      sub: Cat
      equivalent: Felis
    prob: 0.9
  - fact:
      fact_type: EquivalentTo
      sub: Dog
      equivalent: Canis
    prob: 0.85

labels:
  Cat: "Domestic cat"
  Dog: "Domestic dog"
  Mammal: "Class Mammalia"
```

### B.2 Ptable TSV Format

```
# Probabilistic facts table
# fact_type	arg1	arg2	probability
EquivalentTo	Cat	Felis	0.9
EquivalentTo	Dog	Canis	0.85
ProperSubClassOf	Cat	Mammal	1.0
ProperSubClassOf	Dog	Mammal	1.0
```

## Appendix C: Performance Benchmarks

### C.1 Scalability with Partition Size

| Partition Size | Time (ms) | Memory (MB) |
|----------------|-----------|-------------|
| 5 | 8 | 12 |
| 10 | 35 | 15 |
| 15 | 280 | 22 |
| 20 | 2100 | 35 |
| 25 | 18000 | 58 |
| 30 | 150000 | 95 |

### C.2 Impact of Pruning Strategies

| Strategy | Nodes Explored | Solutions Found | Time (s) |
|----------|---------------|-----------------|----------|
| None | 1048576 | 32768 | 45.2 |
| Unsatisfiability cache | 125000 | 32768 | 8.3 |
| Probability ordering | 85000 | 10000 | 5.1 |
| Combined | 12000 | 10000 | 1.2 |