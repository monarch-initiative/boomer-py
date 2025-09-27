from boomer.renderers.renderer import Renderer
from boomer.model import Solution, KB
import yaml
from typing import Optional


class YAMLRenderer(Renderer):
    def render(self, solution: Solution, kb: Optional[KB] = None) -> str:
        return yaml.dump(solution.as_dict(), default_flow_style=False, sort_keys=False)
        