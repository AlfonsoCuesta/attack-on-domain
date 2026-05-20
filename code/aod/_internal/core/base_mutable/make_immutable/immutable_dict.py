from ...domain_exception import MutationForbiddenException


class ImmutableDict(dict):
    __immutable_class__ = dict

    @classmethod
    def from_dict(cls, data: dict, factory) -> "ImmutableDict":
        obj = super().__new__(cls)
        dict.update(obj, data)
        obj.__factory__ = factory
        return obj

    def _raise(self, *args, **kwargs):
        raise MutationForbiddenException("Cannot modify an immutable dict")

    __setitem__ = __delitem__ = update = _raise
    pop = popitem = clear = setdefault = _raise

    def __getitem__(self, key):
        item = super().__getitem__(key)
        return self.__factory__(item)
