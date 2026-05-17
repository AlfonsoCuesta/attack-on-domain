from ...domain_exception import MutationForbiddenError


class ImmutableDict(dict):
    __immutable_class__ = dict

    @classmethod
    def from_dict(cls, data: dict) -> "ImmutableDict":
        obj = super().__new__(cls)
        dict.update(obj, data)
        return obj

    def _raise(self, *args, **kwargs):
        raise MutationForbiddenError("Cannot modify an immutable dict")

    __setitem__ = __delitem__ = update = _raise
    pop = popitem = clear = setdefault = _raise
