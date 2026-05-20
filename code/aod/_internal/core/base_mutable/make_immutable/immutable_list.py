from ...domain_exception import MutationForbiddenException


class ImmutableList(list):
    __immutable_class__ = list

    @classmethod
    def from_list(cls, data: list, factory) -> "ImmutableList":
        obj = super().__new__(cls)
        list.extend(obj, data)
        obj.__factory__ = factory
        return obj

    def _raise(self, *args, **kwargs):
        raise MutationForbiddenException("Cannot modify an immutable list")

    append = extend = insert = remove = _raise
    pop = clear = sort = reverse = _raise
    __setitem__ = __delitem__ = __iadd__ = __imul__ = _raise

    def __getitem__(self, key):
        item = super().__getitem__(key)
        return self.__factory__(item)
