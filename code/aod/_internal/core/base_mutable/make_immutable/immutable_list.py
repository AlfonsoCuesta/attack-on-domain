from ...domain_exception import MutationForbiddenError


class ImmutableList(list):
    @classmethod
    def from_list(cls, data: list) -> "ImmutableList":
        obj = super().__new__(cls)
        list.extend(obj, data)
        return obj

    def _raise(self, *args, **kwargs):
        raise MutationForbiddenError("Cannot modify an immutable list")

    append = extend = insert = remove = _raise
    pop = clear = sort = reverse = _raise
    __setitem__ = __delitem__ = __iadd__ = __imul__ = _raise
