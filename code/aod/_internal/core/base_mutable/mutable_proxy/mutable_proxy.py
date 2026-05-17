from copy import copy
from functools import wraps
from typing import Any

from ...domain_exception import MutationForbiddenError

PRIMITIVE_TYPES = (int, float, str, bool, bytes, type(None))


