from ...domain_exception import MutationForbiddenException


def _identity(value):
    return value


class ImmutableSet(set):
    __immutable_class__ = set

    def __init__(self, data: set, factory=_identity):
        set.update(self, data)
        self.__factory__ = factory

    def _raise(self, *args, **kwargs):
        raise MutationForbiddenException("Cannot modify an immutable set")

    add = discard = remove = _raise
    pop = clear = update = _raise
    __ior__ = __iand__ = __ixor__ = __isub__ = _raise

    def __iter__(self):
        for item in super().__iter__():
            yield self.__factory__(item)
