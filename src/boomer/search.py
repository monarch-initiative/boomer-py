from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
import itertools
import math
import time
from boomer.evaluator import evaluate_facts
from boomer.fact_generator import generate_hypotheses_for_hyperparamaters
from boomer.model import (
    KB,
    EvalStats,
    Fact,
    GridSearch,
    GridSearchResult,
    PFact,
    SolvedPFact,
    TreeNode,
    Grounding,
    Solution,
    SearchConfig,
    PFactConsensus,
    SynthesizedSolution,
    AggregateStats,
)
from typing import Iterator, List, Set, Tuple

from boomer.reasoners import get_reasoner
from boomer.reasoners.reasoner import Reasoner

import logging

from boomer.splitter import partition_kb
from boomer.utils import combine_solutions

logger = logging.getLogger(__name__)


@dataclass
class VisitationTracker:
    visited: Set[Set[Grounding]]
    unsatisfiable_combos: Set[Set[Grounding]]


def pr_selection_best(kb: KB, selection: Grounding) -> Tuple[float, bool]:
    """
    Calculate the probability of a selection.

    Args:
        kb: Knowledge base of facts and probabilistic facts.
        selection: A selected fact

    Returns:
        The probability of the selection.
    """
    ix, truth_value = selection
    pr = kb.pfacts[ix].prob
    if pr >= 0.5:
        return pr, truth_value
    else:
        return 1 - pr, not truth_value


def calc_prob_unselected(kb: KB, node: TreeNode) -> float:
    """
    Calculate the joint probability of the best path to a terminal node.

    Does not take into account entailment, so the actual probability may be lower.

    Args:
        kb: Knowledge base of facts and probabilistic facts.
        node: The node to calculate the probability for

    Returns:
        probability of the best path to a terminal node
    """
    pr_fact = 1.0
    for selection in node_remaining_selections_iter(node, kb):
        pr_fact *= pr_selection_best(kb, selection)[0]
    return pr_fact


def extend_node(
    node: TreeNode, kb: KB, selection: Grounding, reasoner: Reasoner
) -> TreeNode:
    """
    Given a node in the search tree, extend it with a selected ground fact.

    Args:
        node: The node to extend
        kb: The knowledge base
        selection: The selection to extend the node with
    """
    if selection in node.selections:
        raise ValueError(f"Duplicate selection: {selection}")
    asserted_selections = node.selections + [selection]
    reasoner_result = reasoner.reason(kb, asserted_selections)

    if reasoner_result.satisfiable:
        selections = reasoner_result.entailed_selections
        if not selections:
            raise ValueError(
                f"No entailed selections; input={node.selections} // {selection}"
            )
        # calculate joint probability of all selections so far (asserted and entailed)
        pr_selected = 1.0
        for ix, truth_value in selections:
            if truth_value:
                pr_fact = kb.pfacts[ix].prob
            else:
                pr_fact = 1 - kb.pfacts[ix].prob
            pr_selected *= pr_fact
    else:
        selections = asserted_selections + []
        pr_selected = 0.0
        already_selected_ixs = [s[0] for s in selections]
        for i in range(len(kb.pfacts)):
            if i in already_selected_ixs:
                continue
            selections.append((i, None))

    tn = TreeNode(
        parent=node,
        depth=node.depth + 1,
        selection=selection,
        selections=selections,
        asserted_selections=asserted_selections,
        pr_selected=pr_selected,
        terminal=len(selections) == len(kb.pfacts),
    )
    # TODO: improve efficiency avoiding recalculating this
    tn.pr = calc_prob_unselected(kb, tn) * pr_selected
    if node.pr and tn.pr:
        tn.surprise_factor = node.pr / tn.pr
        #if tn.surprise_factor > 10:
        #    print(f"Surprise factor: {kb.pfacts[tn.selection[0]]} {tn.surprise_factor} // {node.pr} / {tn.pr}")
    logger.debug(f"TN: D: {tn.depth} //  TERM:{tn.terminal} SAT: {tn.satifiable} // S: {tn.selections} // pr_est: {tn.pr} // pr_sel: {pr_selected}")
    return tn


def node_remaining_selections_iter(node: TreeNode, kb: KB) -> Iterator[Grounding]:
    """
    Iterate over all remaining extension selections for a node.

    For every pfact will generate two possible groundings, one for true and one for false.

    Args:
        node: The node to iterate over
        kb: The knowledge base

    Returns:
        Iterator[Grounding]: A generator of groundings
    """
    selected_pfacts = [pf[0] for pf in node.selections]
    for i, _pfact in enumerate(kb.pfacts):
        if i in selected_pfacts:
            continue
        for truth_value in [True, False]:
            selection = (i, truth_value)
            yield selection


def all_node_extensions(
    node: TreeNode, kb: KB, vt: VisitationTracker, reasoner: Reasoner
) -> Iterator[TreeNode]:
    # TODO: rename this function to be more descriptive
    # this is basically a wrapper around node_remaining_selections_iter
    # that adds the visited and unsatisfiable checks
    for selection in node_remaining_selections_iter(node, kb):
        fset = frozenset(node.selections + [selection])
        if fset in vt.visited:
            continue
        if any(unsat_set.issubset(fset) for unsat_set in vt.unsatisfiable_combos):
            continue
        yield extend_node(node, kb, selection, reasoner)


def search(kb: KB, config: SearchConfig) -> Iterator[TreeNode]:
    """
    Search for solutions for the knowledge base.

    Args:
        kb: The knowledge base to search
        config: Configuration for the search, including optional timeout

    Returns :
        Iterator[TreeNode]: A generator of search tree nodes
    """
    root = TreeNode(pr_selected=1.0, selections=[], asserted_selections=[])
    root.pr = calc_prob_unselected(kb, root)

    reasoner = get_reasoner(config.reasoner_class)

    # Setup timeout if specified
    start_time = time.time()

    stack = [root]
    # visited = {frozenset(root.asserted_selections)}
    vt = VisitationTracker(
        visited={frozenset(root.asserted_selections)}, unsatisfiable_combos=set()
    )
    n = 0

    grounding_counts: dict[int, dict[bool, int]] = {}

    while stack:
        n += 1
        early_termination = False
        # Check for timeout if configured
        if (
            config.timeout_seconds is not None
            and (time.time() - start_time) > config.timeout_seconds
        ):
            # Time limit exceeded
            print(f"Search timeout after {time.time() - start_time:.2f} seconds")
            early_termination = True

        if n > config.max_iterations:
            logger.info(f"Max iterations reached: {n}")
            early_termination = True

        if early_termination:
            if config.exhaustive_search_depth:
                stack = [n for n in stack if n.depth <= config.exhaustive_search_depth]
                #print(f"Resetting; Remaining Stack: {len(stack)}")
                #for n in stack:
                #    print(f"  {n.depth} {n}")
                #print("===========")
                if not stack:
                    break
                n = 0
            else:
                break

        node_to_expand = stack.pop()
        logger.info(
            f"Expanding node: D:{node_to_expand.depth} S: {len(node_to_expand.selections)}({len(node_to_expand.asserted_selections)}))/{len(kb.pfacts)} // pr:{node_to_expand.pr} // {[(truth_value, kb.pfacts[ix].fact) for ix, truth_value in node_to_expand.selections]}"
        )
        
        # TODO: use this to diversify search
        selected_grounding = node_to_expand.selection
        if selected_grounding:
            selected_fact_ix = selected_grounding[0]
            if selected_fact_ix not in grounding_counts:
                grounding_counts[selected_fact_ix] = {True: 0, False: 0}
            grounding_counts[selected_fact_ix][selected_grounding[1]] += 1

        # all possible ways to expand the tree one hop
        extensions = list(all_node_extensions(node_to_expand, kb, vt, reasoner))
        # print(f"N: {node_to_expand.selections} // exts: {len(extensions)}")
        for e in extensions:
            vt.visited.add(frozenset(e.asserted_selections))
            if not e.satifiable:
                vt.unsatisfiable_combos.add(frozenset(e.asserted_selections))
        # partition into terminal and non-terminal extensions
        terminal_extensions = [e for e in extensions if e.terminal]
        non_terminal_extensions = [
            e for e in extensions if not e.terminal and e.satifiable
        ]
        logger.info(f"Terminal extensions: {len(terminal_extensions)}")
        logger.info(f"Non-terminal extensions: {len(non_terminal_extensions)}")
        yield from terminal_extensions
        if non_terminal_extensions:
            # Extend the stack to ensure depth-first, with the best extension from this node
            # going to the top of the stack; after that all other potential extensions
            assert not any(not e.satifiable for e in non_terminal_extensions)
            # Ensure depth-first; select the best non-terminal extension
            non_terminal_extensions.sort(key=lambda x: x.pr, reverse=False)
            next_node = non_terminal_extensions.pop()
            stack.extend(non_terminal_extensions)
            # sort the stack by probability of the node, but ensure that all
            # each potential grounding has a chance to be explored;
            # TODO: this makes the exhaustive_search_depth feature less relevant
            sort_f = lambda x: x.pr + (1 if x.depth == 1 else 0)
            stack.sort(key=sort_f, reverse=False)
            stack.append(next_node)
            # print(f"NN: {next_node.pr_selected} {next_node.pr} {next_node.depth}")


def pfact_index_truth_value(selections: List[Grounding], ix: int) -> bool:
    for this_ix, truth_value in selections:
        if this_ix == ix:
            return truth_value
    return False


def solve(kb: KB, config: SearchConfig | None = None) -> Solution:
    """
    Solve a knowledge base to find the most probable consistent interpretation.

    This function performs probabilistic reasoning over a knowledge base to find the
    optimal combination of truth values for all probabilistic facts that:
    1. Is logically consistent (satisfiable)
    2. Has the highest probability among all satisfiable combinations

    For large knowledge bases, solve() automatically applies a partitioning and
    subclustering strategy to manage computational complexity:

    **Automatic Partitioning:**
    - If the KB has more pfacts than `config.partition_initial_threshold`, it's
      automatically partitioned into strongly connected components (cliques)
    - Each component is solved independently and solutions are combined
    - This reduces complexity from O(2^n) to O(2^n1 + 2^n2 + ... + 2^nk)

    **Recursive Subclustering:**
    - If a partition still exceeds `config.max_pfacts_per_clique`, it's further
      subdivided using the split_connected_components algorithm
    - This algorithm temporarily drops low-probability pfacts to find natural
      splitting points in the graph structure
    - Dropped pfacts are restored after extracting sub-components

    Args:
        kb: The knowledge base to solve, containing facts and probabilistic facts
        config: Optional SearchConfig to control search behavior. If None, uses defaults.
                Key parameters:
                - max_pfacts_per_clique: Maximum pfacts per partition (triggers subclustering)
                - partition_initial_threshold: When to start partitioning (default: same as max_pfacts_per_clique)
                - max_iterations: Maximum search iterations per partition
                - max_candidate_solutions: Maximum solutions to collect per partition
                - timeout_seconds: Time limit for solving
                - reasoner_class: Reasoner implementation to use

    Returns:
        Solution: Contains the optimal truth value assignments and metadata:
            - solved_pfacts: List of pfacts with truth values and posterior probabilities
            - confidence: Confidence in the solution (0-1)
            - prior_prob: Prior probability of the solution
            - posterior_prob: Posterior probability of the solution
            - number_of_combinations: Total combinations explored
            - number_of_satisfiable_combinations: Satisfiable combinations found
            - time_elapsed: Time taken to solve
            - timed_out: Whether search timed out

    Examples:
        >>> from boomer.model import KB, PFact, EquivalentTo, SearchConfig
        >>> # Simple KB
        >>> kb = KB(pfacts=[
        ...     PFact(fact=EquivalentTo(sub="A", equivalent="B"), prob=0.9),
        ...     PFact(fact=EquivalentTo(sub="B", equivalent="C"), prob=0.8)
        ... ])
        >>> solution = solve(kb)  # doctest: +ELLIPSIS
        Solving KB: ... with 2 pfacts; threshold=...
        >>> solution.confidence > 0.5
        True

        >>> # Large KB with automatic partitioning (example structure)
        >>> config = SearchConfig(
        ...     max_pfacts_per_clique=100,      # Limit partition size
        ...     partition_initial_threshold=50   # Start partitioning early
        ... )
        >>> # Would automatically partition and solve a large KB efficiently

    Note:
        The partitioning and subclustering happen transparently. You don't need to
        manually partition the KB - just call solve() and it handles the complexity.

        For very large KBs, consider setting max_pfacts_per_clique to balance
        accuracy vs performance. Lower values (20-50) are faster but may drop
        some low-probability facts. Higher values (100-200) are more thorough
        but slower.
    """
    if config is None:
        config = SearchConfig()

    # partition the KB into sub-clusters of pfacts
    print(f"Solving KB: {kb.name} with {len(kb.pfacts)} pfacts; threshold={config.partition_initial_threshold}")
    if len(kb.pfacts) > config.max_pfacts_per_clique or len(kb.pfacts) > config.partition_initial_threshold:
        solutions = []
        print(f"Partitioning KB, num pfacts= {len(kb.pfacts)} sub-KBs (threshold={config.partition_initial_threshold})")
        sub_kbs = list(
            partition_kb(kb, max_pfacts_per_clique=config.max_pfacts_per_clique)
        )
        print(f"Partitioning KB into {len(sub_kbs)} sub-KBs")
        for subkb in sub_kbs:
            if not subkb.pfacts:
                continue
            print(
                f"Solving sub-KB: {len(subkb.facts)} facts, {len(subkb.pfacts)} pfacts"
            )
            config = deepcopy(config)
            # ensure no infinite recursion
            config.partition_initial_threshold = len(subkb.pfacts)
            sub_solution = solve(subkb, config)
            print(
                f"Sub-solution: pr:{sub_solution.prior_prob} // post:{sub_solution.posterior_prob} // {sub_solution.number_of_combinations} combinations"
            )
            solutions.append(sub_solution)
        return combine_solutions(solutions)
    
    if kb.hyperparams:
        # create hypotheses for hyperparamaters;
        # e.g. probability of omitted subclasses within the same ontology
        hypotheses = generate_hypotheses_for_hyperparamaters(kb, get_reasoner(config.reasoner_class))
        for h in hypotheses:
            print(f"Adding hypothesis: {h}")
            kb.pfacts_entailed.append(h)

    # Track start time
    time_started = time.time()

    # Flag to track if search timed out
    timed_out = False

    # use the main search function to find terminal nodes
    nodes: list[TreeNode] = []
    for n in search(kb, config):
        if not n.terminal:
            continue
        nodes.append(n)
        if (
            config.max_candidate_solutions
            and len(nodes) >= config.max_candidate_solutions
        ):
            break

    # Check if search timed out - we can infer this if the search completed but
    # we didn't get any nodes, or if we got fewer nodes than expected and we had a timeout set
    if (
        config.timeout_seconds is not None
        and (time.time() - time_started) >= config.timeout_seconds
    ):
        timed_out = True
    # if not nodes:
    #    raise ValueError("No solutions found")
    number_of_possible_combinations = kb.number_of_combinations()
    number_of_combinations_explored = len(nodes)
    number_of_satisfiable_combinations = sum(1 for n in nodes if n.satifiable)
    number_of_combinations_explored_including_implicit = (
        number_of_satisfiable_combinations
    )
    for n in nodes:
        if not n.satifiable:
            number_of_combinations_explored_including_implicit += 2 ** (
                len(n.selections) - len(n.asserted_selections)
            )
    est_prop_explored = (
        number_of_combinations_explored_including_implicit
        / number_of_possible_combinations
    )
    est_prop_explored = min(est_prop_explored, 1.0)

    if nodes:
        # sort nodes by pr; 0th element is best/highest pr
        nodes.sort(key=lambda x: x.pr, reverse=True)
        best = nodes[0]
        prior_prob = best.pr
        total_pr = sum(n.pr for n in nodes)
        posterior_prob = (best.pr / total_pr) if total_pr > 0.0 else 0.0
        if len(nodes) >= 2:
            next_best = nodes[1]
            if next_best.pr > 0.0:
                confidence = 1.0 / (1.0 + math.exp(-math.log(best.pr / next_best.pr)))
            else:
                confidence = 1.0
        else:
            confidence = 1.0
        ground_pfacts = [
            (kb.pfacts[ix], truth_value) for ix, truth_value in best.selections
        ]
        # calculate posterior probability for each pfact
        # P(pfact=true) = sum(P(pfact=true|node) * P(node)) for all nodes
        # P(pfact=false) = sum(P(pfact=false|node) * P(node)) for all nodes
        solved_pfacts = []
        for ix, pfact in enumerate(kb.pfacts):
            pfact_posterior_prob = 0.0
            tot_pr_n = 0.0

            for n in nodes:
                if not n.satifiable:
                    continue
                pr_n = n.pr
                truth_value = pfact_index_truth_value(n.selections, ix)
                if truth_value:
                    pfact_posterior_prob += pr_n

                tot_pr_n += pr_n
            truth_value = pfact_index_truth_value(best.selections, ix)
            solved_pfacts.append(
                SolvedPFact(
                    pfact=pfact,
                    truth_value=truth_value,
                    posterior_prob=(pfact_posterior_prob / tot_pr_n)
                    if tot_pr_n > 0.0
                    else 0.0,
                )
            )

    else:
        confidence = 0.0
        posterior_prob = 0.0
        prior_prob = 0.0
        ground_pfacts = []
        solved_pfacts = []

    # Track end time
    time_finished = time.time()

    return Solution(
        # nodes=nodes,
        ground_pfacts=ground_pfacts,
        solved_pfacts=solved_pfacts,
        confidence=confidence,
        prior_prob=prior_prob,
        posterior_prob=posterior_prob,
        number_of_combinations=number_of_combinations_explored,
        number_of_combinations_explored_including_implicit=number_of_combinations_explored_including_implicit,
        number_of_satisfiable_combinations=number_of_satisfiable_combinations,
        proportion_of_combinations_explored=est_prop_explored,
        time_started=time_started,
        time_finished=time_finished,
        timed_out=timed_out,
    )


def evaluate_hypotheses(
    kb: KB, hypothesis_list: List[Fact], config: SearchConfig
) -> List[Tuple[float, Fact, Solution]]:
    solutions = []
    sum_pr = 0.0
    epsilon = 1e-10
    for i, hypothesis in enumerate(hypothesis_list):
        kb_copy = deepcopy(kb)
        kb_copy.pfacts.append(PFact(hypothesis, 1.0))
        for k in range(len(hypothesis_list)):
            if k != i:
                kb_copy.pfacts.append(PFact(hypothesis_list[k], 0.0))
        solution = solve(kb_copy, config)
        pr = solution.prior_prob
        solutions.append((pr, hypothesis, solution))
        sum_pr += pr + epsilon
    solutions = [
        (pr / sum_pr, hypothesis, solution) for pr, hypothesis, solution in solutions
    ]
    solutions.sort(key=lambda x: x[0], reverse=True)
    return solutions


def compute_aggregate_stats(results: List[GridSearchResult]) -> AggregateStats:
    """
    Compute aggregate statistics across all grid search results.

    >>> results = []  # Would normally have GridSearchResult instances
    >>> # stats = compute_aggregate_stats(results)
    """
    import numpy as np

    # Filter for results with evaluations if available
    eval_results = [r for r in results if r.evaluation is not None]
    all_results = results if not eval_results else eval_results

    # Extract metrics
    if eval_results:
        precisions = [r.evaluation.precision for r in eval_results]
        recalls = [r.evaluation.recall for r in eval_results]
        f1s = [r.evaluation.f1 for r in eval_results]
    else:
        precisions = recalls = f1s = [0.0]

    confidences = [r.result.confidence for r in all_results]
    posterior_probs = [r.result.posterior_prob for r in all_results]
    times = [r.result.time_elapsed or 0.0 for r in all_results]
    combinations = [r.result.number_of_combinations for r in all_results]

    # Calculate success and timeout rates
    success_rate = sum(1 for r in all_results if r.result.confidence > 0) / len(all_results)
    timeout_rate = sum(1 for r in all_results if r.result.timed_out) / len(all_results)

    return AggregateStats(
        mean_precision=np.mean(precisions) if precisions else 0.0,
        std_precision=np.std(precisions) if precisions else 0.0,
        mean_recall=np.mean(recalls) if recalls else 0.0,
        std_recall=np.std(recalls) if recalls else 0.0,
        mean_f1=np.mean(f1s) if f1s else 0.0,
        std_f1=np.std(f1s) if f1s else 0.0,
        mean_confidence=np.mean(confidences),
        std_confidence=np.std(confidences),
        mean_posterior_prob=np.mean(posterior_probs),
        mean_time=np.mean(times),
        std_time=np.std(times),
        mean_combinations_explored=int(np.mean(combinations)),
        success_rate=success_rate,
        timeout_rate=timeout_rate,
    )


def synthesize_solution(kb: KB, results: List[GridSearchResult]) -> SynthesizedSolution:
    """
    Synthesize a consensus solution across all grid search results.

    Creates a robust solution by aggregating evidence across all configurations,
    identifying mappings that are consistently accepted regardless of parameter settings.
    """
    import numpy as np

    # Collect acceptance data for each pfact
    pfact_data: dict[int, dict] = defaultdict(lambda: {
        "accepted_configs": [],
        "posteriors": [],
        "truth_values": [],
    })

    for config_idx, result in enumerate(results):
        for pfact_idx, spfact in enumerate(result.result.solved_pfacts):
            data = pfact_data[pfact_idx]
            data["pfact"] = spfact.pfact
            data["truth_values"].append(spfact.truth_value)

            if spfact.truth_value:
                data["accepted_configs"].append(config_idx)
                data["posteriors"].append(spfact.posterior_prob)

    # Build consensus for each pfact
    pfact_consensus_list = []
    high_confidence = []
    uncertain = []

    for pfact_idx in sorted(pfact_data.keys()):
        data = pfact_data[pfact_idx]
        n_accepted = len(data["accepted_configs"])
        n_total = len(data["truth_values"])

        acceptance_rate = n_accepted / n_total if n_total > 0 else 0.0

        if data["posteriors"]:
            mean_posterior = np.mean(data["posteriors"])
            std_posterior = np.std(data["posteriors"])
        else:
            mean_posterior = 0.0
            std_posterior = 0.0

        # Consensus score weights acceptance rate by mean posterior probability
        consensus_score = acceptance_rate * (mean_posterior if mean_posterior > 0 else 0.0)

        consensus = PFactConsensus(
            pfact=data["pfact"],
            acceptance_rate=acceptance_rate,
            mean_posterior=mean_posterior,
            std_posterior=std_posterior,
            consensus_score=consensus_score,
            configurations_accepted=data["accepted_configs"],
            configurations_total=n_total,
        )
        pfact_consensus_list.append(consensus)

        # Categorize by consensus strength
        if consensus_score > 0.8:
            high_confidence.append(data["pfact"])
        elif 0.4 <= consensus_score <= 0.6:
            uncertain.append(data["pfact"])

    return SynthesizedSolution(
        pfact_consensus=pfact_consensus_list,
        aggregation_method="weighted_vote",
        min_consensus_threshold=0.5,
        contributing_configs=len(results),
        high_confidence_facts=high_confidence,
        uncertain_facts=uncertain,
    )


def find_best_config(results: List[GridSearchResult]) -> Tuple[SearchConfig | None, str | None]:
    """
    Find the best configuration based on F1 score (or confidence if no evaluation).

    Returns the config and the metric name used for selection.
    """
    if not results:
        return None, None

    # Prefer F1 score if evaluations are available
    eval_results = [r for r in results if r.evaluation is not None]

    if eval_results:
        best = max(eval_results, key=lambda r: r.evaluation.f1)
        return best.config, "f1_score"
    else:
        best = max(results, key=lambda r: r.result.confidence)
        return best.config, "confidence"


def find_pareto_frontier(results: List[GridSearchResult]) -> List[GridSearchResult]:
    """
    Find the Pareto frontier of configurations (speed vs accuracy trade-off).

    A configuration is on the Pareto frontier if no other configuration is both
    faster AND more accurate.
    """
    if not results:
        return []

    # For configurations with evaluation, use F1; otherwise use confidence
    def get_accuracy(r: GridSearchResult) -> float:
        if r.evaluation:
            return r.evaluation.f1
        return r.result.confidence

    def get_speed(r: GridSearchResult) -> float:
        # Inverse of time (higher is better/faster)
        time = r.result.time_elapsed or 0.001
        return 1.0 / time

    pareto = []

    for candidate in results:
        candidate_acc = get_accuracy(candidate)
        candidate_speed = get_speed(candidate)

        # Check if dominated by any other result
        dominated = False
        for other in results:
            if other is candidate:
                continue

            other_acc = get_accuracy(other)
            other_speed = get_speed(other)

            # Other dominates if better in both dimensions
            if other_acc >= candidate_acc and other_speed >= candidate_speed:
                if other_acc > candidate_acc or other_speed > candidate_speed:
                    dominated = True
                    break

        if not dominated:
            pareto.append(candidate)

    return pareto


def grid_search(
    kb: KB,
    grid: GridSearch,
    eval_kb: KB | None = None,
) -> GridSearch:
    """
    Perform a grid search over hyperparameters.

    Expands the provided GridSearch.configuration_matrix against each base SearchConfig
    in grid.configurations, runs solve for each resulting configuration, and records
    the solutions and evaluations.

    If eval_kb is provided, each solution is evaluated against eval_kb.facts.
    """
    # Expand configurations via cartesian product of parameter matrix
    if grid.configuration_matrix:
        list_keys = {
            "pr_filter": "pr_filters",
        }
        keys = list(grid.configuration_matrix.keys())
        keys = [k for k in keys if k not in list_keys]
        values_list = [grid.configuration_matrix[k] for k in keys]
        new_configs: list[SearchConfig] = []
        for base_cfg in grid.configurations:
            for combo in itertools.product(*values_list):
                cfg = deepcopy(base_cfg)
                for key, val in zip(keys, combo):
                    setattr(cfg, key, val)
                new_configs.append(cfg)
        for cfg in new_configs:
            for k, mapped_k in list_keys.items():
                if k in grid.configuration_matrix:
                    setattr(cfg, mapped_k, grid.configuration_matrix[k])

        grid.configurations = new_configs

    results: list[GridSearchResult] = []
    for cfg in grid.configurations:
        sol = solve(kb, cfg)
        if eval_kb is not None:
            pr_filters = cfg.pr_filters
            if not pr_filters:
                pr_filters = [0.0]
            for pr_filter in pr_filters:
                preds = [spf.pfact.fact for spf in sol.solved_pfacts if spf.truth_value and spf.posterior_prob >= pr_filter]
                stats = evaluate_facts(eval_kb.facts, preds)
                results.append(GridSearchResult(config=cfg, result=sol, evaluation=stats, pr_filter=pr_filter))
        else:
            results.append(GridSearchResult(config=cfg, result=sol))
    grid.results = results

    # Compute aggregate statistics and synthesized solution
    if results:
        grid.aggregate_stats = compute_aggregate_stats(results)
        grid.synthesized_solution = synthesize_solution(kb, results)
        grid.best_config, grid.best_config_metric = find_best_config(results)
        grid.pareto_frontier = find_pareto_frontier(results)

    return grid
