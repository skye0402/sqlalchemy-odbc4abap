# odbc4abap/base.py
# Copyright (C) 2007-2019 the SQLAlchemy authors and contributors <see AUTHORS file>
# Copyright (C) 2007 Paul Johnston, paj@pajhome.org.uk
# Portions derived from jet2sql.py by Matt Keranen, mksql@yahoo.com
# ODBC for ABAP logic derived from MS Access dialect :-)
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""
Support for the SAP ODBC for ABAP driver
It allows to retrieve data from SAP S/4HANA Cloud, SAP S/4HANA and SAP BTP ABAP
For that CDS View Entities are queried. 
See SAP Note '3076454 - ODBC driver for ABAP: Configuration' 

"""

from sqlalchemy import types, exc, pool
from sqlalchemy.sql import compiler
from sqlalchemy.engine import default, reflection

import logging


class COUNTER(types.Integer):
    __visit_name__ = "COUNTER"


AutoNumber = COUNTER


class TINYINT(types.Integer):
    __visit_name__ = "TINYINT"


Byte = TINYINT
Char = types.CHAR


class CURRENCY(types.DECIMAL):
    """
    Internally the same as DECIMAL(19, 4), but defined as a separate column type in Access
    so it can do clever things like display values according to the Windows locale (for
    currency symbols and whatnot).
    """

    __visit_name__ = "CURRENCY"


Currency = CURRENCY
DateTime = types.DATETIME
Decimal = types.DECIMAL
Double = types.FLOAT
Integer = types.SMALLINT
LongInteger = types.INTEGER


class LONGCHAR(types.Text):
    __visit_name__ = "LONGCHAR"


LongText = LONGCHAR


class OLEOBJECT(types.LargeBinary):
    __visit_name__ = "OLEOBJECT"


OleObject = OLEOBJECT


class GUID(types.Integer):
    __visit_name__ = "GUID"


ReplicationID = GUID
ShortText = types.String


class Single(types.REAL):
    __visit_name__ = "REAL"


class YESNO(types.BOOLEAN):
    __visit_name__ = "YESNO"


YesNo = YESNO


"""
Map names returned by the "type_name" column of pyodbc's Cursor.columns method to our dialect types.

These names are what you would retrieve from INFORMATION_SCHEMA.COLUMNS.DATA_TYPE if Access
supported those types of system views.
"""
ischema_names = {
    "BIT": YesNo,
    "BYTE": Byte,
    "CHAR": Char,
    "COUNTER": AutoNumber,
    "CURRENCY": Currency,
    "DATETIME": DateTime,
    "DECIMAL": Decimal,
    "DOUBLE": Double,
    "GUID": ReplicationID,
    "INTEGER": LongInteger,
    "LONGBINARY": OleObject,
    "LONGCHAR": LongText,
    "REAL": Single,
    "SMALLINT": Integer,
    "VARCHAR": ShortText,
}


class O4AExecutionContext(default.DefaultExecutionContext):
    def get_lastrowid(self):
        self.cursor.execute("SELECT @@identity AS lastrowid")
        return self.cursor.fetchone()[0]


class O4ACompiler(compiler.SQLCompiler):
    extract_map = compiler.SQLCompiler.extract_map.copy()
    extract_map.update(
        {
            "month": "m",
            "day": "d",
            "year": "yyyy",
            "second": "s",
            "hour": "h",
            "doy": "y",
            "minute": "n",
            "quarter": "q",
            "dow": "w",
            "week": "ww",
        }
    )

    def visit_cast(self, cast, **kw):
        return cast.clause._compiler_dispatch(self, **kw)

    def get_select_precolumns(self, select, **kw):
        """ Before the columns are stated, after SELECT """
        s = super(O4ACompiler, self).get_select_precolumns(select, **kw)
        # if select._offset:
        #     raise NotImplementedError("ABAP ODBC SQL does not support OFFSET")
        # elif hasattr(select, "_simple_int_limit"):
        #     if select._simple_int_limit:
        #         # ODBC drivers and possibly others
        #         # don't support bind params in the SELECT clause on SQL Server.
        #         # so have to use literal here.
        #         s += "LIMIT %d " % select._limit
        # elif select._has_row_limiting_clause and self._use_top(
        #     select
        # ):  # SQLA_1.4
        #     # ODBC drivers and possibly others
        #     # don't support bind params in the SELECT clause on SQL Server.
        #     # so have to use literal here.
        #     kw["literal_execute"] = True
        #     s += "LIMIT %s " % self.process(
        #         self._get_limit_or_fetch(select), **kw
        #     )
        #     # if select._fetch_clause is not None:
        #     #     if select._fetch_clause_options["percent"]:
        #     #         s += "PERCENT "
        #     #     if select._fetch_clause_options["with_ties"]:
        #     #         s += "WITH TIES "

        return s

    def visit_fromclause(self, fromclause, **kwargs):
        return super().visit_fromclause(fromclause, **kwargs)

    # def limit_clause(self, select, **kw):
    #     """Limit in access is after the select keyword"""
    #     return ""

    def binary_operator_string(self, binary):
        """Access uses "mod" instead of "%" """
        return binary.operator == "%" and "mod" or binary.operator

    def visit_concat_op_binary(self, binary, operator, **kw):
        return "%s & %s" % (
            self.process(binary.left, **kw),
            self.process(binary.right, **kw),
        )

    function_rewrites = {
        "current_date": "now",
        "current_timestamp": "now",
        "length": "len",
    }

    def visit_function(self, func, **kw):
        """Access function names differ from the ANSI SQL names;
        rewrite common ones"""
        func.name = self.function_rewrites.get(func.name, func.name)
        return super(O4ACompiler, self).visit_function(func)

    def for_update_clause(self, select, **kw):
        """FOR UPDATE is not supported by Access; silently ignore"""
        return ""

    def visit_table(self, table, asfrom=False, **kw):
        if asfrom:
            return self.preparer.quote(table.fullname)
        else:
            return ""

    def visit_join(self, join, asfrom=False, **kw):
        return (
            "("
            + self.process(join.left, asfrom=True)
            + (join.isouter and " LEFT OUTER JOIN " or " INNER JOIN ")
            + self.process(join.right, asfrom=True)
            + " ON "
            + self.process(join.onclause)
            + ")"
        )

    def visit_extract(self, extract, **kw):
        field = self.extract_map.get(extract.field, extract.field)
        return 'DATEPART("%s", %s)' % (field, self.process(extract.expr, **kw))

    def visit_empty_set_expr(self, type_):
        literal = None
        repr_ = repr(type_[0])
        if repr_.startswith("Integer("):
            literal = "1"
        elif repr_.startswith("String("):
            literal = "'x'"
        elif repr_.startswith("NullType("):
            literal = "NULL"
        else:
            raise ValueError("Unknown type_: %s" % type(type_[0]))
        stmt = "SELECT %s FROM USysSQLAlchemyDUAL WHERE 1=0" % literal
        return stmt

    def visit_ne_binary(self, binary, operator, **kw):
        return "%s <> %s" % (
            self.process(binary.left),
            self.process(binary.right),
        )

    def _get_limit_or_fetch(self, select):  # SQLA_1.4+
        if select._fetch_clause is None:
            return select._limit_clause
        else:
            return select._fetch_clause

    def _use_top(self, select):  # SQLA_1.4+
        return (
            select._offset_clause is None
            or (
                select._simple_int_clause(select._offset_clause)
                and select._offset == 0
            )
        ) and (
            select._simple_int_clause(select._limit_clause)
            or (
                # limit can use TOP with is by itself. fetch only uses TOP
                # when it needs to because of PERCENT and/or WITH TIES
                select._simple_int_clause(select._fetch_clause)
                and (
                    select._fetch_clause_options["percent"]
                    or select._fetch_clause_options["with_ties"]
                )
            )
        )


class O4ATypeCompiler(compiler.GenericTypeCompiler):
    def visit_big_integer(self, type_, **kw):
        """
        Squeeze SQLAlchemy BigInteger() into Access LongInteger by default until Access ODBC supports BIGINT

        If a user needs to store true BIGINT values they can convert them to string, e.g., for a pandas DataFrame:
            df.to_sql("tablename", engine, dtype={'colname': sa_a.ShortText(20)})
        """
        return LongInteger.__visit_name__

    def visit_BOOLEAN(self, type_, **kw):
        return YESNO.__visit_name__

    def visit_COUNTER(self, type_, **kw):
        return COUNTER.__visit_name__

    def visit_CURRENCY(self, type_, **kw):
        return CURRENCY.__visit_name__

    def visit_GUID(self, type_, **kw):
        return GUID.__visit_name__

    def visit_LONGCHAR(self, type_, **kw):
        return LONGCHAR.__visit_name__

    def visit_OLEOBJECT(self, type_, **kw):
        return OLEOBJECT.__visit_name__

    def visit_TINYINT(self, type_, **kw):
        return TINYINT.__visit_name__

    def visit_TEXT(self, type_, **kw):
        """Access ODBC has an option named ExtendedAnsiSQL which defaults to zero. Using ExtendedAnsiSQL=1 is
        recommended with this dialect because it enables DECIMAL(x, y) in DDL, but it also changes the behaviour
        of TEXT (with no length specified). With ExtendedAnsiSQL=0, TEXT behaves like ShortText(255). With
        ExtendedAnsiSQL=1, TEXT creates a LongText (Memo) field. This visit makes the behaviour consistent, and
        helps ensure that string values longer than 255 characters do not get truncated by pandas to_sql."""
        return LongText.__visit_name__


class O4ADDLCompiler(compiler.DDLCompiler):
    def get_column_specification(self, column, **kw):
        if column.table is None:
            raise exc.CompileError(
                "access requires Table-bound columns "
                "in order to generate DDL"
            )

        colspec = self.preparer.format_column(column)
        seq_col = column.table._autoincrement_column
        if seq_col is column:
            colspec += " COUNTER"
        else:
            colspec += " " + self.dialect.type_compiler.process(column.type)

            if column.nullable is not None and not column.primary_key:
                if not column.nullable or column.primary_key:
                    colspec += " NOT NULL"
                else:
                    colspec += " NULL"

            default = self.get_column_default_string(column)
            if default is not None:
                colspec += " DEFAULT " + default

        return colspec

    def visit_drop_index(self, drop):
        index = drop.element
        self.append(
            "\nDROP INDEX [%s].[%s]"
            % (index.table.name, self._index_identifier(index.name))
        )


class O4AIdentifierPreparer(compiler.IdentifierPreparer):
    illegal_initial_characters = compiler.ILLEGAL_INITIAL_CHARACTERS.copy()
    illegal_initial_characters.update(["_"])

    reserved_words = compiler.RESERVED_WORDS.copy()
    # https://support.office.com/en-us/article/learn-about-access-reserved-words-and-symbols-ae9d9ada-3255-4b12-91a9-f855bdd9c5a2
    reserved_words.update(
        [
            "absolute",
            "action",
            "add",
            "admindb",
            "all",
            "allocate",
            "alphanumeric",
            "alter",
            "and",
            "any",
            "are",
            "as",
            "asc",
            "assertion",
            "at",
            "authorization",
            "autoincrement",
            "avg",
            "band",
            "begin",
            "between",
            "binary",
            "bit",
            "bit_length",
            "bnot",
            "bor",
            "both",
            "bxor",
            "by",
            "byte",
            "cascade",
            "cascaded",
            "case",
            "cast",
            "catalog",
            "char",
            "character",
            "char_length",
            "character_length",
            "check",
            "close",
            "coalesce",
            "collate",
            "collation",
            "column",
            "commit",
            "comp",
            "compression",
            "connect",
            "connection",
            "constraint",
            "constraints",
            "container",
            "continue",
            "convert",
            "corresponding",
            "count",
            "counter",
            "create",
            "createdb",
            "cross",
            "currency",
            "current",
            "current_date",
            "current_time",
            "current_timestamp",
            "current_user",
            "cursor",
            "database",
            "date",
            "datetime",
            "day",
            "deallocate",
            "dec",
            "decimal",
            "declare",
            "default",
            "deferrable",
            "deferred",
            "delete",
            "desc",
            "describe",
            "descriptor",
            "diagnostics",
            "disallow",
            "disconnect",
            "distinct",
            "domain",
            "double",
            "drop",
            "else",
            "end",
            "end-exec",
            "escape",
            "except",
            "exception",
            "exclusiveconnect",
            "exec",
            "execute",
            "exists",
            "external",
            "extract",
            "false",
            "fetch",
            "first",
            "float",
            "float4",
            "float8",
            "for",
            "foreign",
            "found",
            "from",
            "full",
            "general",
            "get",
            "global",
            "go",
            "goto",
            "grant",
            "group",
            "guid",
            "having",
            "hour",
            "identity",
            "ieeedouble",
            "ieeesingle",
            "ignore",
            "image",
            "immediate",
            "index",
            "inindex",
            "indicator",
            "inheritable",
            "initially",
            "inner",
            "input",
            "insensitive",
            "insert",
            "int",
            "integer",
            "integer1",
            "integer2",
            "integer4",
            "intersect",
            "interval",
            "into",
            "is",
            "isolation",
            "join",
            "key",
            "language",
            "last",
            "leading",
            "left",
            "level",
            "like",
            "local",
            "logical",
            "logical1",
            "long",
            "longbinary",
            "longchar",
            "longtext",
            "lower",
            "match",
            "max",
            "memo",
            "min",
            "minute",
            "module",
            "money",
            "month",
            "names",
            "national",
            "natural",
            "nchar",
            "next",
            "no",
            "not",
            "note",
            "null",
            "nullif",
            "number",
            "numeric",
            "object",
            "octet_length",
            "ofoleobject",
            "ononly",
            "open",
            "option",
            "ororder",
            "outer",
            "output",
            "overlaps",
            "owneraccess",
            "pad",
            "parameters",
            "partial",
            "password",
            "percent",
            "pivot",
            "position",
            "precision",
            "prepare",
            "preserve",
            "primary",
            "prior",
            "privileges",
            "proc",
            "procedure",
            "public",
            "read",
            "real",
            "references",
            "relative",
            "restrict",
            "revoke",
            "right",
            "rollback",
            "rows",
            "schema",
            "scroll",
            "second",
            "section",
            "select",
            "selectschema",
            "selectsecurity",
            "session",
            "session_user",
            "set",
            "short",
            "single",
            "size",
            "smallint",
            "some",
            "space",
            "sql",
            "sqlcode",
            "sqlerror",
            "sqlstate",
            "string",
            "substring",
            "sum",
            "system_user",
            "table",
            "tableid",
            "temporary",
            "text",
            "then",
            "time",
            "timestamp",
            "timezone_hour",
            "timezone_minute",
            "to",
            "top",
            "trailing",
            "transaction",
            "transform",
            "translate",
            "translation",
            "trim",
            "true",
            "union",
            "unique",
            "uniqueidentifier",
            "unknown",
            "update",
            "updateidentity",
            "updateowner",
            "updatesecurity",
            "upper",
            "usage",
            "user",
            "using",
            "value",
            "values",
            "varbinary",
            "varchar",
            "varying",
            "view",
            "when",
            "whenever",
            "where",
            "with",
            "work",
            "write",
            "year",
            "yesno",
            "zone",
        ]
    )

    def __init__(self, dialect):
        super(O4AIdentifierPreparer, self).__init__(
            dialect, initial_quote="", final_quote=""
        )
        
    def format_schema(self, name):
        logger = logging.getLogger('sqlalchemy.engine')
        logger.debug(f"Returning schema {name} in format_schema.")
    
    def quote_schema(self, schema, force=None):
        logger = logging.getLogger('sqlalchemy.engine')
        logger.debug(f"Returning schema {schema} in quote_schema.")
        return schema

    def quote_identifier(self, schema, force=None):
        logger = logging.getLogger('sqlalchemy.engine')
        logger.debug(f"Returning schema {schema} in quote_identifier.")
        return schema
    
class O4ADialect(default.DefaultDialect):
    colspecs = {}
    name = "odbc4abap"
    supports_native_boolean = (
        True  # suppress CHECK constraint on YesNo columns
    )
    supports_sane_rowcount = False
    supports_sane_multi_rowcount = False
    supports_simple_order_by_label = False
    _need_decimal_fix = False

    supports_is_distinct_from = False

    poolclass = pool.SingletonThreadPool
    statement_compiler = O4ACompiler
    ddl_compiler = O4ADDLCompiler
    type_compiler = O4ATypeCompiler
    preparer = O4AIdentifierPreparer
    execution_ctx_cls = O4AExecutionContext

    @classmethod
    def dbapi(cls):
        import pyodbc as module

        module.pooling = (
            False  # TODO: Check if needed
        )
        return module

    def create_connect_args(self, url):
        opts = url.translate_connect_args()
        connectors = ["Driver={Microsoft Access Driver (*.mdb)}"]
        connectors.append("Dbq=%s" % opts["database"])
        user = opts.get("username", None)
        if user:
            connectors.append("UID=%s" % user)
            connectors.append("PWD=%s" % opts.get("password", ""))
        return [[";".join(connectors)], {}]

    def last_inserted_ids(self):
        return self.context.last_inserted_ids

    def has_table(self, connection, tablename, schema=None):
        pyodbc_crsr = connection.engine.raw_connection().cursor()
        result = pyodbc_crsr.tables(table=tablename).fetchone()
        return bool(result)

    @reflection.cache
    def get_table_names(self, connection, schema=None, **kw):
        pyodbc_crsr = connection.engine.raw_connection().cursor()
        query = f"SELECT view_name FROM sys.views WHERE schema_name = '{schema}'"
        pyodbc_crsr.execute(query)
        result = pyodbc_crsr.fetchall()
        table_names = [
            row.VIEW_NAME
            for row in result
        ]
        return table_names

    @reflection.cache
    def get_view_names(self, connection, schema=None, **kw):
        pyodbc_crsr = connection.engine.raw_connection().cursor()
        result = pyodbc_crsr.tables(tableType="VIEW").fetchall()
        return [row[2] for row in result]

    def _decode_sketchy_utf16(self, raw_bytes):
        # work around bug in Access ODBC driver
        # ref: https://github.com/mkleehammer/pyodbc/issues/328
        s = raw_bytes.decode("utf-16le", "ignore")
        try:
            n = s.index("\u0000")
            s = s[:n]  # respect null terminator
        except ValueError:
            pass
        return s

    def get_columns(self, connection, table_name, schema=None, **kw):
        pyodbc_crsr = connection.engine.raw_connection().cursor()
        query = f"SELECT * FROM sys.view_columns WHERE schema_name = '{schema}' and view_name = '{table_name}'"
        pyodbc_crsr.execute(query)
        res = pyodbc_crsr.fetchall()
        result = []
        for row in res:
            if row.ODBC_TYPE_NAME == "INT4":
                row.ODBC_TYPE_NAME = "INTEGER"
            elif row.ODBC_TYPE_NAME == "NUMC":
                row.ODBC_TYPE_NAME = "CHAR"
            elif row.ODBC_TYPE_NAME == "DATN" or row.ODBC_TYPE_NAME == "DATS":
                row.ODBC_TYPE_NAME = "DATETIME"
            elif row.ODBC_TYPE_NAME == "QUAN":
                row.ODBC_TYPE_NAME = "DECIMAL"
            elif row.ODBC_TYPE_NAME == "UNIT":
                row.ODBC_TYPE_NAME = "CHAR"
            class_ = ischema_names[row.ODBC_TYPE_NAME]
            type_ = class_()
            result.append(
                {
                    "name": row.COLUMN_NAME,
                    "type": type_,
                    "length": row.ODBC_COLUMN_SIZE,
                    "comment": row.DESCRIPTION,
                    "nullable": not row.ODBC_NULLABLE,
                    "primary_key": True if row.IS_KEY == 'TRUE' else False,
                    "default": None,
                }
            )
        return result

    def get_primary_keys(self, connection, table_name, schema=None, **kw):
        return self.get_pk_constraint(
            self, connection, table_name, schema=schema, **kw
        )

    def get_pk_constraint(self, connection, table_name, schema=None, **kw):
        pyodbc_crsr = connection.engine.raw_connection().cursor()
        query = f"SELECT * FROM sys.view_columns WHERE schema_name = '{schema}' and view_name = '{table_name}'"
        pyodbc_crsr.execute(query)
        res = pyodbc_crsr.fetchall()
        result = []
        for row in res:
            if row.IS_KEY == 'TRUE':
                result.append(row.COLUMN_NAME)
        constraint_name = None
        return {"constrained_columns": result, "name": constraint_name}

    def get_foreign_keys(self, connection, table_name, schema=None, **kw):
        logger = logging.getLogger('sqlalchemy.engine')
        logger.debug("No foreign keys implemented.")
        return []

    def get_indexes(self, connection, table_name, schema=None, **kw):
        """ Not implemented in driver """
        return []
    
    def do_rollback(self, dbapi_connection):
        logger = logging.getLogger('sqlalchemy.engine')
        logger.debug("No rollback from ODBC read access needed. Skipped.")
        
    def do_commit(self, dbapi_connection):
        logger = logging.getLogger('sqlalchemy.engine')
        logger.debug("No commit from ODBC read access needed. Skipped.")        