# Renderers API Reference

This page documents the renderers used in BOOMER to format and display solutions.

## Renderer Interface

```python
class Renderer(ABC):
    """Abstract base class for renderers."""
    
    @abstractmethod
    def render(self, solution: Solution) -> str:
        """
        Render a solution as a string.
        
        Args:
            solution: The solution to render
            
        Returns:
            A string representation of the solution
        """
        pass
```

## MarkdownRenderer

```python
class MarkdownRenderer(Renderer):
    """
    Renderer that formats solutions as Markdown.
    
    This renderer is useful for displaying solutions in a human-readable
    format that can be displayed in Markdown viewers or converted to
    other formats.
    """

    def render(self, solution: Solution) -> str:
        """
        Render a solution as Markdown.
        
        Args:
            solution: The solution to render
            
        Returns:
            A Markdown string representation of the solution
        """
```

## Usage Example

```python
from boomer.model import KB, PFact, EquivalentTo
from boomer.search import solve
from boomer.renderers.markdown_renderer import MarkdownRenderer

# Create a knowledge base
kb = KB(
    pfacts=[
        PFact(fact=EquivalentTo(sub="A", equivalent="B"), prob=0.9),
        PFact(fact=EquivalentTo(sub="B", equivalent="C"), prob=0.8),
    ]
)

# Solve the knowledge base
solution = solve(kb)

# Create a renderer
renderer = MarkdownRenderer()

# Render the solution
markdown_output = renderer.render(solution)
print(markdown_output)
```

## Creating Custom Renderers

To create a custom renderer, implement the `Renderer` interface:

```python
from boomer.renderers.renderer import Renderer
from boomer.model import Solution

class JSONRenderer(Renderer):
    """Renderer that formats solutions as JSON."""
    
    def render(self, solution: Solution) -> str:
        """
        Render a solution as JSON.
        
        Args:
            solution: The solution to render
            
        Returns:
            A JSON string representation of the solution
        """
        import json
        
        # Convert solution to a dictionary
        result = {
            "confidence": solution.confidence,
            "prior_probability": solution.prior_prob,
            "posterior_probability": solution.posterior_prob,
            "combinations_explored": solution.number_of_combinations,
            "satisfiable_combinations": solution.number_of_satisfiable_combinations,
            "time_elapsed": solution.time_elapsed,
            "facts": []
        }
        
        # Add facts to the result
        for spf in solution.solved_pfacts:
            if spf.truth_value:
                result["facts"].append({
                    "fact": str(spf.pfact.fact),
                    "prior": spf.pfact.prob,
                    "posterior": spf.posterior_prob
                })
        
        # Return as formatted JSON
        return json.dumps(result, indent=2)
```

This example shows how to create a custom renderer that outputs JSON. You can create renderers for any format you need, such as HTML, CSV, or specialized formats for integration with other tools.