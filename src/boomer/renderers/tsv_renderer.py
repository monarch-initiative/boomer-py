from boomer.renderers.renderer import Renderer
from boomer.model import Solution, KB
import csv
from io import StringIO
import datetime
from typing import Optional


class TSVRenderer(Renderer):
    def render(self, solution: Solution, kb: Optional[KB] = None) -> str:
        output = StringIO()

        # Write SSSOM-style YAML metadata header
        output.write("# BOOMER Solution TSV Output\n")
        output.write("#\n")
        output.write("# Metadata:\n")
        output.write(f"#   generated_date: {datetime.datetime.now().isoformat()}\n")
        output.write(f"#   combinations: {solution.number_of_combinations}\n")
        output.write(
            f"#   satisfiable_combinations: {solution.number_of_satisfiable_combinations}\n"
        )
        output.write(f"#   confidence: {solution.confidence}\n")
        output.write(f"#   prior_probability: {solution.prior_prob}\n")
        output.write(f"#   posterior_probability: {solution.posterior_prob}\n")
        if solution.time_elapsed is not None:
            output.write(f"#   time_elapsed_seconds: {solution.time_elapsed}\n")
        output.write(f"#   timed_out: {solution.timed_out}\n")
        output.write("#\n")
        output.write(
            "# Format: fact_type followed by arguments, then truth_value and probabilities\n"
        )
        output.write("#\n")

        writer = csv.writer(output, delimiter="\t")

        # Determine maximum number of arguments across all facts
        max_args = 0
        for spf in solution.solved_pfacts:
            fact = spf.pfact.fact
            args = self._extract_fact_args(fact)
            max_args = max(max_args, len(args))

        # Determine if we have labels to include
        has_labels = kb is not None and kb.labels

        # Write header with dynamic number of argument columns
        header = ["fact_type"]
        for i in range(max_args):
            header.append(f"arg{i + 1}")

        # Add label columns if labels are available
        if has_labels:
            for i in range(max_args):
                header.append(f"arg{i + 1}_label")

        header.extend(["truth_value", "prior_probability", "posterior_probability"])
        writer.writerow(header)

        # Write fact data
        for spf in solution.solved_pfacts:
            fact = spf.pfact.fact
            fact_type = fact.__class__.__name__
            args = self._extract_fact_args(fact)

            # Pad args to max_args length
            padded_args = args + [""] * (max_args - len(args))

            # Build the row starting with fact_type and args
            row = [fact_type] + padded_args

            # Add labels if available
            if has_labels:
                labels = []
                for arg in padded_args:
                    if arg and kb.labels.get(arg):
                        labels.append(kb.labels[arg])
                    else:
                        labels.append("")
                row.extend(labels)

            # Add the final columns
            row.extend([spf.truth_value, spf.pfact.prob, spf.posterior_prob])
            writer.writerow(row)

        return output.getvalue()

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
            # Fallback: extract all field values from dataclass if available
            if hasattr(fact, "__dataclass_fields__"):
                return [
                    str(getattr(fact, field.name))
                    for field in fact.__dataclass_fields__.values()
                ]
            else:
                # Last resort: convert to string
                return [str(fact)]
