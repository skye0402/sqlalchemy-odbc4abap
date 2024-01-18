from sqlalchemy.dialects import registry as _registry

from .base import (
    AutoNumber,
    Byte,
    Char,
    Currency,
    DateTime,
    Decimal,
    Double,
    Integer,
    LongInteger,
    LongText,
    ReplicationID,
    ShortText,
    Single,
    YesNo,
)

import pyodbc

__version__ = "0.0.5"

_registry.register(
    "odbc4abap.pyodbc", "sqlalchemy_odbc4abap.pyodbc", "O4ADialect_pyodbc"
)
