import importlib

from boomer.reasoners.reasoner import Reasoner


def get_reasoner(reasoner_class: str) -> Reasoner:
    """
    Get a reasoner from a class name.

    Example:

        >>> cls = "boomer.reasoners.nx_reasoner.NxReasoner"
        >>> reasoner = get_reasoner(cls)
    """
    # the class name is the last part of the module name; previous parts are the package name
    # split the class name by '.' and take the last part
    package_name, class_name = reasoner_class.rsplit(".", 1)
    # import the module
    module = importlib.import_module(package_name)
    # get the class
    cls = getattr(module, class_name)
    return cls()
