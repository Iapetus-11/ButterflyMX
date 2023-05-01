from __future__ import annotations

import abc
import json
from typing import Any, Sequence

DEFAULT_INDENTATION = 2


class AbstractBuilder(abc.ABC):
    @abc.abstractmethod
    def render(self, *, indent: int = DEFAULT_INDENTATION, depth: int = 1) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError


def render_fields(
    *,
    fields: Sequence[str | AbstractBuilder],
    depth: int,
    indent: int,
) -> str:
    indent_str = ' ' * (depth * indent)

    return '\n'.join(
        indent_str + (f.render(depth=(depth + 1)) if isinstance(f, AbstractBuilder) else f)
        for f in fields
    )


def render_dict(
    *,
    fields: dict[str, str | dict[str, Any]],
    depth: int,
    indent: int,
    root: bool = False,
) -> str:
    depth -= root

    indent_str = ' ' * (depth * indent)

    def render_field(value: Any) -> str:
        return render_dict(
            fields=value,
            depth=(depth + 1),
            indent=indent
        ) if isinstance(value, dict) else json.dumps(value)

    rendered = render_fields(
        fields=[
            f'{k}: {render_field(v)}'
            for k, v in fields.items()
        ],
        depth=depth,
        indent=indent,
    )

    if root:
        return rendered

    return f'{{\n{rendered}\n{indent_str[:indent * (depth - 1)]}}}'


class Q(AbstractBuilder):
    def __init__(
        self,
        fields: Sequence[str | AbstractBuilder] | str | AbstractBuilder | None = None,
        name: str = 'query',
    ):
        self.fields: Sequence[str | AbstractBuilder] = (
            [fields] if isinstance(fields, (str, AbstractBuilder)) else (fields or [])
        )
        self.name = name

    def render(self, *, depth: int = 1, indent: int = DEFAULT_INDENTATION) -> str:
        indent_str = ' ' * (depth * indent)

        fields = render_fields(fields=self.fields, depth=depth, indent=indent)

        return f'{self.name} {{\n{fields}\n{indent_str[:(depth - 1) * indent]}}}'

    def __str__(self) -> str:
        return self.render()


class Func(AbstractBuilder):
    def __init__(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        selections: Sequence[str | Q] | None = None,
    ):
        self.name = name
        self.arguments = arguments or {}
        self.selections = selections or []

    def render(self, *, depth: int = 1, indent: int = DEFAULT_INDENTATION) -> str:
        indent_str = ' ' * (depth * indent)

        rendered_arguments = render_dict(
            fields=self.arguments,
            depth=depth,
            indent=indent,
            root=True,
        ).lstrip()

        rendered_selections = render_fields(fields=self.selections, depth=depth, indent=indent)

        return (
            f'{self.name}({rendered_arguments}) {{\n{rendered_selections}\n'
            f'{indent_str[:(depth - 1) * indent]}}}'
        )

    def __str__(self) -> str:
        return self.render()
