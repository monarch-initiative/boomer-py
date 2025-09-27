from boomer.renderers.renderer import Renderer
from boomer.model import Solution, KB
from typing import Optional


class MarkdownRenderer(Renderer):
    def render(self, solution: Solution, kb: Optional[KB] = None) -> str:
        s = (
            f"\n ## {solution.name}"
            f"\n * {solution.number_of_combinations} combinations"
            f"\n * {solution.number_of_satisfiable_combinations} satisfiable combinations"
            f"\n * {solution.proportion_of_combinations_explored} proportion of combinations explored"
            f"\n * {solution.confidence} confidence"
            f"\n * {solution.prior_prob} prior probability"
            f"\n * {solution.posterior_prob} posterior probability"
        )

        # Add timing information if available
        if solution.time_elapsed is not None:
            s += f"\n * {solution.time_elapsed:.4f} seconds elapsed"

        # Add timeout information if search timed out
        if solution.timed_out:
            s += "\n * Search timed out (exceeded time limit)"

        s += "\nGrounding:\n"
        for spf in solution.solved_pfacts:
            fact_str = self._format_fact_with_labels(spf.pfact.fact, kb)
            s += f" * {spf.truth_value} {fact_str} :: prior: {spf.pfact.prob} posterior: {spf.posterior_prob}\n"
        return s

    def _format_fact_with_labels(self, fact, kb: Optional[KB]) -> str:
        """Format a fact with labels if available."""
        if kb is None or not kb.labels:
            return str(fact)

        # Get the base string representation
        fact_str = str(fact)

        # Extract entity identifiers from the fact and add labels
        args = self._extract_fact_args(fact)
        if args:
            labeled_parts = []
            for arg in args:
                if arg and kb.labels.get(arg):
                    labeled_parts.append(f"{arg} ({kb.labels[arg]})")
                else:
                    labeled_parts.append(str(arg))

            # For common fact types, format nicely
            fact_type = fact.__class__.__name__
            if (
                fact_type in ["SubClassOf", "ProperSubClassOf"]
                and len(labeled_parts) >= 2
            ):
                return f"{labeled_parts[0]} ⊆ {labeled_parts[1]}"
            elif fact_type == "EquivalentTo" and len(labeled_parts) >= 2:
                return f"{labeled_parts[0]} ≡ {labeled_parts[1]}"
            elif fact_type == "DisjointWith" and len(labeled_parts) >= 2:
                return f"{labeled_parts[0]} ⊥ {labeled_parts[1]}"
            elif fact_type == "MemberOfDisjointGroup" and len(labeled_parts) >= 2:
                return f"{labeled_parts[0]} ∈ group:{labeled_parts[1]}"
            else:
                # Fallback to the original string representation
                return fact_str

        return fact_str

    def _extract_fact_args(self, fact) -> list:
        """Extract arguments from a fact in order based on fact type."""
        fact_type = fact.__class__.__name__

        if fact_type in ["SubClassOf", "ProperSubClassOf"]:
            return [fact.sub, fact.sup]
        elif fact_type == "EquivalentTo":
            return [fact.sub, fact.equivalent]
        elif fact_type in ["DisjointWith", "OneOf", "NotInSubsumptionWith"]:
            return [fact.sub, fact.sibling]
        elif fact_type == "MemberOfDisjointGroup":
            return [fact.sub, fact.group]
        elif fact_type == "NegatedFact":
            return [str(fact.negated)]
        elif fact_type == "DisjointSet":
            return list(fact.entities)
        else:
            return []
