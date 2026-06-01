from ...domain_exception import MutationForbiddenException
from ._helpers import identity


class ImmutableSet(set):
    __immutable_class__ = set

    def __init__(self, data: set, factory=identity):
        super().__init__(data)
        self.__factory__ = factory

    def _block_mutation(self, *args, **kwargs):
        raise MutationForbiddenException("Cannot modify an immutable set")

    add = discard = remove = _block_mutation
    pop = clear = update = _block_mutation
    __ior__ = __iand__ = __ixor__ = __isub__ = _block_mutation

    def __iter__(self):
        for item in super().__iter__():
            yield self.__factory__(item)
