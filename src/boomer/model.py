from abc import ABC
from copy import deepcopy
from pydantic import BaseModel, Field
from typing import Any, List, Tuple, Optional, Dict, Union, Literal, Annotated

NodeIdentifier = str
EntityIdentifier = str


class SearchConfig(BaseModel):
    """
    A search configuration is a configuration for a search.

    Attributes:
        reasoner_class: The class name of the reasoner to use
        max_iterations: Maximum number of iterations in the search
        max_candidate_solutions: Maximum number of candidate solutions to generate
        timeout_seconds: Maximum time in seconds to allow search to run (None means no timeout)
        partition_initial_threshold: Minimum number of pfacts to trigger partitioning
        max_pfacts_per_clique: Maximum pfacts per clique; excess low-probability facts are removed
    """

    reasoner_class: str = Field(default="boomer.reasoners.nx_reasoner.NxReasoner")
    max_iterations: int = 1000000
    max_candidate_solutions: int = 10000
    timeout_seconds: Optional[float] = None
    exhaustive_search_depth: Optional[int] = Field(None, description="If set, the search will be exhaustive up to the given depth. Timeouts apply to sub-search branches.")
    partition_initial_threshold: int = 200
    max_pfacts_per_clique: Optional[int] = 1000
    pr_filters: list[float] | None = None


class BaseFact(BaseModel, ABC):
    model_config = {"frozen": True}


# for each of these document using the DL form:
class SubClassOf(BaseFact):
    """
    A subclass (subsumption) axiom.

    SubClassOf(sub="a", sup="b") means a ⊆ b

    Note that SubClassOf includes equivalence, i.e. 
    EquivalentTo(sub="a", equivalent="b") entails SubClassOf(sub="a", sup="b")

    See ProperSubClassOf for subclass axioms that exclude equivalence.
    """
    fact_type: Literal["SubClassOf"] = "SubClassOf"
    sub: EntityIdentifier
    sup: EntityIdentifier


class ProperSubClassOf(BaseFact):
    """
    A proper subclass of a class is a subclass of a class that is not the same as the class itself.

    ProperSubClassOf(sub="a", sup="b") means a ⊂ b
    """

    fact_type: Literal["ProperSubClassOf"] = "ProperSubClassOf"
    sub: EntityIdentifier
    sup: EntityIdentifier


class EquivalentTo(BaseFact):
    """
    An equivalence axiom.

    EquivalentTo(sub="a", equivalent="b") means a ≡ b
    """

    fact_type: Literal["EquivalentTo"] = "EquivalentTo"
    sub: str
    equivalent: EntityIdentifier


class DisjointWith(BaseFact):
    fact_type: Literal["DisjointWith"] = "DisjointWith"
    sub: EntityIdentifier
    sibling: EntityIdentifier


class OneOf(BaseFact):
    fact_type: Literal["OneOf"] = "OneOf"
    sub: EntityIdentifier
    sibling: EntityIdentifier


class NotInSubsumptionWith(BaseFact):
    fact_type: Literal["NotInSubsumptionWith"] = "NotInSubsumptionWith"
    sub: EntityIdentifier
    sibling: EntityIdentifier


class MemberOfDisjointGroup(BaseModel):
    """
    A member of a disjoint group.

    MemberOfDisjointGroup(sub="c1", group="g") and MemberOfDisjointGroup(sub="c2", group="g") entails
    that c1 and c2 are not equivalent.

    This can be used to assert a local form of the unique name constraint.

    It is commonly used for ontologies where the UNA would apply *within* a namespace. This is
    useful for mapping problems, where we might want to infer ONT1:xyz ≡ ONT2:abc, but forbit
    ONT1:xyz ≡ ONT1:abc
    """
    model_config = {"frozen": True}
    fact_type: Literal["MemberOfDisjointGroup"] = "MemberOfDisjointGroup"
    sub: EntityIdentifier
    group: str


class DisjointSet(BaseFact):
    """
    Efficiently encode a set of pairwise disjoint entities.
    DisjointSet([a,b,c,d]) means a⊥b, a⊥c, a⊥d, b⊥c, b⊥d, c⊥d
    """

    fact_type: Literal["DisjointSet"] = "DisjointSet"
    entities: Tuple[EntityIdentifier, ...]

    def model_post_init(self, __context):
        # Ensure immutable tuple and sorted for consistency
        if not isinstance(self.entities, tuple):
            object.__setattr__(self, "entities", tuple(sorted(self.entities)))


class NegatedFact(BaseFact):
    fact_type: Literal["NegatedFact"] = "NegatedFact"
    negated: "Fact"


Fact = Annotated[
    Union[
        SubClassOf,
        ProperSubClassOf,
        EquivalentTo,
        NotInSubsumptionWith,
        DisjointSet,
        DisjointWith,
        NegatedFact,
        MemberOfDisjointGroup,
    ],
    Field(discriminator="fact_type"),
]

# TODO: implement these
class KBHyperParameter(BaseModel, ABC):
    prob: float

class ProbabilityMissingEquivalentTo(KBHyperParameter):
    """
    The probability of a missing EquivalentTo fact.
    """
    disjoint_group_sub: str | None = None
    disjoint_group_equivalent: str | None = None

class ProbabilityMissingProperSubClassOf(KBHyperParameter):
    """
    The probability of a missing ProperSubClassOf fact.
    """
    disjoint_group_sub: str | None = None
    disjoint_group_sup: str | None = None

class PFact(BaseModel):
    """
    A probabilistic fact is a fact and a probability.
    """

    fact: Fact
    prob: float


class KB(BaseModel):
    """
    A knowledge base is a collection of facts and probabilistic facts.
    """

    facts: List[Fact] = Field(default_factory=list)
    pfacts: List[PFact] = Field(default_factory=list)
    hypotheses: List[Fact] = Field(default_factory=list)
    labels: Dict[EntityIdentifier, str] = Field(default_factory=dict)
    hyperparams: List[KBHyperParameter] = Field(default_factory=list)
    pfacts_entailed: List[PFact] = Field(default_factory=list, description="Pfacts that are only check as entailments")
    default_configurations: dict[str, SearchConfig] | None = None

    name: Optional[str] = None
    description: Optional[str] = None
    comments: Optional[str] = None

    def normalize(self):
        """
        Ensure all facts are ordered by probability, highest first.
        """
        self.pfacts.sort(key=lambda x: x.prob, reverse=True)

    def number_of_combinations(self) -> int:
        """
        Return the number of combinations of the facts.
        """
        return 2 ** len(self.pfacts)

    def pfact_index(self, fact: Fact) -> Optional[int]:
        """
        Return the index of the fact in the pfacts list.
        """
        for i, pfact in enumerate(self.pfacts):
            if pfact.fact == fact:
                return i

    def extend(self, **kwargs) -> "KB":
        """
        Extend the knowledge base with new facts.
        """
        new_kb = deepcopy(self)
        for k, v in kwargs.items():
            curr_val = getattr(new_kb, k)
            if isinstance(curr_val, list):
                # append to the list
                curr_val.extend(v)
            elif isinstance(curr_val, dict):
                # merge the dicts
                curr_val.update(v)
            else:
                # replace the value
                setattr(new_kb, k, v)
        return new_kb


class ReasonerState(BaseModel):
    """
    A reasoner state is a state of a reasoner.
    """

    pass


PFactIndex = int

# class Grounding(NamedTuple):
#    """
#    A grounding is an index to a probabilistic fact and its grounded truth value.
#    """
#    pfact_index: PFactIndex
#    truth_value: bool
Grounding = Tuple[PFactIndex, Optional[bool | None]]


class TreeNode(BaseModel):
    """
    A node in the search tree.

    Represents a search path/state over a set of potential hypotheses
    """

    parent: Optional["TreeNode"] = Field(None, description="The parent node representing the previous selection")
    depth: int = Field(0, description="The depth of the node in the search tree")
    selection: Union[Grounding, None] = Field(None, description="The current selection made at this node")
    asserted_selections: List[Grounding] = Field(default_factory=list, description="The selections that have been asserted at this node")
    selections: List[Grounding] = Field(default_factory=list, description="The selections that have been considered at this node, including asserted and entailed")
    pr_selected: float = Field(0.0, description="The probability of the selections being true")
    pr: Optional[float] = Field(None, description="Estimated probability of the overall solution, including estimated of best path to terminal node")
    surprise_factor: Optional[float] = Field(None, description="Ratio between pr of parent and pr of child")
    terminal: bool = Field(False, description="Whether the node is a terminal node")
    reasoner_state: Union[ReasonerState, None] = None

    @property
    def satifiable(self) -> bool:
        """
        Return True if the solution at this node is satisfiable.
        """
        return self.pr_selected > 0.0

    @property
    def identifier(self) -> NodeIdentifier:
        """
        Return a unique identifier for the node.
        """
        n_true = 0
        n_false = 0
        for s in self.selections:
            if s[1]:
                n_true += 2 ** s[0]
            else:
                n_false += 2 ** s[0]
        return f"{n_true}/{n_false}"


class SolvedPFact(BaseModel):
    """
    A ground state for a particular probabilistic fact, with a probability
    """

    pfact: PFact
    truth_value: bool | None = None
    posterior_prob: float
    metadata: Dict[str, Any] | None = None


class Solution(BaseModel):
    """
    A solution is a grounding of probabilistic facts.
    """

    name: str | None = Field(None, description="The name of the solution")
    number_of_combinations: int = Field(..., description="The number of explicitly explored combinations.")

    number_of_satisfiable_combinations: int = Field(..., description="The number of satisfiable combinations.")
    number_of_combinations_explored_including_implicit: int = Field(..., description="The number of combinations explored, including implicit ones.")
    number_of_components: int | None = Field(None, description="The number of components in the solution.")

    confidence: float = Field(..., description="The confidence of the solution (prob of solution vs next most likely solution).")
    prior_prob: float = Field(..., description="The prior probability of the solution.")
    posterior_prob: float = Field(..., description="The posterior probability of the solution.")
    proportion_of_combinations_explored: float = Field(..., description="The proportion of combinations explored (may be an estimate).")

    # nodes: List[TreeNode]
    ground_pfacts: List[Tuple[PFact, bool | None]] = Field(..., description="The ground probabilistic facts and their truth values.")
    solved_pfacts: List[SolvedPFact] = Field(..., description="The solved probabilistic facts.")

    sub_solutions: List["Solution"] = Field(default_factory=list, description="If the KB is partitioned, this is a list of sub-solutions.")

    # Timing information
    time_started: Optional[float] = Field(None, description="Timestamp when the search started (seconds since epoch)")

    time_finished: Optional[float] = Field(None, description="Timestamp when the search finished (seconds since epoch)")

    # Status information
    timed_out: bool = Field(False, description="Whether the search timed out before completion")

    @property
    def time_elapsed(self) -> Optional[float]:
        """
        Returns the elapsed time in seconds between start and finish.
        Returns None if either time_started or time_finished is not set.
        """
        if self.time_started is None or self.time_finished is None:
            return None
        return self.time_finished - self.time_started
    
    def as_dict(self) -> Dict[str, Any]:
        """
        Convert the solution to a dictionary.
        """
        obj = self.model_dump()
        obj["ground_pfacts"] = []
        #obj["ground_pfacts"] = [{"fact": pfact.model_dump(), "truth_value": tv} for pfact, tv in self.ground_pfacts]
        obj["time_elapsed"] = self.time_elapsed
        # recursively add sub-solutions (to avoid tuples)
        obj["sub_solutions"] = [s.as_dict() for s in self.sub_solutions]
        return obj
    
    def sort_sub_solutions(self):
        """
        Sort the sub-solutions by posterior probability, lowest first.
        """
        if self.sub_solutions:
            self.sub_solutions.sort(key=lambda x: x.posterior_prob)

    def name_sub_solutions(self, kb: KB):
        """
        Name the sub-solutions.
        """
        if self.sub_solutions:
            for i, sub_solution in enumerate(self.sub_solutions):
                if not sub_solution.name:
                    distinct_labels = set()
                    if kb.labels:
                        for spfact in sub_solution.solved_pfacts:
                            fact = spfact.pfact.fact
                            fact_args = fact.model_dump().values()
                            for pfact_arg in fact_args:
                                label = kb.labels.get(pfact_arg)
                                if label:
                                    distinct_labels.add(label)
                    if distinct_labels:
                        sub_solution.name = "; ".join(distinct_labels)
                    else:
                        sub_solution.name = f"sub_solution_{i}"

class HypothesisTest(BaseModel):
    hypothesis: Fact

    solution_pos: Solution
    solution_neg: Solution

    @property
    def probability(self) -> float:
        return self.solution_pos.prior_prob / (
            self.solution_pos.prior_prob + self.solution_neg.prior_prob
        )

class EvalStats(BaseModel):
    """Evaluation statistics for fact prediction."""

    tp: int  # True positives
    fp: int  # False positives
    fn: int  # False negatives
    tp_list: list[Fact] | None = None
    fp_list: list[Fact] | None = None
    fn_list: list[Fact] | None = None
    precision: float
    recall: float
    f1: float

class GridSearchResult(BaseModel):
    """
    A result of a grid search.
    """
    config: SearchConfig
    result: Solution
    evaluation: EvalStats | None = None
    pr_filter: float | None = None

class GridSearch(BaseModel):
    """
    A grid search is a grid search over a set of hyperparameters.
    """
    configurations: list[SearchConfig]
    configuration_matrix: dict[str, list[Any]] | None = None
    results: list[GridSearchResult] | None = None

    def to_flat_dicts(self) -> dict[str, Any]:
        """
        Convert the grid search to a flat dictionary.
        """
        dict_keys = ["config", "result", "evaluation"]
        objs = []
        for r in self.results:
            obj = r.model_dump()
            for k1 in dict_keys:
                if k1 not in obj:
                    continue
                k1v = obj[k1]
                if not k1v:
                    k1v = {}
                for k2, vs in k1v.items():
                    obj[f"{k1}_{k2}"] = vs
                del obj[k1]
            objs.append(obj)
        return objs
