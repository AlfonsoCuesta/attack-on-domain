from typing import Any, NoReturn

from ...domain_exception import MutationForbiddenException
from ._helpers import identity


class ImmutableSet(set):
    __immutable_class__ = set

    def __init__(self, data: set[Any], factory: Any = identity) -> None:
        super().__init__(data)
        self.__factory__ = factory

    def _block_mutation(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise MutationForbiddenException("Cannot modify an immutable set")

    add = discard = remove = _block_mutation
    pop = clear = update = _block_mutation
    __ior__ = __iand__ = __ixor__ = __isub__ = _block_mutation

    def __iter__(self) -> Any:
        for item in super().__iter__():
            yield self.__factory__(item)
