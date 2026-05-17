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

    def __copy__(self):
        return ImmutableList.from_list(list(self))

    def __deepcopy__(self, memo):
        import copy

        return ImmutableList.from_list([copy.deepcopy(v, memo) for v in self])


class ImmutableDict(dict):
    @classmethod
    def from_dict(cls, data: dict) -> "ImmutableDict":
        return super().__new__(cls, data)

    def _raise(self, *args, **kwargs):
        raise MutationForbiddenError("Cannot modify an immutable dict")

    __setitem__ = __delitem__ = update = _raise
    pop = popitem = clear = setdefault = _raise

    def __copy__(self):
        return ImmutableDict.from_dict(dict(self))

    def __deepcopy__(self, memo):
        import copy

        return ImmutableDict.from_dict(
            {k: copy.deepcopy(v, memo) for k, v in self.items()}
        )


class ImmutableSet(set):
    @classmethod
    def from_set(cls, data: set) -> "ImmutableSet":
        obj = set.__new__(cls)
        set.update(obj, data)  # bypaseamos nuestro update bloqueado
        return obj

    def _raise(self, *args, **kwargs):
        raise MutationForbiddenError("Cannot modify an immutable set")

    add = discard = remove = _raise
    pop = clear = update = _raise
    __ior__ = __iand__ = __ixor__ = __isub__ = _raise
