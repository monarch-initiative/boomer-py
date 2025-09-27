"""
Brain Ontology Integration Benchmark

This benchmark evaluates Boomer-Py's ability to integrate multiple brain ontologies
and neuroanatomical terminologies with uncertain mappings. It tests the system's
capacity to handle complex hierarchical structures, cross-species mappings, and
conflicting expert annotations.

The benchmark includes:
1. Human brain anatomy (from FMA - Foundational Model of Anatomy)
2. Mouse brain anatomy (from Allen Brain Atlas)
3. Neuroscience terminology (from NeuroLex)
4. Clinical terminology (from SNOMED CT brain subset)
"""

from boomer.model import (
    KB,
    PFact,
    Fact,
    EquivalentTo,
    ProperSubClassOf,
    SubClassOf,
    MemberOfDisjointGroup,
    DisjointWith,
    SearchConfig,
)
from boomer.search import solve
from boomer.renderers.markdown_renderer import MarkdownRenderer
from boomer.renderers.yaml_renderer import YAMLRenderer
from boomer.evaluator import evaluate_facts
import time
from typing import List, Tuple, Dict
import json


def create_brain_kb() -> KB:
    """
    Create a knowledge base representing brain ontology integration challenges.

    This KB includes:
    - Cross-species mappings (human vs mouse brain regions)
    - Historical vs modern neuroanatomical terminology
    - Clinical vs research terminology
    - Uncertain mappings from automated text mining
    """

    # Deterministic facts (high-confidence background knowledge)
    facts = [
        # Human brain hierarchy (FMA-based)
        ProperSubClassOf(sub="human_cerebral_cortex", sup="human_telencephalon"),
        ProperSubClassOf(sub="human_telencephalon", sup="human_forebrain"),
        ProperSubClassOf(sub="human_forebrain", sup="human_brain"),
        ProperSubClassOf(sub="human_hippocampus", sup="human_telencephalon"),
        ProperSubClassOf(sub="human_amygdala", sup="human_telencephalon"),
        ProperSubClassOf(sub="human_frontal_lobe", sup="human_cerebral_cortex"),
        ProperSubClassOf(sub="human_temporal_lobe", sup="human_cerebral_cortex"),
        ProperSubClassOf(sub="human_parietal_lobe", sup="human_cerebral_cortex"),
        ProperSubClassOf(sub="human_occipital_lobe", sup="human_cerebral_cortex"),
        ProperSubClassOf(sub="human_prefrontal_cortex", sup="human_frontal_lobe"),

        # Mouse brain hierarchy (Allen Brain Atlas-based)
        ProperSubClassOf(sub="mouse_isocortex", sup="mouse_cerebrum"),
        ProperSubClassOf(sub="mouse_cerebrum", sup="mouse_forebrain"),
        ProperSubClassOf(sub="mouse_forebrain", sup="mouse_brain"),
        ProperSubClassOf(sub="mouse_hippocampal_formation", sup="mouse_cerebrum"),
        ProperSubClassOf(sub="mouse_amygdalar_nuclei", sup="mouse_cerebrum"),
        ProperSubClassOf(sub="mouse_frontal_pole", sup="mouse_isocortex"),
        ProperSubClassOf(sub="mouse_temporal_association_areas", sup="mouse_isocortex"),
        ProperSubClassOf(sub="mouse_somatosensory_areas", sup="mouse_isocortex"),
        ProperSubClassOf(sub="mouse_visual_areas", sup="mouse_isocortex"),

        # Clinical terminology (SNOMED CT-based)
        ProperSubClassOf(sub="cerebral_hemisphere_structure", sup="brain_structure"),
        ProperSubClassOf(sub="frontal_lobe_structure", sup="cerebral_hemisphere_structure"),
        ProperSubClassOf(sub="limbic_lobe_structure", sup="cerebral_hemisphere_structure"),
        ProperSubClassOf(sub="hippocampal_structure", sup="limbic_lobe_structure"),

        # Disjoint groups to prevent invalid intra-ontology equivalences
        MemberOfDisjointGroup(sub="human_cerebral_cortex", group="FMA"),
        MemberOfDisjointGroup(sub="human_hippocampus", group="FMA"),
        MemberOfDisjointGroup(sub="human_amygdala", group="FMA"),
        MemberOfDisjointGroup(sub="human_frontal_lobe", group="FMA"),
        MemberOfDisjointGroup(sub="human_temporal_lobe", group="FMA"),
        MemberOfDisjointGroup(sub="human_parietal_lobe", group="FMA"),
        MemberOfDisjointGroup(sub="human_occipital_lobe", group="FMA"),

        MemberOfDisjointGroup(sub="mouse_isocortex", group="AllenBrain"),
        MemberOfDisjointGroup(sub="mouse_hippocampal_formation", group="AllenBrain"),
        MemberOfDisjointGroup(sub="mouse_amygdalar_nuclei", group="AllenBrain"),
        MemberOfDisjointGroup(sub="mouse_frontal_pole", group="AllenBrain"),
        MemberOfDisjointGroup(sub="mouse_visual_areas", group="AllenBrain"),

        MemberOfDisjointGroup(sub="cerebral_hemisphere_structure", group="SNOMED"),
        MemberOfDisjointGroup(sub="frontal_lobe_structure", group="SNOMED"),
        MemberOfDisjointGroup(sub="hippocampal_structure", group="SNOMED"),

        # Known disjointness constraints
        DisjointWith(sub="human_frontal_lobe", sibling="human_temporal_lobe"),
        DisjointWith(sub="human_frontal_lobe", sibling="human_parietal_lobe"),
        DisjointWith(sub="human_frontal_lobe", sibling="human_occipital_lobe"),
        DisjointWith(sub="human_temporal_lobe", sibling="human_parietal_lobe"),
        DisjointWith(sub="human_temporal_lobe", sibling="human_occipital_lobe"),
        DisjointWith(sub="human_parietal_lobe", sibling="human_occipital_lobe"),
    ]

    # Probabilistic facts (uncertain mappings)
    pfacts = [
        # High-confidence cross-species homologies
        PFact(fact=EquivalentTo(sub="human_cerebral_cortex", equivalent="mouse_isocortex"), prob=0.85),
        PFact(fact=EquivalentTo(sub="human_hippocampus", equivalent="mouse_hippocampal_formation"), prob=0.92),
        PFact(fact=EquivalentTo(sub="human_amygdala", equivalent="mouse_amygdalar_nuclei"), prob=0.88),

        # Moderate confidence clinical mappings
        PFact(fact=EquivalentTo(sub="human_cerebral_cortex", equivalent="cerebral_hemisphere_structure"), prob=0.75),
        PFact(fact=EquivalentTo(sub="human_frontal_lobe", equivalent="frontal_lobe_structure"), prob=0.82),
        PFact(fact=EquivalentTo(sub="human_hippocampus", equivalent="hippocampal_structure"), prob=0.78),

        # Lower confidence cross-species mappings for specific regions
        PFact(fact=EquivalentTo(sub="human_frontal_lobe", equivalent="mouse_frontal_pole"), prob=0.65),
        PFact(fact=EquivalentTo(sub="human_occipital_lobe", equivalent="mouse_visual_areas"), prob=0.70),
        PFact(fact=EquivalentTo(sub="human_temporal_lobe", equivalent="mouse_temporal_association_areas"), prob=0.62),
        PFact(fact=EquivalentTo(sub="human_parietal_lobe", equivalent="mouse_somatosensory_areas"), prob=0.58),

        # Historical terminology mappings (legacy terms)
        PFact(fact=EquivalentTo(sub="archicortex", equivalent="human_hippocampus"), prob=0.71),
        PFact(fact=EquivalentTo(sub="paleocortex", equivalent="human_olfactory_cortex"), prob=0.68),
        PFact(fact=EquivalentTo(sub="neocortex", equivalent="human_cerebral_cortex"), prob=0.89),
        PFact(fact=EquivalentTo(sub="rhinencephalon", equivalent="human_olfactory_system"), prob=0.64),

        # Conflicting mappings from different sources
        PFact(fact=EquivalentTo(sub="human_prefrontal_cortex", equivalent="mouse_frontal_pole"), prob=0.72),
        PFact(fact=EquivalentTo(sub="human_prefrontal_cortex", equivalent="anterior_cingulate_area"), prob=0.45),

        # Text-mining derived mappings with lower confidence
        PFact(fact=EquivalentTo(sub="Ammon's_horn", equivalent="human_hippocampus"), prob=0.61),
        PFact(fact=EquivalentTo(sub="dentate_gyrus", equivalent="hippocampal_structure"), prob=0.58),
        PFact(fact=EquivalentTo(sub="CA1_field", equivalent="hippocampal_CA1"), prob=0.82),
        PFact(fact=EquivalentTo(sub="CA3_field", equivalent="hippocampal_CA3"), prob=0.81),

        # Potentially incorrect mappings (low probability)
        PFact(fact=EquivalentTo(sub="human_cerebral_cortex", equivalent="mouse_hippocampal_formation"), prob=0.12),
        PFact(fact=EquivalentTo(sub="human_frontal_lobe", equivalent="mouse_visual_areas"), prob=0.08),
        PFact(fact=EquivalentTo(sub="human_hippocampus", equivalent="mouse_frontal_pole"), prob=0.05),

        # Subsumption relationships with uncertainty
        PFact(fact=ProperSubClassOf(sub="human_prefrontal_cortex", sup="executive_control_region"), prob=0.77),
        PFact(fact=ProperSubClassOf(sub="mouse_frontal_pole", sup="executive_control_region"), prob=0.68),
        PFact(fact=ProperSubClassOf(sub="human_amygdala", sup="emotion_processing_region"), prob=0.83),
        PFact(fact=ProperSubClassOf(sub="mouse_amygdalar_nuclei", sup="emotion_processing_region"), prob=0.79),
    ]

    # Entity labels for human-readable output
    labels = {
        "human_cerebral_cortex": "Human Cerebral Cortex",
        "human_hippocampus": "Human Hippocampus",
        "human_amygdala": "Human Amygdala",
        "human_frontal_lobe": "Human Frontal Lobe",
        "human_temporal_lobe": "Human Temporal Lobe",
        "human_parietal_lobe": "Human Parietal Lobe",
        "human_occipital_lobe": "Human Occipital Lobe",
        "human_prefrontal_cortex": "Human Prefrontal Cortex",
        "mouse_isocortex": "Mouse Isocortex",
        "mouse_hippocampal_formation": "Mouse Hippocampal Formation",
        "mouse_amygdalar_nuclei": "Mouse Amygdalar Nuclei",
        "mouse_frontal_pole": "Mouse Frontal Pole",
        "mouse_visual_areas": "Mouse Visual Areas",
        "mouse_temporal_association_areas": "Mouse Temporal Association Areas",
        "mouse_somatosensory_areas": "Mouse Somatosensory Areas",
        "cerebral_hemisphere_structure": "Cerebral Hemisphere (SNOMED)",
        "frontal_lobe_structure": "Frontal Lobe (SNOMED)",
        "hippocampal_structure": "Hippocampal Structure (SNOMED)",
        "archicortex": "Archicortex (Historical)",
        "paleocortex": "Paleocortex (Historical)",
        "neocortex": "Neocortex (Historical)",
        "rhinencephalon": "Rhinencephalon (Historical)",
        "Ammon's_horn": "Ammon's Horn",
        "dentate_gyrus": "Dentate Gyrus",
        "CA1_field": "CA1 Field",
        "CA3_field": "CA3 Field",
    }

    return KB(
        facts=facts,
        pfacts=pfacts,
        labels=labels,
        name="Brain Ontology Integration",
        description="Integration of human and mouse brain anatomical ontologies with clinical terminology",
        comments="Benchmark for testing cross-species neuroanatomical alignment and terminology reconciliation"
    )


def create_extended_brain_kb() -> KB:
    """
    Create an extended version with more complexity for stress testing.
    Adds functional and cellular level annotations.
    """
    base_kb = create_brain_kb()

    additional_pfacts = [
        # Functional region mappings
        PFact(fact=EquivalentTo(sub="motor_cortex", equivalent="human_precentral_gyrus"), prob=0.91),
        PFact(fact=EquivalentTo(sub="sensory_cortex", equivalent="human_postcentral_gyrus"), prob=0.89),
        PFact(fact=EquivalentTo(sub="visual_cortex", equivalent="human_occipital_lobe"), prob=0.86),
        PFact(fact=EquivalentTo(sub="auditory_cortex", equivalent="human_superior_temporal_gyrus"), prob=0.84),

        # Brodmann area mappings
        PFact(fact=EquivalentTo(sub="BA4", equivalent="primary_motor_cortex"), prob=0.93),
        PFact(fact=EquivalentTo(sub="BA17", equivalent="primary_visual_cortex"), prob=0.94),
        PFact(fact=EquivalentTo(sub="BA41", equivalent="primary_auditory_cortex"), prob=0.92),
        PFact(fact=EquivalentTo(sub="BA44", equivalent="Broca's_area_pars_opercularis"), prob=0.88),
        PFact(fact=EquivalentTo(sub="BA45", equivalent="Broca's_area_pars_triangularis"), prob=0.87),

        # Cell type mappings across species
        PFact(fact=EquivalentTo(sub="human_pyramidal_neurons", equivalent="mouse_pyramidal_cells"), prob=0.95),
        PFact(fact=EquivalentTo(sub="human_interneurons", equivalent="mouse_GABAergic_neurons"), prob=0.91),
        PFact(fact=EquivalentTo(sub="human_astrocytes", equivalent="mouse_astroglia"), prob=0.93),
        PFact(fact=EquivalentTo(sub="human_oligodendrocytes", equivalent="mouse_oligodendroglia"), prob=0.92),
        PFact(fact=EquivalentTo(sub="human_microglia", equivalent="mouse_microglial_cells"), prob=0.94),

        # Developmental stage mappings
        PFact(fact=ProperSubClassOf(sub="embryonic_forebrain", sup="developing_brain"), prob=0.96),
        PFact(fact=ProperSubClassOf(sub="fetal_cerebral_cortex", sup="developing_cortex"), prob=0.95),
        PFact(fact=EquivalentTo(sub="neural_tube_prosencephalon", equivalent="embryonic_forebrain"), prob=0.88),

        # Disease-related mappings
        PFact(fact=ProperSubClassOf(sub="Alzheimer_affected_hippocampus", sup="human_hippocampus"), prob=0.98),
        PFact(fact=ProperSubClassOf(sub="Parkinson_affected_substantia_nigra", sup="human_midbrain"), prob=0.97),
        PFact(fact=ProperSubClassOf(sub="stroke_affected_cortex", sup="human_cerebral_cortex"), prob=0.96),
    ]

    base_kb.pfacts.extend(additional_pfacts)
    return base_kb


def run_benchmark(kb: KB, config: SearchConfig = None) -> Dict:
    """
    Run the benchmark and collect performance metrics.
    """
    if config is None:
        config = SearchConfig(
            max_iterations=100000,
            max_candidate_solutions=1000,
            timeout_seconds=60,
            partition_initial_threshold=50,
            max_pfacts_per_clique=30,
        )

    print(f"\n{'='*60}")
    print(f"Running Brain Ontology Benchmark")
    print(f"{'='*60}")
    print(f"KB Statistics:")
    print(f"  - Deterministic facts: {len(kb.facts)}")
    print(f"  - Probabilistic facts: {len(kb.pfacts)}")
    print(f"  - Total entities: {len(kb.labels)}")
    print(f"  - Search space size: 2^{len(kb.pfacts)} = {2**len(kb.pfacts):,} combinations")
    print(f"\nConfiguration:")
    print(f"  - Max iterations: {config.max_iterations:,}")
    print(f"  - Timeout: {config.timeout_seconds}s")
    print(f"  - Partition threshold: {config.partition_initial_threshold}")
    print(f"  - Max pfacts per clique: {config.max_pfacts_per_clique}")

    # Run the solver
    start_time = time.time()
    solution = solve(kb, config)
    end_time = time.time()

    # Collect metrics
    metrics = {
        "kb_size": {
            "facts": len(kb.facts),
            "pfacts": len(kb.pfacts),
            "entities": len(kb.labels),
            "search_space": 2**len(kb.pfacts),
        },
        "solution": {
            "confidence": solution.confidence,
            "prior_prob": solution.prior_prob,
            "posterior_prob": solution.posterior_prob,
            "combinations_explored": solution.number_of_combinations,
            "satisfiable_combinations": solution.number_of_satisfiable_combinations,
            "proportion_explored": solution.proportion_of_combinations_explored,
            "number_of_components": solution.number_of_components,
            "timed_out": solution.timed_out,
        },
        "performance": {
            "time_elapsed": end_time - start_time,
            "time_per_combination": (end_time - start_time) / max(solution.number_of_combinations, 1),
            "combinations_per_second": solution.number_of_combinations / max(end_time - start_time, 0.001),
        },
        "accepted_mappings": [],
        "rejected_mappings": [],
        "uncertain_mappings": [],
    }

    # Categorize results
    for spfact in solution.solved_pfacts:
        fact_info = {
            "fact": str(spfact.pfact.fact),
            "prior_prob": spfact.pfact.prob,
            "posterior_prob": spfact.posterior_prob,
        }

        if spfact.truth_value and spfact.posterior_prob > 0.8:
            metrics["accepted_mappings"].append(fact_info)
        elif not spfact.truth_value and spfact.posterior_prob < 0.2:
            metrics["rejected_mappings"].append(fact_info)
        else:
            metrics["uncertain_mappings"].append(fact_info)

    # Print results
    print(f"\n{'='*60}")
    print(f"Results:")
    print(f"{'='*60}")
    print(f"Performance:")
    print(f"  - Time elapsed: {metrics['performance']['time_elapsed']:.2f}s")
    print(f"  - Combinations explored: {metrics['solution']['combinations_explored']:,}")
    print(f"  - Combinations/second: {metrics['performance']['combinations_per_second']:.0f}")
    print(f"  - Proportion explored: {metrics['solution']['proportion_explored']:.2%}")

    print(f"\nSolution Quality:")
    print(f"  - Confidence: {metrics['solution']['confidence']:.2%}")
    print(f"  - Prior probability: {metrics['solution']['prior_prob']:.4e}")
    print(f"  - Posterior probability: {metrics['solution']['posterior_prob']:.2%}")

    print(f"\nMapping Statistics:")
    print(f"  - Accepted (high confidence): {len(metrics['accepted_mappings'])}")
    print(f"  - Rejected (low confidence): {len(metrics['rejected_mappings'])}")
    print(f"  - Uncertain: {len(metrics['uncertain_mappings'])}")

    # Show sample accepted mappings
    print(f"\nSample Accepted Mappings (top 10 by posterior probability):")
    accepted_sorted = sorted(metrics["accepted_mappings"],
                           key=lambda x: x["posterior_prob"],
                           reverse=True)[:10]
    for mapping in accepted_sorted:
        print(f"  - {mapping['fact']}")
        print(f"    Prior: {mapping['prior_prob']:.2f}, Posterior: {mapping['posterior_prob']:.2f}")

    return metrics


def run_scalability_experiment():
    """
    Test scalability with increasing KB sizes.
    """
    print(f"\n{'='*60}")
    print(f"Scalability Experiment")
    print(f"{'='*60}")

    results = []

    # Test with different subset sizes
    base_kb = create_brain_kb()
    sizes = [10, 20, 30, 40, len(base_kb.pfacts)]

    for size in sizes:
        # Create subset KB
        subset_kb = KB(
            facts=base_kb.facts,
            pfacts=base_kb.pfacts[:size],
            labels=base_kb.labels,
            name=f"Brain KB (size {size})",
        )

        config = SearchConfig(
            max_iterations=100000,
            timeout_seconds=30,
            partition_initial_threshold=20,
            max_pfacts_per_clique=15,
        )

        print(f"\nTesting with {size} pfacts...")
        metrics = run_benchmark(subset_kb, config)
        results.append({
            "size": size,
            "time": metrics["performance"]["time_elapsed"],
            "explored": metrics["solution"]["combinations_explored"],
            "confidence": metrics["solution"]["confidence"],
        })

    # Print summary table
    print(f"\n{'='*60}")
    print(f"Scalability Summary")
    print(f"{'='*60}")
    print(f"{'Size':<10} {'Time (s)':<12} {'Explored':<15} {'Confidence':<12}")
    print(f"{'-'*10} {'-'*12} {'-'*15} {'-'*12}")
    for r in results:
        print(f"{r['size']:<10} {r['time']:<12.2f} {r['explored']:<15,} {r['confidence']:<12.2%}")

    return results


def generate_ground_truth() -> List[Fact]:
    """
    Generate ground truth mappings for evaluation.
    Based on expert neuroanatomist consensus.
    """
    return [
        EquivalentTo(sub="human_cerebral_cortex", equivalent="mouse_isocortex"),
        EquivalentTo(sub="human_hippocampus", equivalent="mouse_hippocampal_formation"),
        EquivalentTo(sub="human_amygdala", equivalent="mouse_amygdalar_nuclei"),
        EquivalentTo(sub="human_frontal_lobe", equivalent="frontal_lobe_structure"),
        EquivalentTo(sub="human_hippocampus", equivalent="hippocampal_structure"),
        EquivalentTo(sub="neocortex", equivalent="human_cerebral_cortex"),
        EquivalentTo(sub="CA1_field", equivalent="hippocampal_CA1"),
        EquivalentTo(sub="CA3_field", equivalent="hippocampal_CA3"),
        ProperSubClassOf(sub="human_prefrontal_cortex", sup="executive_control_region"),
        ProperSubClassOf(sub="human_amygdala", sup="emotion_processing_region"),
    ]


def evaluate_solution(kb: KB, solution, ground_truth: List[Fact]):
    """
    Evaluate solution against ground truth.
    """
    # Extract accepted facts from solution
    accepted_facts = [
        spfact.pfact.fact
        for spfact in solution.solved_pfacts
        if spfact.truth_value and spfact.posterior_prob > 0.5
    ]

    # Calculate metrics
    stats = evaluate_facts(ground_truth, accepted_facts)

    print(f"\n{'='*60}")
    print(f"Evaluation Against Ground Truth")
    print(f"{'='*60}")
    print(f"Precision: {stats.precision:.2%}")
    print(f"Recall: {stats.recall:.2%}")
    print(f"F1 Score: {stats.f1:.2%}")
    print(f"\nTrue Positives: {stats.tp}")
    print(f"False Positives: {stats.fp}")
    print(f"False Negatives: {stats.fn}")

    if stats.fp_list:
        print(f"\nFalse Positives (incorrectly accepted):")
        for fact in stats.fp_list[:5]:
            print(f"  - {fact}")

    if stats.fn_list:
        print(f"\nFalse Negatives (incorrectly rejected):")
        for fact in stats.fn_list[:5]:
            print(f"  - {fact}")

    return stats


def save_results(metrics: Dict, filename: str = "brain_benchmark_results.json"):
    """
    Save benchmark results to file.
    """
    # Convert non-serializable objects to strings
    def make_serializable(obj):
        if isinstance(obj, (list, tuple)):
            return [make_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: make_serializable(value) for key, value in obj.items()}
        elif hasattr(obj, '__dict__'):
            return str(obj)
        else:
            return obj

    serializable_metrics = make_serializable(metrics)

    with open(f"analysis/{filename}", "w") as f:
        json.dump(serializable_metrics, f, indent=2)

    print(f"\nResults saved to analysis/{filename}")


def main():
    """
    Run the complete brain ontology benchmark suite.
    """
    # Create knowledge base
    kb = create_brain_kb()

    # Run basic benchmark
    print("\n" + "="*60)
    print("BRAIN ONTOLOGY INTEGRATION BENCHMARK")
    print("="*60)

    metrics = run_benchmark(kb)

    # Evaluate against ground truth
    ground_truth = generate_ground_truth()
    solution = solve(kb)
    eval_stats = evaluate_solution(kb, solution, ground_truth)

    # Add evaluation to metrics
    metrics["evaluation"] = {
        "precision": eval_stats.precision,
        "recall": eval_stats.recall,
        "f1": eval_stats.f1,
        "tp": eval_stats.tp,
        "fp": eval_stats.fp,
        "fn": eval_stats.fn,
    }

    # Run scalability experiment
    scalability_results = run_scalability_experiment()
    metrics["scalability"] = scalability_results

    # Save results
    save_results(metrics)

    # Generate detailed report
    renderer = MarkdownRenderer()
    with open("analysis/brain_benchmark_report.md", "w") as f:
        f.write("# Brain Ontology Integration Benchmark Report\n\n")
        f.write(f"## Solution\n\n")
        f.write(renderer.render(solution))
        f.write(f"\n## Metrics\n\n")
        f.write(f"```json\n{json.dumps(metrics, indent=2)}\n```\n")

    print("\nDetailed report saved to analysis/brain_benchmark_report.md")

    # Save solution in YAML format
    yaml_renderer = YAMLRenderer()
    with open("analysis/brain_solution.yaml", "w") as f:
        f.write(yaml_renderer.render(solution))

    print("Solution saved to analysis/brain_solution.yaml")

    print(f"\n{'='*60}")
    print("Benchmark Complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()