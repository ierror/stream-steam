import re

RE_CAMELCASE_TO_DASHED = re.compile(r"(?<!^)(?=[A-Z][^A-Z]+)")


def dashed_to_camel_case(dashed_str):
    """
    e.g. foo-bar => FooBar
    """
    components = dashed_str.split("-")
    return components[0].capitalize() + "".join(x.title() for x in components[1:])


def camel_case_to_dashed(camel_str):
    """
    e.g. FooBar => foo-bar
    """
    return RE_CAMELCASE_TO_DASHED.sub("-", camel_str).lower()
