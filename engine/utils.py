def to_camel_case(snake_str):
    components = snake_str.split("-")
    return components[0].capitalize() + "".join(x.title() for x in components[1:])
