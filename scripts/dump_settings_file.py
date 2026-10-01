#!/usr/bin/env python
import argparse
from enum import Enum
from pathlib import Path
from types import NoneType
from typing import Any, Literal, Union, get_args, get_origin

import tomlkit
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined
from tomlkit.items import AbstractTable, Comment, Item

from valhalla.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, required=True)
    args = parser.parse_args()

    doc = write_table(Settings)
    with open(args.file, "wb") as f:
        f.write(doc.as_string().encode("utf-8"))


def python_to_tomlkit(val: object) -> Item:
    match val:
        case str():
            return tomlkit.string(val)
        case bool():
            return tomlkit.boolean(val)
        case float():
            return tomlkit.float_(val)
        case int():
            return tomlkit.integer(val)
        case list() | set() | frozenset() | tuple():
            arr = tomlkit.array()
            arr.extend(val)
            return arr
        case dict():
            tbl = tomlkit.inline_table()
            tbl.update(val)
            return tbl
        case _:
            raise ValueError(type(val))


def get_valid_values(
    model: type[BaseModel], f: FieldInfo
) -> list[str | int | bool] | None:

    typ = f.annotation
    if get_origin(typ) in (list, set, frozenset):
        (typ,) = get_args(typ)

    if isinstance(typ, type) and issubclass(typ, Enum):
        # Check the model config for whether to use the enum name or value
        if model.model_config["use_enum_values"]:
            return [e.value for e in typ]
        return [e.name for e in typ]

    if get_origin(typ) is Literal:
        return list(get_args(typ))

    return None


def get_field_description(
    model: type[BaseModel], f: FieldInfo, *, raw: bool = False
) -> str | None:
    descs: list[str] = []
    if f.description:
        descs.extend(f.description.strip().splitlines())

    if (valid_values := get_valid_values(model, f)) is not None:
        valid_text = python_to_tomlkit(valid_values).as_string()
        if descs:
            descs.append("")
        descs.append(f"Valid values: {valid_text}")

    if not descs:
        return None

    if raw:
        return "\n".join(f"# {line}" for line in descs) + "\n"
    return "\n".join(descs) + "\n"


def write_table(model: type[BaseModel]) -> tomlkit.TOMLDocument:
    obj = tomlkit.document()
    if model.__doc__:
        obj.add(tomlkit.comment(model.__doc__.strip()))

    table_encountered = False
    for name, f2 in model.__pydantic_fields__.items():
        if f2.exclude:
            continue

        obj.add(tomlkit.nl())
        name = f2.alias or name

        if write_documented_item(obj, name, model, f2):
            table_encountered = True
        elif table_encountered:
            raise RuntimeError(
                "Encountered non-root value after a table. This would result in a"
                " badly formatted toml file."
            )
    return obj


def union_strip_none(ty: Any) -> Any:  # noqa: ANN401
    """Strips `None` from a `Union`.

    When given a Union, ensures it has only 2 elements and the last item is `None`, then
    returns the first value. When not given a union, it returns the value unmodified.

    Input expects to be `T | None`.
    `NoneType | T` is not supported.
    """
    if get_origin(ty) is Union:
        args = get_args(ty)
        if len(args) > 2:
            raise ValueError(
                "Union had more than 2 elements. Expected it to be `T | None`."
            )
        if args[1] not in (None, NoneType):
            raise ValueError("Union was not `T | None`")
        return args[0]
    return ty


def write_documented_item(
    obj: tomlkit.TOMLDocument,
    name: str,
    model: type[BaseModel],
    field: FieldInfo,
    *,
    typ: Any = ...,  # noqa: ANN401
) -> bool:
    """Returns True when the value would result in a table."""
    if typ is ...:
        typ = field.annotation
    typ = union_strip_none(typ)
    name = field.alias or name

    if isinstance(typ, type) and issubclass(typ, BaseModel):
        # BaseModel fields should get a dedicated table
        tbl = tomlkit.table()
        if desc := get_field_description(typ, field, raw=True):
            tbl.trivia.comment = desc
            tbl.trivia.comment_ws = "\n"
        for n, f in typ.__pydantic_fields__.items():
            name2 = f.alias or n
            write_item_values(tbl, name2, f)
        obj.add(name, tbl)
        return True

    if desc := get_field_description(model, field):
        obj.add(tomlkit.comment(desc))

    write_item_values(obj, name, field)
    return False


def write_item_values(
    tbl: AbstractTable | tomlkit.TOMLDocument, name: str, field: FieldInfo
) -> None:
    """Writes a commented key-value pair to the table"""
    if field.examples:
        for ex in field.examples:
            tbl.add(commented(tomlkit.table().add(name, ex)))

    if field.default not in (None, PydanticUndefined):
        tbl.add(commented(tomlkit.table().add(name, python_to_tomlkit(field.default))))
    else:
        tbl.add(commented(tomlkit.table().add(name, "")))


def commented(item: Item) -> Comment:
    """Converts a `tomlkit.Item` to a comment."""
    return tomlkit.comment(item.as_string().strip())


if __name__ == "__main__":
    main()
