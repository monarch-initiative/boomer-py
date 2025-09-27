from boomer.renderers.renderer import Renderer
from boomer.model import Solution, KB
import json
from typing import Optional


class JSONRenderer(Renderer):
    def render(self, solution: Solution, kb: Optional[KB] = None) -> str:
        obj = solution.as_dict()
        return json.dumps(obj, indent=2)
