from ...domain_exception import MutationForbiddenError


class ImmutableSet(set):
    @classmethod
    def from_set(cls, data: set) -> "ImmutableSet":
        obj = super().__new__(cls)
        set.update(obj, data)
        return obj

    def _raise(self, *args, **kwargs):
        raise MutationForbiddenError("Cannot modify an immutable set")

    add = discard = remove = _raise
    pop = clear = update = _raise
    __ior__ = __iand__ = __ixor__ = __isub__ = _raise
