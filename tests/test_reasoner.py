from copy import deepcopy
import pytest
from boomer.model import KB, DisjointWith, DisjointSet, MemberOfDisjointGroup, NegatedFact, NotInSubsumptionWith, OneOf, SubClassOf, PFact, SearchConfig, ProperSubClassOf, EquivalentTo
from boomer.search import search, solve
import boomer.datasets.animals as animals
import boomer.datasets.quad as quad
from boomer.reasoners.nx_reasoner import NxReasoner

def test_nx_reasoner_main():
    kb = animals.kb
    reasoner = NxReasoner()
    all_facts_as_true = [(i, True) for i in range(0, len(kb.pfacts))]
    # print(all_facts_as_true)
    result = reasoner.reason(kb, all_facts_as_true)
    # print(result)
    assert not result.satisfiable
    result = reasoner.reason(kb, [])
    assert result.satisfiable

@pytest.mark.parametrize("facts,satisfiable,entailed,not_entailed", [
    ([], True, [], []),
    ([ProperSubClassOf(sub="Felix", sup="Mammalia")], True, [SubClassOf(sub="Felix", sup="Mammalia")], []), # no change
    ([ProperSubClassOf(sub="Mammalia", sup="Felix")], False, [], []), # cycle
    ([EquivalentTo(sub="cat", equivalent="dog")], False, [EquivalentTo(sub="dog", equivalent="cat")], []), # disjointness
    ([EquivalentTo(sub="cat", equivalent="Felix")], True, [EquivalentTo(sub="cat", equivalent="Felix")], []), # valid
    ([SubClassOf(sub="X", sup="Y"), NegatedFact(negated=SubClassOf(sub="X", sup="Y"))], False, [], []), # assert negated fact
    ([EquivalentTo(sub="cat", equivalent="Felix"), EquivalentTo(sub="dog", equivalent="Canus"), EquivalentTo(sub="furry_animal", equivalent="Mammalia")], 
     True, 
     [EquivalentTo(sub="cat", equivalent="Felix"), EquivalentTo(sub="dog", equivalent="Canus"), EquivalentTo(sub="furry_animal", equivalent="Mammalia")], 
     []
     ), # valid
    ([EquivalentTo(sub="cat", equivalent="Felix"), EquivalentTo(sub="dog", equivalent="Canus"), EquivalentTo(sub="furry_animal", equivalent="Mammalia"), SubClassOf(sub="furry_animal", sup="dog")], 
     False, 
     [], 
     []
     ), # ivvalid

])
def test_nx_reasoner_animal_combos(facts, satisfiable, entailed, not_entailed):
    kb = deepcopy(animals.kb)
    kb.pfacts = [PFact(fact=fact, prob=1.0) for fact in facts] + [PFact(fact=fact, prob=0.5) for fact in entailed] + [PFact(fact=fact, prob=0.5) for fact in not_entailed]
    reasoner = NxReasoner()
    result = reasoner.reason(kb, [(kb.pfact_index(fact), True) for fact in facts])
    assert result.satisfiable == satisfiable
    print(result.entailed_selections)
    entailed_facts = [kb.pfacts[ix].fact for ix, tv in result.entailed_selections]
    for f in entailed:
        assert f in entailed_facts
    not_entailed_facts = [kb.pfacts[ix].fact for ix, tv in result.entailed_selections if tv == False]
    for f in not_entailed:
        assert f not in entailed_facts

@pytest.mark.parametrize("asserted_facts,satisfiable,expected_entailed,expected_not_entailed", [
    ([], True, [], []),
    ([ProperSubClassOf(sub="a", sup="b")], True, [SubClassOf(sub="a", sup="b")], []), # subproperty
    ([SubClassOf(sub="a", sup="b")], True, [], [ProperSubClassOf(sub="a", sup="b")]), # strict does NOT entail lax
    ([ProperSubClassOf(sub="a", sup="b")], True, [SubClassOf(sub="a", sup="b")], [EquivalentTo(sub="a", equivalent="b")]),
    ([ProperSubClassOf(sub="a", sup="b")], True, [NegatedFact(negated=EquivalentTo(sub="a", equivalent="b"))], [EquivalentTo(sub="a", equivalent="b")]),
    # ([SubClassOf("a", "b"), NegatedFact(EquivalentTo("a", "b"))], True, [ProperSubClassOf("a", "b")], []),
    ([ProperSubClassOf(sub="a", sup="b"), ProperSubClassOf(sub="b", sup="a")], False, [], []), # cycle
    ([SubClassOf(sub="a", sup="b"), EquivalentTo(sub="a", equivalent="a2"), EquivalentTo(sub="b", equivalent="b2")], True, [SubClassOf(sub="a2", sup="b2")], []), # ladder entailment
    ([SubClassOf(sub="a", sup="b"), EquivalentTo(sub="a", equivalent="a2"), EquivalentTo(sub="b", equivalent="b2")], True, [], [ProperSubClassOf(sub="a2", sup="b2")]), # properness NOT entailed without UNA
    ([SubClassOf(sub="a", sup="b"), EquivalentTo(sub="a", equivalent="a2"), EquivalentTo(sub="b", equivalent="b2"), 
      #MemberOfDisjointGroup(sub="a", group="1"), MemberOfDisjointGroup(sub="b", group="1"), 
      MemberOfDisjointGroup(sub="a2", group="2"), MemberOfDisjointGroup(sub="b2", group="2"),
      ], True, [ProperSubClassOf(sub="a2", sup="b2")], []), # properness IS entailed *with* UNA
    ([SubClassOf(sub="a", sup="b"), SubClassOf(sub="b", sup="a")], True, [EquivalentTo(sub="a", equivalent="b")], []), # cycle
    ([SubClassOf(sub="a", sup="b"), SubClassOf(sub="b", sup="c"), SubClassOf(sub="c", sup="a")], True, [EquivalentTo(sub="a", equivalent="b"), EquivalentTo(sub="b", equivalent="c"), EquivalentTo(sub="c", equivalent="a")], []), # 3-cycle
    ([SubClassOf(sub="a", sup="b"), SubClassOf(sub="b", sup="c")], True, [SubClassOf(sub="a", sup="c")], []), # transitive
    ([EquivalentTo(sub="a", equivalent="b"),], True, [EquivalentTo(sub="b", equivalent="a")], []), # symmetry
    ([EquivalentTo(sub="a", equivalent="b"), EquivalentTo(sub="b", equivalent="c")], True, [EquivalentTo(sub="a", equivalent="c"), EquivalentTo(sub="c", equivalent="a")], []), # transitive
    ([EquivalentTo(sub="a", equivalent="b"), EquivalentTo(sub="c", equivalent="b")], True, [EquivalentTo(sub="a", equivalent="c"), EquivalentTo(sub="c", equivalent="a")], []), # transitive
    ([SubClassOf(sub="c", sup="p1"), SubClassOf(sub="c", sup="p2"), DisjointWith(sub="p1", sibling="p2")], False, [], []), # disjointness
    ([SubClassOf(sub="c1", sup="p"), SubClassOf(sub="c2", sup="p"), DisjointWith(sub="c1", sibling="c2")], True, [], []), # disjointness
    # ([SubClassOf("a", "b"), OneOf("b", "c")], True, [SubClassOf("a", "!c")], []), # oneof
    ([SubClassOf(sub="a", sup="b"), NotInSubsumptionWith(sub="a", sibling="b")], False, [], []), 
    ([SubClassOf(sub="b", sup="a"), NotInSubsumptionWith(sub="a", sibling="b")], False, [], []), 
    ([ProperSubClassOf(sub="a", sup="b"), NotInSubsumptionWith(sub="a", sibling="b")], False, [], []), 
    ([EquivalentTo(sub="a", equivalent="b"), NotInSubsumptionWith(sub="a", sibling="b")], False, [], []), 
    ([SubClassOf(sub="a", sup="b"), SubClassOf(sub="b", sup="c"),  NotInSubsumptionWith(sub="a", sibling="c")], False, [], []), 
    ([SubClassOf(sub="a", sup="b"), SubClassOf(sub="a", sup="c"), NotInSubsumptionWith(sub="b", sibling="c")], True, [], []), 
    # DisjointSet tests
    ([DisjointSet(entities=("a", "b", "c"))], True, [], []), # Just the disjoint constraint itself
    ([DisjointSet(entities=("a", "b", "c")), EquivalentTo(sub="a", equivalent="b")], False, [], []), # Violates disjointness
    ([DisjointSet(entities=("a", "b", "c")), SubClassOf(sub="x", sup="a"), SubClassOf(sub="x", sup="b")], False, [], []), # Common subclass violates disjointness
    ([DisjointSet(entities=("a", "b")), SubClassOf(sub="a", sup="p"), SubClassOf(sub="b", sup="p")], True, [], []), # Disjoint classes can have common superclass
    ([DisjointSet(entities=("a", "b", "c")), ProperSubClassOf(sub="a", sup="b")], False, [], []), # Subclass relation violates disjointness
        

])
def test_nx_reasoner_main_combos(asserted_facts, satisfiable, expected_entailed, expected_not_entailed):
    kb = KB()
    kb.pfacts = [PFact(fact=fact, prob=1.0) for fact in asserted_facts] + [PFact(fact=fact, prob=0.5) for fact in expected_entailed] + [PFact(fact=fact, prob=0.5) for fact in expected_not_entailed]
    reasoner = NxReasoner()
    result = reasoner.reason(kb, [(kb.pfact_index(fact), True) for fact in asserted_facts])
    assert result.satisfiable == satisfiable
    print(result.entailed_selections)
    if satisfiable:
        entailed_facts = {kb.pfacts[ix].fact for ix, tv in result.entailed_selections if tv == True}
        not_entailed_facts = {kb.pfacts[ix].fact for ix, tv in result.entailed_selections if tv == False}
        expected_entailed = set(expected_entailed).union(asserted_facts)
        expected_not_entailed = set(expected_not_entailed)
        assert entailed_facts == expected_entailed
        # TODO: assert not_entailed_facts is currently a mix of
        # (a) hypotheses that are not expected to be entailed but NOT disproven 
        # (b) hypotheses that are expected to be disproven
        #assert not_entailed_facts == expected_not_entailed

