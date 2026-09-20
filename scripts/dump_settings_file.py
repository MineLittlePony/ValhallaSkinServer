#!/usr/bin/env python
import argparse
from enum import Enum
from pathlib import Path
from typing import Literal, Union, get_args, get_origin

import tomlkit
from pydantic import BaseModel
from tomlkit.items import Item

from valhalla.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path)
    args = parser.parse_args()

    doc = write_table(Settings(_build_sources=((), {})))
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


def write_table(model: BaseModel) -> tomlkit.TOMLDocument:
    obj = tomlkit.document()
    for name, f2 in model.__pydantic_fields__.items():
        if f2.exclude:
            continue

        obj.add(tomlkit.nl())
        n = f2.alias or name
        if f2.description:
            obj.add(tomlkit.comment(f2.description.strip() + "\n"))

        typ = f2.annotation
        if get_origin(typ) in (list, set, frozenset):
            (typ,) = get_args(typ)

        # Calculate the valid values for this field
        if isinstance(typ, type) and issubclass(typ, Enum):
            if model.model_config["use_enum_values"]:
                valid_values = [e.value for e in typ]
            else:
                valid_values = [e.name for e in typ]
        elif get_origin(typ) is Literal:
            valid_values = list(get_args(typ))
        else:
            valid_values = None

        if valid_values is not None:
            valid_text = python_to_tomlkit(valid_values).as_string()
            obj.add(tomlkit.comment(f"Valid values: {valid_text}"))

        if f2.examples:
            for example in f2.examples:
                example_string = python_to_tomlkit(example).as_string()
                obj.add(tomlkit.comment(f"{n} = {example_string}"))

        default_value = getattr(model, name)
        if default_value is None and get_origin(typ) is Union:
            for arg in get_args(typ):
                if arg is str:
                    obj.add(tomlkit.comment(f'{n} = ""'))
                    break
        else:
            default_text = python_to_tomlkit(default_value).as_string()
            obj.add(tomlkit.comment(f"{n} = {default_text}"))

    return obj


if __name__ == "__main__":
    main()
