from typing import Any, Callable

from ...domain_exception import MutationForbiddenException


class ImmutableList(list):
    __immutable_class__ = list

    def __init__(self, items: Any, factory: Callable):
        super().__init__(items)
        self.__factory__ = factory

    def _block_mutation(self, *args, **kwargs):
        raise MutationForbiddenException("Cannot modify an immutable list")

    append = extend = insert = remove = _block_mutation
    pop = clear = sort = reverse = _block_mutation
    __setitem__ = __delitem__ = __iadd__ = __imul__ = _block_mutation

    def __getitem__(self, key):
        item = super().__getitem__(key)
        if isinstance(key, slice):
            return type(self)(item, self.__factory__)
        return self.__factory__(item)

    def __iter__(self):
        for item in super().__iter__():
            yield self.__factory__(item)
