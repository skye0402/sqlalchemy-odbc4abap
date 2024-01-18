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

__version__ = "0.0.1"

pyodbc.pooling = False  # TODO: Check if required for ABAP ODBC
_registry.register(
    "odbc4abap.pyodbc", "sqlalchemy_odbc4abap.pyodbc", "O4ADialect_pyodbc"
)
