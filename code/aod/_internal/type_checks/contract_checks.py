from typing import get_args

from aod._internal.domain.entity import RootEntity


def extract_root_entity(repo: object) -> type | None:
    for base in getattr(type(repo), "__orig_bases__", ()):
        for arg in get_args(base):
            if isinstance(arg, type) and issubclass(arg, RootEntity):
                return arg
    return None
