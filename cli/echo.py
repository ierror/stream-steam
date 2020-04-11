from click import echo, secho

from .colors import ERROR, PRIMARY, SUCCESS, WARNING


def h1(text):
    secho(f"\n## {text}", fg=PRIMARY)


def enum_elm(text, nl=True, dash_color=SUCCESS):
    prefix_char = "-"
    if dash_color == ERROR:
        prefix_char = "x"
    elif dash_color == WARNING:
        prefix_char = "~"
    secho(f"{prefix_char} ", fg=dash_color, nl=False)
    echo(f"{text}", nl=nl)


def info(text, nl=True):
    echo(text, nl=nl)


def success(text, nl=True):
    secho(text, fg=SUCCESS, nl=nl)


def warning(text, nl=True):
    secho(text, fg=WARNING, nl=nl)


def error(text, nl=True):
    secho(f"\n## Error", fg=ERROR)
    enum_elm(f"{text}\n", nl=nl, dash_color=ERROR)
