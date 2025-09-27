from math import prod
from pydantic import BaseModel
from boomer.model import Solution
from copy import deepcopy
from typing import Any, List


AGGS = {
    "ground_pfacts": "concat",
    "solved_pfacts": "concat",
    "number_of_combinations": "sum",
    "number_of_satisfiable_combinations": "sum",
    "number_of_combinations_explored_including_implicit": "sum",
    "proportion_of_combinations_explored": "product",
    "time_started": "min",
    "time_finished": "max",
    "confidence": "product",
    "prior_prob": "product",
    "posterior_prob": "product",
}

def aggegate_objects(objects: List[BaseModel|dict], field_aggs: dict[str, str]) -> BaseModel | dict:
    """
    Aggregate a list of objects into a single object.

    Args:
        objects: List of objects to aggregate
        field_aggs: Dictionary of field names and aggregation functions

    Returns:
        Aggregated object

    Example:

        >>> aggegate_objects([{"x": 1}, {"x": 2}], {"x": "sum"})
        {'x': 3}

        >>> aggegate_objects([{"x": 1}, {"x": 2}], {"x": "product"})
        {'x': 2}

        >>> aggegate_objects([{"x": 1}, {"x": 2}], {"x": "min"})
        {'x': 1}

        >>> aggegate_objects([{"x": 1}, {"x": 2}], {"x": "max"})
        {'x': 2}
    """

    def _get_field(obj: BaseModel|dict, field: str) -> Any:
        if isinstance(obj, BaseModel):
            return getattr(obj, field)
        return obj[field]

    new_object = {}
    for field, agg in field_aggs.items():
        if agg == "concat":
            new_object[field] = []
            for obj in objects:
                new_object[field].extend(_get_field(obj, field))
        elif agg == "sum":
            new_object[field] = sum(_get_field(obj, field) for obj in objects)
        elif agg == "min":
            new_object[field] = min(_get_field(obj, field) for obj in objects)
        elif agg == "max":
            new_object[field] = max(_get_field(obj, field) for obj in objects)
        elif agg == "product":
            new_object[field] = prod(_get_field(obj, field) for obj in objects)
        else:
            raise ValueError(f"Invalid aggregation function: {agg}")
    if isinstance(objects[0], BaseModel):
        return type(objects[0])(**new_object)
    return new_object


def combine_solutions(solutions: List[Solution]) -> Solution:
    """
    Combine a list of solutions into a single solution.
    """
    base_solution = aggegate_objects(solutions, AGGS)
    base_solution.number_of_components = sum(s.number_of_components if s.number_of_components else 1 for s in solutions)
    base_solution.sub_solutions = solutions
    return base_solution