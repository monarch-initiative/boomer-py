from copy import deepcopy
from typing import List
from collections import defaultdict
from boomer.model import KB, EquivalentTo, PFact, ProbabilityMissingEquivalentTo, ProbabilityMissingProperSubClassOf, Fact, MemberOfDisjointGroup, ProperSubClassOf, SubClassOf
from boomer.reasoners.reasoner import Reasoner

def generate_hypotheses_for_hyperparamaters(kb: KB, reasoner: Reasoner) -> List[PFact]:
    """
    Generate hypotheses for the hyperparamaters.

    Args:
        kb: The knowledge base
        reasoner: The reasoner to use

    Returns:
        A list of hypotheses for the hyperparamaters

    Example:
        >>> facts=[MemberOfDisjointGroup(sub="a", group="g1"), MemberOfDisjointGroup(sub="b", group="g1"), MemberOfDisjointGroup(sub="c", group="g2"), MemberOfDisjointGroup(sub="d", group="g2")]
        >>> hyperparams1=[ProbabilityMissingProperSubClassOf(prob=0.2, disjoint_group_sub="g1", disjoint_group_sup="g1")]
        >>> hyperparams2=[ProbabilityMissingProperSubClassOf(prob=0.1, disjoint_group_sub="g2", disjoint_group_sup="g2")]
        >>> kb = KB(facts=facts, hyperparams=hyperparams1 + hyperparams2)
        >>> from boomer.reasoners.nx_reasoner import NxReasoner
        >>> reasoner = NxReasoner()
        >>> for pfact in sorted(generate_hypotheses_for_hyperparamaters(kb, reasoner), key=lambda x: x.prob):
        ...     print(pfact)
        fact=ProperSubClassOf(fact_type='ProperSubClassOf', sub='c', sup='d') prob=0.1
        fact=ProperSubClassOf(fact_type='ProperSubClassOf', sub='d', sup='c') prob=0.1
        fact=ProperSubClassOf(fact_type='ProperSubClassOf', sub='a', sup='b') prob=0.2
        fact=ProperSubClassOf(fact_type='ProperSubClassOf', sub='b', sup='a') prob=0.2
    """
    hypotheses = []
    entity_to_disjoint_groups = defaultdict(list)
    disjoint_groups_to_entities = defaultdict(list)
    all_entities = set()
    for fact in kb.facts:
        if isinstance(fact, MemberOfDisjointGroup):
            all_entities.add(fact.sub)
            all_entities.add(fact.group)
        elif isinstance(fact, (ProperSubClassOf, SubClassOf)):
            all_entities.add(fact.sub)
            all_entities.add(fact.sup)
        elif isinstance(fact, EquivalentTo):
            all_entities.add(fact.sub)
            all_entities.add(fact.equivalent)
    for fact in kb.facts:
        if isinstance(fact, MemberOfDisjointGroup):
            entity_to_disjoint_groups[fact.sub].append(fact.group)
            disjoint_groups_to_entities[fact.group].append(fact.sub)
    for hp in kb.hyperparams:
        if isinstance(hp, ProbabilityMissingProperSubClassOf):
            for i in disjoint_groups_to_entities.get(hp.disjoint_group_sub, []):
                for j in disjoint_groups_to_entities.get(hp.disjoint_group_sup, []):
                    if i != j:
                        hypotheses.append(PFact(fact=ProperSubClassOf(sub=i, sup=j), prob=hp.prob))
        elif isinstance(hp, ProbabilityMissingEquivalentTo):
            for i in disjoint_groups_to_entities.get(hp.disjoint_group_sub, []):
                for j in disjoint_groups_to_entities.get(hp.disjoint_group_equivalent, []):
                    if i != j:
                        hypotheses.append(PFact(fact=EquivalentTo(sub=i, equivalent=j), prob=hp.prob))
            
    existing_hypotheses = {h.fact: h for h in kb.pfacts}
    # find all entailments in the KB
    kb_copy = deepcopy(kb)
    kb_copy.pfacts = hypotheses
    reasoner_result = reasoner.reason(kb_copy)
    if not reasoner_result.satisfiable:
        return []
    
    remove_facts = []
    for ix, _tv in reasoner_result.entailed_selections:
        fact = kb_copy.pfacts[ix].fact
        remove_facts.append(fact)
    
    unentailed_hypotheses = []
    for h in hypotheses:
        if h.fact in existing_hypotheses:
            continue
        if h.fact not in remove_facts:
            unentailed_hypotheses.append(h)
    return unentailed_hypotheses