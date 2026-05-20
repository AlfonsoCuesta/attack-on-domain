from ...domain_exception import MutationForbiddenException


class ImmutableSet(set):
    __immutable_class__ = set

    @classmethod
    def from_set(cls, data: set, factory) -> "ImmutableSet":
        obj = super().__new__(cls)
        set.update(obj, data)
        obj.__factory__ = factory
        return obj

    def _raise(self, *args, **kwargs):
        raise MutationForbiddenException("Cannot modify an immutable set")

    add = discard = remove = _raise
    pop = clear = update = _raise
    __ior__ = __iand__ = __ixor__ = __isub__ = _raise
