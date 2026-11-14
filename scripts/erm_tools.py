#!/usr/bin/env python3
# Copyright (c) 2013-Now https://jeesite.com All rights reserved.
# No deletion without permission, or be held responsible to law.
"""
ERMaster（ERM）文件生成与修改工具

依据 ERMaster 源码（org.insightech.er.editor.persistent.impl.PersistentXmlImpl / XMLLoader）
实现的 ERM 文件读写工具，生成的 XML 严格遵循 ERMaster 的真实格式，可被 ERMaster 直接打开。

格式要点（源码依据）：
    - ERM 是单层扁平 XML，根节点 <diagram>，顺序为
      settings / dictionary / tablespace_set / contents / column_groups /
      test_data_list / sequence_set / trigger_set / change_tracking_list
    - 列的长度、精度存放在 <dictionary><word> 中，列通过 <word_id> 引用，
      因此写入列时必须同步写入字典词条，否则长度/精度会丢失。
    - 外键列存放在子表的 <columns> 中，不写 word_id，物理名/逻辑名留空，
      依靠 <referenced_column> 与 <relation> 继承父表列的信息。
    - <relation> 写在子表的 <connections> 内：source=父表、target=子表。
    - 索引容器为 <indexes>，子元素沿用 ERMaster 写出的 <inidex>（原样拼写）。
    - 文本转义：& < > " ' 以及 \\r \\n \\t 分别写成 &#x0A; &#x0D; &#x09; 等字符实体。

子命令：
    create    依据 JSON 规格生成新的 ERM 文件
    apply     在保留原有内容的前提下修改已有 ERM 文件（增量更新）
    info      读取 ERM 文件，输出结构化 JSON 摘要
    validate  校验 ERM 文件的结构与引用完整性
    backups   列出临时缓存中的备份记录
    restore   从备份恢复 ERM 文件（支持 --run <id> 或 --file <path>）
    schema    输出 create/apply 的 JSON 规格模板（供 AI 直接参考）

备份与回退（每次执行都会留档，可随时恢复）：
    备份根目录：$ERM_BACKUP_DIR，未设置时用 ~/.cache/jeesite-erm-backups
    每次 create/apply/restore 都会新建一个运行目录：
        <备份根目录>/<YYYYmmdd-HHMMSS-xxxx>/<原文件名>
        <备份根目录>/<YYYYmmdd-HHMMSS-xxxx>/manifest.json
    默认最多保留最近 200 次备份，超出后自动清理最旧的记录。
    恢复方式：
        python3 scripts/erm_tools.py backups --file db/test.erm
        python3 scripts/erm_tools.py restore --file db/test.erm
        python3 scripts/erm_tools.py restore --run 20261114-101530-a1b2

用法示例：
    python3 scripts/erm_tools.py create --spec spec.json --out db/test.erm
    python3 scripts/erm_tools.py apply  --file db/test.erm --spec patch.json
    python3 scripts/erm_tools.py info   --file db/test.erm
    python3 scripts/erm_tools.py validate --file db/test.erm
    python3 scripts/erm_tools.py backups --file db/test.erm
    python3 scripts/erm_tools.py restore --file db/test.erm
    python3 scripts/erm_tools.py schema

退出码：
    0 - 成功
    1 - 校验失败（validate）
    2 - 参数或规格错误、文件读写失败
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# 常量：来自 ERMaster resources/SqlType.xls 的合法类型 id
# ---------------------------------------------------------------------------

_RAW_TYPE_IDS = (
    "character(n)|varchar(n)|nchar(n)|nvarchar(n)|decimal|decimal(p)|decimal(p,s)|"
    "numeric|numeric(p)|numeric(p,s)|integer|smallint|float|double precision|real|text|"
    "clob|clob(n)|nclob|ntext|varchar|varchar_ignorecase|varchar_ignorecase(n)|nvarchar|"
    "blob|blob(n)|bfile|varbinary|varbinary(n)|array|bigint|bigint(n)|bigserial|"
    "binary_double|binary_float|binary(n)|binary1|bit|bit(n)|bit varying|bit varying(n)|"
    "boolean|box|char|nchar|cidr|circle|date|dbclob|dbclob(n)|double precision(m,d)|enum|"
    "decfloat16|float(p)|float(m,d)|geometry|hierarchyid|image|inet|int(n)|interval|"
    "interval(p)|interval year|interval month|interval day|interval hour|interval minute|"
    "interval second|interval second(p)|interval year to month|interval year(p) to month|"
    "interval day to hour|interval day to minute|interval day to second|"
    "interval day to second(p)|interval day(p) to second|interval day(p) to second(p)|"
    "interval hour to minute|interval hour to second|interval hour to second(p)|"
    "interval minute to second|interval minute to second(p)|line|long|longblob|long raw|"
    "longtext|longvarchar|longvarbinary|lseg|macaddr|mediumblob|mediumint|mediumint(n)|"
    "mediumtext|money|smallmoney|oid|other|path|point|polygon|raw(n)|real(m,d)|rowguidcol|"
    "rowversion|serial|set|smallint(n)|time|time(p)|time with time zone|"
    "time(p) with time zone|timestamp|datetime2|timestamp(p)|timestamp with time zone|"
    "timestamp(p) with time zone|timestamp with local time zone|"
    "timestamp(p) with local time zone|datetime|smalldatetime|tinyblob|tinyint|tinyint(n)|"
    "tinytext|urowid|urowid(n)|uuid|xml|year(2)|year(4)|alert_type|anydata|multipoint|"
    "linestring|multilinestring|multipolygon|geometrycollection|datetime(n)|sdo_geometry|"
    "sdo_topo_geometry|sdo_georaster|datetime year to month|datetime year to day|"
    "datetime year to hour|datetime year to minute|datetime year to second|"
    "datetime year to fraction(p)"
)

# 合法类型 id 集合
ERM_TYPE_IDS = [t.strip() for t in _RAW_TYPE_IDS.split("|") if t.strip()]
ERM_TYPE_ID_SET = set(ERM_TYPE_IDS)

# 常见类型别名 -> ERMaster 类型基准名
TYPE_ALIASES = {
    "int": "integer",
    "int4": "integer",
    "int8": "bigint",
    "varchar2": "varchar",
    "nvarchar2": "nvarchar",
    "string": "varchar",
    "bool": "boolean",
    "double": "double precision",
    "float8": "double precision",
    "float4": "real",
    "number": "decimal",
    "char": "character",
    "bytea": "blob",
    "timestamp without time zone": "timestamp",
}

# ERMaster 支持的数据库 id（settings/database）
ERM_DATABASES = [
    "StandardSQL", "MySQL", "Oracle", "PostgreSQL", "DB2", "H2", "HSQLDB",
    "SQLite", "SQLServer", "SQLServer 2008", "MSAccess", "Tibero", "CUBRID", "Informix",
]

# 各节点的规范子元素顺序（与 PersistentXmlImpl 写出的顺序一致，顺序影响加载器取值）
TABLE_TAGS = [
    "id", "height", "width", "font_name", "font_size", "x", "y", "color", "connections",
    "physical_name", "logical_name", "description", "constraint", "primary_key_name",
    "option", "columns", "indexes", "complex_unique_key_list", "table_properties",
]
VIEW_TAGS = [
    "id", "height", "width", "font_name", "font_size", "x", "y", "color", "connections",
    "physical_name", "logical_name", "description", "sql", "columns", "view_properties",
]
NOTE_TAGS = [
    "id", "height", "width", "font_name", "font_size", "x", "y", "color", "connections", "text",
]
COLUMN_TAGS = [
    "word_id", "id", "referenced_column", "relation", "description", "unique_key_name",
    "logical_name", "physical_name", "type", "constraint", "default_value", "auto_increment",
    "foreign_key", "not_null", "primary_key", "unique_key", "character_set", "collation",
    "sequence",
]
WORD_TAGS = [
    "id", "length", "decimal", "array", "array_dimension", "unsigned", "zerofill", "binary",
    "args", "char_semantics", "description", "logical_name", "physical_name", "type",
]
RELATION_TAGS = [
    "id", "source", "target", "source_xp", "source_yp", "target_xp", "target_yp",
    "bendpoint", "color", "child_cardinality", "parent_cardinality", "reference_for_pk",
    "name", "on_delete_action", "on_update_action", "referenced_column",
    "referenced_complex_unique_key",
]
INDEX_TAGS = ["full_text", "non_unique", "name", "type", "description", "columns"]
SEQUENCE_TAGS = [
    "name", "schema", "increment", "min_value", "max_value", "start", "cache",
    "nocache", "cycle", "order", "description", "data_type", "decimal_size",
]

# 默认绘图参数（与 ERMaster 新建图一致）
DEFAULT_COLOR = (128, 128, 192)
DEFAULT_FONT = "Arial"
DEFAULT_FONT_SIZE = 14
DEFAULT_TABLE_HEIGHT = 75
DEFAULT_TABLE_WIDTH = 200

# ---------------------------------------------------------------------------
# JeeSite 约定（来自 core.erm 真实样本）
# ---------------------------------------------------------------------------

# 设置风格
JEESITE_DEFAULT_DATABASE = "StandardSQL"
JEESITE_DEFAULT_TABLE_STYLE = "funny"
JEESITE_DEFAULT_NOTATION = "IE"
JEESITE_DEFAULT_ZOOM = "0.8"
JEESITE_TABLE_PREFIX = "js_"

# ---------------------------------------------------------------------------
# 标识符命名（索引、约束、主键）
# ---------------------------------------------------------------------------

# 各数据库标识符长度上限（统一取最小公共值，最保守）
# Oracle 12.2 前 = 30，MySQL <= 8.0 默认为 64，PG >= 7.3 = 63，SQL Server = 128
# 安全上限取 30（Oracle 兼容），MySQL/PG 等也不会报错
MAX_IDENTIFIER_LEN = 30

# SQL 关键字/保留字（跨库公共，覆盖 Oracle / MySQL / PostgreSQL / SQL Server / DB2）
# 用于在自动命名后检测是否命中关键字并给出警告
SQL_RESERVED_WORDS = {
    # 通用
    "add", "all", "alter", "and", "as", "asc", "between", "case", "check", "column",
    "constraint", "create", "database", "default", "delete", "desc", "distinct", "drop",
    "else", "exists", "foreign", "from", "group", "having", "in", "inner", "insert",
    "into", "is", "join", "key", "left", "like", "limit", "not", "null", "on", "or",
    "order", "outer", "primary", "references", "right", "select", "set", "table", "then",
    "to", "union", "unique", "update", "values", "view", "when", "where", "with",
    # Oracle 特有
    "audit", "cluster", "comment", "compress", "connected", "connect", "context", "cursor",
    "cycle", "dictionary", "disable", "enable", "exclude", "fetch", "for", "force", "grant",
    "grouping", "interface", "intersect", "materialize", "minus", "mode", "noaudit", "nocompress",
    "nowait", "offline", "on", "online", "pctfree", "prior", "privileges", "public", "rename",
    "resource", "revoke", "role", "rollback", "row", "rownum", "rows", "session", "start",
    "successful", "synonym", "sysdate", "tablespace", "temporary", "trigger", "truncate",
    "uid", "user", "validate", "values", "varchar2", "waiting", "whenever", "writes",
    # MySQL 特有
    "auto_increment", "binary", "bfile", "blob", "bool", "boolean", "btree", "cache", "call",
    "cascade", "character", "checkpoint", "collate", "collation", "column_format", "columns",
    "commit", "compressed", "condition", "definition", "delay_key_write", "deterministic",
    "discard", "distinctrow", "div", "double", "dumpfile", "each", "elseif", "empty", "enclosed",
    "engine", "enum", "escape", "escaped", "evaluate", "explain", "extended", "fast", "first",
    "fixed", "float", "flush", "foreign_key_checks", "fulltext", "ge_collection", "geometry",
    "geometrycollection", "get", "global", "grant", "groupby", "handler", "hash", "help",
    "high_priority", "hour_microsecond", "ignore", "infile", "inout", "insensitive", "int",
    "integer", "interval", "invisible", "iteration", "join", "json", "key_block_size",
    "language", "last_value", "lead", "leading", "leave", "left", "less", "level", "limit",
    "linear", "lines", "list", "load", "local", "localtime", "localtimestamp", "lock",
    "low_priority", "master", "master_key", "match", "maxvalue", "mediumint", "memory",
    "merge", "minute_microsecond", "modify", "no_write_to_binlog", "nullif", "numeric",
    "onupdate", "optimize", "option", "optionally", "options", "or", "out", "outer", "outfile",
    "overwrite", "partition", "precision", "primary", "procedure", "query", "range", "read",
    "read_write", "readonly", "real", "recursive", "reference", "regexp", "release", "remove",
    "rename", "repeat", "replace", "resignal", "restrict", "return", "revoke", "rlike",
    "schema", "schemas", "second_microsecond", "segment", "sensitive", "server", "share",
    "shared", "show", "signal", "smallint", "spatial", "sql", "sqlexception", "sqlstate",
    "sqlwarning", "straight_join", "system", "table_name", "tables", "terminated", "text",
    "time", "timestamp", "tinyblob", "tinyint", "tinytext", "to", "trailing", "transaction",
    "trigger", "unbounded", "unencrypted", "union", "unique", "unsigned", "until", "updatexml",
    "usage", "use", "user", "using", "utc_date", "utc_time", "utc_timestamp", "value",
    "values", "varbinary", "varchar", "variable", "variables", "varying", "vector", "virtual",
    "visibility", "wait", "warning", "week", "when", "where", "while", "window", "with",
    "without", "work", "wrapper", "xid", "xml", "xor", "year", "zerofill",
    # PostgreSQL 特有
    "action", "add", "admin", "after", "aggregate", "all", "also", "analyze", "and", "any",
    "array", "as", "asc", "assertion", "assignment", "at", "attach", "attribute", "avg",
    "backward", "before", "begin", "between", "bigint", "binary", "bit", "boolean", "both",
    "by", "cache", "call", "cascade", "case", "cast", "chain", "char", "character", "check",
    "checkpoint", "class", "close", "cluster", "coalesce", "collate", "collation", "column",
    "comment", "comments", "commit", "committed", "condition", "configuration", "confirm",
    "constraint", "constraints", "convert", "copy", "correspond", "count", "covariate",
    "create", "cross", "cube", "current", "current_catalog", "current_date", "current_path",
    "current_role", "current_row", "current_schema", "current_setting", "current_time",
    "current_timestamp", "current_user", "cursor", "cycle", "data", "database", "date",
    "day", "deallocate", "dec", "decimal", "declare", "default", "defaults", "define",
    "delete", "delimiter", "delimiters", "deterministic", "distinct", "do", "double", "drop",
    "each", "else", "empty", "end", "end_execution", "enum", "escape", "event", "every",
    "except", "exclude", "excluding", "execute", "exists", "explain", "expression", "extract",
    "false", "family", "fetch", "filter", "first", "float", "following", "for", "force",
    "foreign", "forward", "freeze", "from", "full", "function", "fundamental", "group",
    "grouping", "handler", "having", "if", "ilike", "immediate", "immutable", "implicit",
    "import", "in", "include", "including", "increment", "index", "indicator", "inherits",
    "initially", "inline", "inner", "inout", "input", "insensitive", "insert", "instead",
    "int", "integer", "intersect", "interval", "into", "invoker", "is", "isnull", "join",
    "key", "label", "language", "large", "last", "lateral", "leading", "leakproof", "left",
    "level", "like", "limit", "listen", "literal", "localtime", "localtimestamp", "lock",
    "locked", "log", "mapping", "match", "materialized", "max", "method", "min", "mod",
    "mode", "month", "move", "name", "national", "natural", "nchar", "new", "next", "no",
    "none", "normalize", "not", "nothing", "notify", "nowait", "null", "nullif", "nulls",
    "numeric", "object", "of", "off", "offset", "oids", "old", "on", "only", "operator",
    "option", "options", "or", "order", "ordinality", "others", "out", "outer", "over",
    "overlaps", "overlay", "overwrite", "partition", "passing", "password", "percent",
    "period", "permissions", "pivot", "placing", "plan", "plans", "policy", "precedes",
    "precision", "prepare", "preserve", "prev", "previous", "privileges", "procedural",
    "procedure", "program", "publication", "quote", "range", "read", "real", "reassign",
    "references", "refresh", "rename", "repeatable", "replace", "replica", "required",
    "reset", "restart", "restrict", "return", "returning", "returns", "reverse", "revoke",
    "right", "role", "rollback", "rollup", "row", "rows", "rule", "savepoint", "scalar",
    "schema", "schemas", "scroll", "search", "security", "select", "sequence", "serializable",
    "server", "session", "session_user", "set", "setof", "share", "show", "similar", "simple",
    "skip", "smallint", "some", "support", "sysdate", "system", "table", "tablesample",
    "tablespace", "temp", "template", "temptext", "then", "timestamp", "timezone", "to",
    "top_level_count", "trailing", "transaction", "trigger", "trim", "true", "truncate",
    "trusted", "type", "types", "unbounded", "uncommitted", "unencrypted", "union", "unique",
    "unknown", "unless", "unnest", "until", "update", "user", "using", "value", "values",
    "varchar", "variadic", "various", "varying", "verbose", "version", "view", "views",
    "volatile", "when", "where", "whitespace", "window", "with", "within", "without", "work",
    "wrapper", "write", "xml", "year", "yes", "zone",
    # SQL Server 特有
    "all", "alter", "and", "as", "asc", "authorization", "avg", "backup", "begin", "between",
    "break", "by", "browse", "bulk", "case", "check", "checkpoint", "class", "clustered",
    "coalesce", "collate", "column", "commit", "compute", "constraint", "contains",
    "containskeyword", "continue", "convert", "count", "create", "cross", "current",
    "current_date", "current_time", "current_timestamp", "cursor", "database", "dbcc",
    "deallocate", "declare", "default", "delete", "deny", "desc", "disk", "distinct",
    "distributed", "double", "drop", "dump", "else", "end", "errlvl", "escape", "except",
    "exec", "execute", "exists", "exit", "external", "fetch", "file", "fillfactor",
    "float", "for", "foreign", "freetext", "from", "full", "function", "goto", "grant",
    "group", "having", "holdlock", "identity", "identity_insert", "identitycol", "if",
    "in", "index", "inner", "insert", "intersect", "into", "is", "join", "key", "kill",
    "left", "like", "lineno", "load", "national", "natural", "nclob", "nocount", "nonclustered",
    "not", "null", "nullif", "of", "off", "offsets", "on", "open", "opendatasource",
    "openquery", "openrowset", "openxml", "option", "or", "order", "outer", "over",
    "percent", "period", "pivot", "plan", "precision", "preserve", "primary", "print",
    "proc", "procedure", "public", "raiserror", "rand", "range", "read", "readonly",
    "readtext", "real", "reconfigure", "references", "replication", "resample", "restore",
    "restrict", "return", "revert", "revoke", "right", "rlike", "rollback", "rowcount",
    "rowguidcol", "rows", "rule", "save", "schema", "securityaudit", "select", "semantickeyphrase",
    "session_user", "set", "setuser", "shutdown", "simple", "some", "statistics", "streamaggregate",
    "system_user", "table", "tablesample", "text", "top", "tran", "transaction", "trigger",
    "trim", "try", "try_convert", "tsql", "tsequal", "union", "unique", "unknown",
    "unpivot", "update", "updatetext", "use", "user", "using", "value", "values", "varchar",
    "varying", "view", "waitfor", "when", "where", "while", "with", "within", "writetext",
    # DB2 特有
    "allocate", "alter", "and", "any", "as", "assocresult", "associate", "asc", "between",
    "both", "bufferpool", "by", "call", "case", "cast", "ccsid", "check", "close", "cluster",
    "collect", "column", "comment", "commit", "concurrency", "condition", "connect",
    "constraint", "continue", "convert", "copy", "count", "create", "current", "cursor",
    "database", "day", "days", "dbcc", "deallocate", "declare", "default", "delete",
    "descriptor", "deterministic", "diagnostics", "disallow", "distinct", "do", "double",
    "drop", "else", "elseif", "enable", "end", "ending", "erase", "escape", "except",
    "exception", "execute", "exists", "exit", "explain", "external", "family", "fetch",
    "full", "function", "generated", "global", "go", "goto", "grant", "graphical", "group",
    "having", "hour", "hours", "identity", "immediate", "in", "index", "indicator",
    "inherit", "inner", "inout", "input", "insensitive", "insert", "integrity", "intersect",
    "into", "is", "isolation", "join", "key", "language", "like", "limit", "lock",
    "locksize", "locks", "long", "materialized", "maxvalue", "minvalue", "modifies",
    "no", "nocache", "cycle", "node", "none", "not", "null", "nulls", "numeric", "of",
    "on", "open", "optimization", "optimize", "or", "order", "out", "output", "outer",
    "over", "overriding", "partition", "precision", "prepare", "preserve", "primary",
    "procedure", "program", "queryno", "range", "reads", "recover", "references", "refresh",
    "release", "rename", "repeat", "reset", "resource", "result", "return", "returns",
    "reverse", "revoke", "right", "rollback", "row", "rows", "rule", "savepoint", "schema",
    "scroll", "search", "select", "session", "set", "signal", "simple", "size", "smallint",
    "some", "source", "specific", "sqlstate", "static", "summary", "sysfun", "sysproc",
    "table", "tablespace", "then", "to", "transaction", "trigger", "truncate", "type",
    "union", "unique", "update", "usage", "use", "using", "value", "values", "varchar",
    "variant", "varying", "view", "when", "where", "while", "with", "without",
}


def _warn(msg):
    """输出一条警告（stderr），不中断流程。"""
    import sys as _sys
    print("[WARN] {}".format(msg), file=_sys.stderr)


def _table_short_name(table_name):
    """把 js_sys_job_log → sys_job_log（去掉 js_ 前缀，取表的后半段）。"""
    if not table_name:
        return table_name or ""
    lower = table_name.lower()
    for prefix in ("js_", "ts_", "hr_", "biz_", "gen_"):
        if lower.startswith(prefix):
            return table_name[len(prefix):]
    return table_name


def _column_abbr(col_name):
    """列名缩写：job_name → jn，status → s，create_date → cd。

    规则：下划线/驼峰拆分后各单词首字母；单单词取首 2 字符。
    """
    if not col_name:
        return col_name or ""
    n = col_name.lower()
    parts = n.split("_")
    if len(parts) >= 2:
        return "".join(p[0] for p in parts if p)
    import re as _re
    camel = _re.sub(r"(?<!^)(?=[A-Z])", "_", col_name).lower().split("_")
    if len(camel) >= 2:
        return "".join(p[0] for p in camel if p)
    return n[:2]


def _trim_identifier(name, max_len=MAX_IDENTIFIER_LEN):
    """把标识符长度裁到 max_len 以内。"""
    if len(name) <= max_len:
        return name
    trimmed = name[:max_len]
    last_und = trimmed.rfind("_")
    # 如果刚好截断在单词中间（last_und 很靠前），说明截断位置合理；否则放弃该尾部
    if last_und > 0 and max_len - last_und <= 4:
        trimmed = trimmed[:last_und]
    return trimmed


def _is_reserved_word(name):
    return name.lower() in SQL_RESERVED_WORDS


def make_constraint_name(kind, table_name, *col_names):
    """
    自动生成索引/约束名（"表后缀_名称" 模式）。

    kind: "idx" / "uk" / "pk" / "fk"
    示例:
      make_constraint_name("idx", "js_sys_job_log", "job_name")
        → "idx_sys_job_log_jn"
      make_constraint_name("uk", "js_sys_user", "login_code")
        → "uk_sys_user_lc"
      make_constraint_name("pk", "js_sys_user")
        → "pk_sys_user"
      make_constraint_name("fk", "js_sys_user_role", "js_sys_user")
        → "fk_sys_user_role_sys_user"

    - 表名前缀 js_ 等自动剥掉（_table_short_name）
    - 各列名缩写 _column_abbr（多列用 _ 连接）
    - 长度自动裁到 MAX_IDENTIFIER_LEN=30（Oracle 兼容）
    - 命中 SQL 关键字时输出警告
    """
    import re as _re
    table_short = _table_short_name(table_name)
    col_part = ""
    if kind == "fk" and len(col_names) >= 2:
        col_part = _table_short_name(col_names[0]) + "_" + _table_short_name(col_names[1])
    elif col_names:
        col_part = "_".join(_column_abbr(c) for c in col_names)
    raw = "{}_{}".format(kind, table_short)
    if col_part:
        raw = raw + "_" + col_part
    raw = _re.sub(r"_+", "_", raw).strip("_")
    final = _trim_identifier(raw)
    if _is_reserved_word(final):
        _warn("标识符命中 SQL 关键字: {}（表 {}，类型 {}）".format(final, table_name, kind))
    if len(final) > MAX_IDENTIFIER_LEN:
        _warn("标识符长度 {} 超过上限 {}: {}".format(len(final), MAX_IDENTIFIER_LEN, final))
    return final


# 字段名 → (type_id, length, decimal, 说明) 推断规则
# 当规格中列未显式给 type 时，按列名匹配此表自动填上（来自 core.erm 统计）
JEESITE_NAME_TYPE_HINTS = [
    # 主键
    ("id", "varchar(n)", 64, None, "主键，统一 varchar(64)"),
    ("*_code", "varchar(n)", 64, None, "编码/外键编码，如 user_code、office_code、module_code"),
    ("*_codes", "varchar(n)", 500, None, "多编码串联，如 module_codes、sys_codes"),
    ("*_id", "varchar(n)", 64, None, "外部关联 id，如 user_id、office_id、demo_id"),
    ("*_by", "varchar(n)", 64, None, "操作人编码，如 create_by、update_by、push_by"),
    # 布尔/状态
    ("status", "character(n)", 1, None, "状态位，0/1/2"),
    ("is_*", "character(n)", 1, None, "is_sys、is_show、is_pk、is_null、is_list 等布尔标志"),
    ("has_*", "character(n)", 1, None),
    ("can_*", "character(n)", 1, None),
    ("read_status", "character(n)", 1, None),
    ("mgr_type", "character(n)", 1, None),
    ("data_scope", "character(n)", 1, None),
    ("user_type", "varchar(n)", 16, None, "用户类型，short string"),
    ("content_level", "character(n)", 1, None),
    ("content_type", "character(n)", 1, None),
    ("receive_type", "character(n)", 1, None),
    ("rule_type", "character(n)", 1, None),
    ("menu_type", "character(n)", 1, None),
    ("office_type", "character(n)", 1, None),
    ("push_status", "character(n)", 1, None),
    ("sex", "character(n)", 1, None),
    # 时间
    ("*_date", "datetime", None, None, "所有 *_date 后缀 → datetime（create_date、send_date、read_date 等）"),
    # 名称（中文多的用 nvarchar）
    ("*_name", "nvarchar(n)", 100, None, "office_name、company_name、msg_title、user_name 等"),
    ("*_label", "nvarchar(n)", 100, None),
    ("*_title", "varchar(n)", 200, None, "msg_title"),
    ("*_code_view", "varchar(n)", 100, None, "view_code（树形展现代码）"),
    ("*_sort", "decimal(p)", 10, None, "排序/权重，整数但用 decimal 存储"),
    ("weight", "decimal(p)", 4, None),
    ("job_priority", "decimal(p)", 10, None),
    ("pwd_security_level", "decimal(p)", 1, None),
    # 说明/描述/备注
    ("description", "nvarchar(n)", 500, None),
    ("comments", "nvarchar(n)", 500, None),
    ("options", "nvarchar(n)", 1000, None),
    ("remarks", "nvarchar(n)", 500, None),
    ("sign", "nvarchar(n)", 200, None),
    ("*_content", "clob", None, None, "msg_content、exception_info、column_content 等大文本"),
    ("*_config", "clob", None, None, "field_config、rule_config"),
    ("*_modify_data", "clob", None, None),
    # 联系方式
    ("phone", "varchar(n)", 100, None),
    ("mobile", "varchar(n)", 100, None),
    ("email", "varchar(n)", 300, None),
    ("address", "varchar(n)", 255, None),
    ("zip_code", "varchar(n)", 100, None),
    ("login_code", "varchar(n)", 100, None),
    ("login_ip", "varchar(n)", 100, None),
    ("last_login_ip", "varchar(n)", 100, None),
    ("password", "varchar(n)", 200, None),
    ("avatar", "varchar(n)", 1000, None),
    ("wx_openid", "varchar(n)", 100, None),
    # 业务
    ("biz_key", "varchar(n)", 64, None),
    ("biz_type", "varchar(n)", 64, None),
    ("module_code", "varchar(n)", 64, None),
    ("module_codes", "varchar(n)", 500, None),
    ("component", "varchar(n)", 500, None),
    ("params", "varchar(n)", 500, None),
    ("permission", "varchar(n)", 1000, None),
    ("menu_href", "varchar(n)", 1000, None),
    ("class_name", "varchar(n)", 500, None),
    ("package_name", "varchar(n)", 500, None),
    ("*_return_content", "clob", None, None),
    ("*_return_code", "varchar(n)", 200, None),
    ("*_return_msg_id", "varchar(n)", 200, None),
    # 文件
    ("file_name", "nvarchar(n)", 500, None),
    ("file_path", "nvarchar(n)", 1000, None),
    ("file_content_type", "varchar(n)", 200, None),
    ("file_extension", "varchar(n)", 100, None),
    ("file_size", "decimal(p)", 31, None),
    ("file_md5", "varchar(n)", 64, None),
    ("file_preview", "character(n)", 1, None),
    ("file_meta", "varchar(n)", 255, None),
    ("file_type", "varchar(n)", 20, None),
    ("file_sort", "decimal(p)", 10, None),
    # 代码生成相关
    ("column_sort", "decimal(p)", 10, None),
    ("column_type", "varchar(n)", 100, None),
    ("column_label", "nvarchar(n)", 50, None),
    ("attr_name", "varchar(n)", 200, None),
    ("attr_type", "varchar(n)", 200, None),
    ("query_type", "varchar(n)", 200, None),
    ("show_type", "varchar(n)", 200, None),
    # 日志相关
    ("log_type", "varchar(n)", 50, None),
    ("log_title", "nvarchar(n)", 500, None),
    ("request_uri", "nvarchar(n)", 500, None),
    ("request_method", "varchar(n)", 10, None),
    ("request_params", "longtext", None, None),
    ("remote_addr", "varchar(n)", 255, None),
    ("server_addr", "varchar(n)", 255, None),
    ("user_agent", "nvarchar(n)", 500, None),
    ("device_name", "varchar(n)", 100, None),
    ("browser_name", "varchar(n)", 100, None),
    ("execute_time", "decimal(p)", 19, None),
    ("is_exception", "character(n)", 1, None),
    ("exception_info", "clob", None, None),
    # 默认（未匹配到时）— 字符串用 varchar(255)
    ("*", "varchar(n)", 255, None, "兜底：未匹配到规则的列名"),
]

# JeeSite 公共列分组（来自 core.erm 的 6 个 column_group）
# 每个分组是一组命名上的列集合，由 ERM 通过列组机制在多表间复用
JEESITE_COLUMN_GROUPS = [
    # 分组 1：基础 id + status
    {"physical_name": "cg_basic", "logical_name": "基础(id,status)",
     "columns": [
         {"name": "id", "logical": "编号", "type": "varchar(n)", "length": 64, "pk": True, "nn": True},
         {"name": "status", "logical": "状态", "type": "character(n)", "length": 1, "nn": True},
     ]},
    # 分组 2：公司维度 corp
    {"physical_name": "cg_corp", "logical_name": "公司维度",
     "columns": [
         {"name": "corp_code", "logical": "公司编码", "type": "varchar(n)", "length": 64},
         {"name": "corp_name", "logical": "公司名称", "type": "nvarchar(n)", "length": 200},
     ]},
    # 分组 3：完整审计字段（最常用）
    {"physical_name": "cg_audit_full", "logical_name": "审计(status,create/update/remarks)",
     "columns": [
         {"name": "status", "logical": "状态", "type": "character(n)", "length": 1, "nn": True},
         {"name": "create_by", "logical": "创建人", "type": "varchar(n)", "length": 64},
         {"name": "create_date", "logical": "创建时间", "type": "datetime"},
         {"name": "update_by", "logical": "更新人", "type": "varchar(n)", "length": 64},
         {"name": "update_date", "logical": "更新时间", "type": "datetime"},
         {"name": "remarks", "logical": "备注", "type": "nvarchar(n)", "length": 500},
     ]},
    # 分组 4：简化审计（无 status）
    {"physical_name": "cg_audit_simple", "logical_name": "审计(create/update/remarks)",
     "columns": [
         {"name": "create_by", "logical": "创建人", "type": "varchar(n)", "length": 64},
         {"name": "create_date", "logical": "创建时间", "type": "datetime"},
         {"name": "update_by", "logical": "更新人", "type": "varchar(n)", "length": 64},
         {"name": "update_date", "logical": "更新时间", "type": "datetime"},
         {"name": "remarks", "logical": "备注", "type": "nvarchar(n)", "length": 500},
     ]},
    # 分组 5：扩展字段（extend_s/i/f/d + json）
    {"physical_name": "cg_extend", "logical_name": "扩展字段",
     "columns": [
         {"name": "extend_s1", "type": "varchar(n)", "length": 255},
         {"name": "extend_s2", "type": "varchar(n)", "length": 255},
         {"name": "extend_s3", "type": "varchar(n)", "length": 255},
         {"name": "extend_s4", "type": "varchar(n)", "length": 255},
         {"name": "extend_s5", "type": "varchar(n)", "length": 255},
         {"name": "extend_s6", "type": "varchar(n)", "length": 255},
         {"name": "extend_s7", "type": "varchar(n)", "length": 255},
         {"name": "extend_s8", "type": "varchar(n)", "length": 255},
         {"name": "extend_i1", "type": "integer"},
         {"name": "extend_i2", "type": "integer"},
         {"name": "extend_i3", "type": "integer"},
         {"name": "extend_i4", "type": "integer"},
         {"name": "extend_f1", "type": "decimal(p)", "length": 19, "decimal": 6},
         {"name": "extend_f2", "type": "decimal(p)", "length": 19, "decimal": 6},
         {"name": "extend_f3", "type": "decimal(p)", "length": 19, "decimal": 6},
         {"name": "extend_f4", "type": "decimal(p)", "length": 19, "decimal": 6},
         {"name": "extend_d1", "type": "datetime"},
         {"name": "extend_d2", "type": "datetime"},
         {"name": "extend_d3", "type": "datetime"},
         {"name": "extend_d4", "type": "datetime"},
         {"name": "extend_json", "type": "clob"},
     ]},
    # 分组 6：树结构
    {"physical_name": "cg_tree", "logical_name": "树结构字段",
     "columns": [
         {"name": "parent_code", "logical": "父编码", "type": "varchar(n)", "length": 64},
         {"name": "parent_codes", "logical": "父编码链", "type": "varchar(n)", "length": 500},
         {"name": "tree_sort", "logical": "树排序", "type": "decimal(p)", "length": 10},
         {"name": "tree_sorts", "logical": "排序链", "type": "varchar(n)", "length": 500},
         {"name": "tree_leaf", "logical": "叶子标记", "type": "character(n)", "length": 1},
         {"name": "tree_level", "logical": "树层级", "type": "decimal(p)", "length": 10},
         {"name": "tree_names", "logical": "名称链", "type": "varchar(n)", "length": 500},
     ]},
]


def jeesite_infer_column_type(name):
    """
    按字段名推断类型（来自 core.erm 统计）。

    返回 (type_id, length, decimal)，未匹配到时返回 None。
    """
    lower = name.lower().strip()
    for rule in JEESITE_NAME_TYPE_HINTS:
        pattern, type_id, length, decimal = rule[0], rule[1], rule[2], rule[3]
        desc = rule[4] if len(rule) > 4 else None
        if pattern == "*":
            continue  # 跳过兜底规则
        if pattern.startswith("*_"):
            suffix = pattern[1:]  # 去掉前缀 *，得到 _code 或 code
            if lower.endswith(suffix):
                return type_id, length, decimal
        elif pattern.endswith("_*"):
            prefix = pattern[:-1]
            if lower.startswith(prefix):
                return type_id, length, decimal
        elif "*" in pattern:
            # 中间带 * 的简单匹配，如 "*_content"
            parts = pattern.split("*")
            if len(parts) == 2 and lower.startswith(parts[0]) and lower.endswith(parts[1]):
                return type_id, length, decimal
        else:
            if lower == pattern:
                return type_id, length, decimal
    # 兜底规则
    for rule in JEESITE_NAME_TYPE_HINTS:
        if rule[0] == "*":
            return rule[1], rule[2], rule[3]
    return None


class ErmError(Exception):
    """规格或文件错误，统一由 CLI 捕获并以退出码 2 结束。"""


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def sha1_id(seed):
    """生成 40 位十六进制 id（与 ERMaster IdGenerator 的形式一致）。"""
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()


def make_node_id(physical_name):
    """表/视图/备注等节点的 id。"""
    return sha1_id("NODE_ELEMENT_" + (physical_name or ""))


def make_column_id(table_name, column_name):
    """列 id，同一张表内按列名唯一。"""
    return sha1_id("COLUMN_{}_{}".format(table_name or "", column_name or ""))


def make_word_id(physical, logical, type_id, length, decimal, description):
    """字典词条 id，同一组属性共用一个词条（与 ERMaster 的去重语义一致）。"""
    return sha1_id("WORD_{}_{}_{}_{}_{}_{}".format(
        physical or "", logical or "", type_id or "", length, decimal, description or ""))


def make_relation_id(child_id, child_column, parent_id, parent_column):
    """关系（连线）id。"""
    return sha1_id("CONNECTION_{}_{}_{}_{}".format(child_id, child_column, parent_id, parent_column))


def make_environment_id(name):
    """环境（environment）id。"""
    return sha1_id("ENVIRONMENT_" + (name or ""))


def text_of(parent, tag, default=""):
    """读取直接子元素的文本，不存在时返回默认值。"""
    if parent is None:
        return default
    el = parent.find(tag)
    if el is None or el.text is None:
        return default
    return el.text


def int_of(parent, tag, default=0):
    """读取直接子元素的整数值。"""
    value = text_of(parent, tag, "")
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def bool_of(parent, tag, default=False):
    """读取直接子元素的布尔值（ERMaster 写 true/false）。"""
    value = text_of(parent, tag, "")
    if value == "":
        return default
    return value.strip().lower() == "true"


def bool_text(value):
    """布尔值转为 ERMaster 的文本形式。"""
    return "true" if value else "false"


def num_text(value):
    """数值转文本，None 转空串（对应 Java 中 Format.toString(null)）。"""
    if value is None:
        return ""
    return str(value)


def word_num_text(value):
    """字典词条中的数值文本，None 必须写成 null（Java 直接拼接 null）。"""
    if value is None:
        return "null"
    return str(value)


def reorder_children(parent, ordered_tags):
    """
    按规范顺序重排直接子元素，未列出的子元素保持原相对顺序放到末尾。

    ERMaster 的加载器用 getElementsByTagName 取“文档顺序中的第一个”，
    因此子元素顺序不能乱（否则表的 description 可能取到列的 description）。
    """
    children = list(parent)
    known = set(ordered_tags)
    ordered = []
    for tag in ordered_tags:
        ordered.extend([c for c in children if c.tag == tag])
    extras = [c for c in children if c.tag not in known]
    parent[:] = ordered + extras


def ensure_child(parent, tag, value=""):
    """确保存在指定直接子元素并写入文本；不存在则创建。"""
    el = parent.find(tag)
    if el is None:
        el = ET.SubElement(parent, tag)
    el.text = "" if value is None else str(value)
    return el


def ensure_empty_child(parent, tag):
    """确保存在指定直接子元素（元素节点），返回该元素。"""
    el = parent.find(tag)
    if el is None:
        el = ET.SubElement(parent, tag)
    return el


def set_scalar(parent, tag, value):
    """写入标量子元素；value 为 None 时写入空串。"""
    return ensure_child(parent, tag, "" if value is None else value)


def textext_escape(value):
    """ERMaster 的文本转义规则（PersistentXmlImpl.escape）。"""
    if value is None:
        return ""
    out = []
    for ch in str(value):
        if ch == "&":
            out.append("&amp;")
        elif ch == "<":
            out.append("&lt;")
        elif ch == ">":
            out.append("&gt;")
        elif ch == '"':
            out.append("&quot;")
        elif ch == "'":
            out.append("&apos;")
        elif ch == "\r":
            out.append("&#x0D;")
        elif ch == "\n":
            out.append("&#x0A;")
        elif ch == "\t":
            out.append("&#x09;")
        else:
            out.append(ch)
    return "".join(out)


def serialize(element, level=0, out=None):
    """
    将 ElementTree 节点序列化为 ERMaster 风格的 XML 文本。

    - 使用制表符缩进；
    - 空文本写成 <tag></tag>（与 ERMaster 输出一致）；
    - 保留注释节点。
    """
    if out is None:
        out = []
    indent = "\t" * level
    if element.tag is ET.Comment:
        out.append("{indent}<!--{text}-->\n".format(indent=indent, text=element.text or ""))
        return out
    if element.tag is ET.ProcessingInstruction:
        out.append("{indent}<?{text}?>\n".format(indent=indent, text=element.text or ""))
        return out

    tag = element.tag
    attrs = "".join(' {}="{}"'.format(k, textext_escape(v)) for k, v in element.attrib.items())
    children = list(element)
    text = element.text or ""

    if not children:
        out.append("{indent}<{tag}{attrs}>{text}</{tag}>\n".format(
            indent=indent, tag=tag, attrs=attrs, text=textext_escape(text)))
        return out

    out.append("{indent}<{tag}{attrs}>\n".format(indent=indent, tag=tag, attrs=attrs))
    if text.strip():
        # ERM 中不存在混合内容，这里仅作兜底
        out.append("{indent}\t{text}\n".format(indent=indent, text=textext_escape(text)))
    for child in children:
        serialize(child, level + 1, out)
    out.append("{indent}</{tag}>\n".format(indent=indent, tag=tag))
    return out


def write_erm(root, path):
    """
    把 XML 树写入 ERM 文件（UTF-8，带 XML 声明）。

    先写临时文件再原子替换，避免写入中断导致原文件损坏。
    """
    body = "".join(serialize(root, 0))
    content = '<?xml version="1.0" encoding="UTF-8"?>\n' + body
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    os.replace(tmp_path, path)


def load_erm(path):
    """解析 ERM 文件，保留注释节点。"""
    if not os.path.isfile(path):
        raise ErmError("文件不存在: " + path)
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    try:
        tree = ET.parse(path, parser=parser)
    except ET.ParseError as e:
        raise ErmError("XML 解析失败: {} ({})".format(path, e))
    root = tree.getroot()
    if root.tag != "diagram":
        raise ErmError("不是有效的 ERM 文件：根节点应为 <diagram>，实际为 <{}>".format(root.tag))
    # 清掉缩进产生的纯空白文本，避免 <categories> 这类空容器被写入换行/制表符
    for element in root.iter():
        if len(element) == 0 and element.text is not None and not element.text.strip():
            element.text = ""
    return root


# ---------------------------------------------------------------------------
# 类型解析
# ---------------------------------------------------------------------------

def _build_param_index():
    """
    建立“基准名 -> 参数形式 -> 类型 id”索引。

    例如 varchar(n)  -> {"varchar": {"n": "varchar(n)"}}
         decimal(p,s) -> {"decimal": {"p": "decimal(p)", "p,s": "decimal(p,s)"}}
         year(4)      -> {"year": {"4": "year(4)"}}
    """
    index = {}
    pattern = re.compile(r"^(.*?)\(([a-z0-9,]+)\)(.*)$")
    for type_id in ERM_TYPE_IDS:
        m = pattern.match(type_id)
        if not m:
            continue
        base = (m.group(1) + m.group(3)).strip()
        index.setdefault(base, {})[m.group(2)] = type_id
    return index


_PARAM_INDEX = _build_param_index()


def _normalize_type_text(value):
    """类型文本归一化：小写、压缩空白。"""
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def resolve_type(type_name, length=None, decimal=None):
    """
    把用户书写的类型解析为 ERM 的类型 id，并给出长度、精度。

    支持的写法：
        "varchar", length=64      -> ("varchar(n)", 64, None)
        "varchar(64)"             -> ("varchar(n)", 64, None)
        "decimal", 12, 2          -> ("decimal(p,s)", 12, 2)
        "decimal(12,2)"           -> ("decimal(p,s)", 12, 2)
        "int"                     -> ("integer", None, None)
        "varchar(n)", length=64   -> ("varchar(n)", 64, None)

    返回 (type_id, length, decimal)。
    """
    raw = (type_name or "").strip()
    if not raw:
        raise ErmError("列类型不能为空")

    # 长度/精度必须为非负整数，避免写出非法类型（如 varchar(0)）
    for label, value in (("length", length), ("decimal", decimal)):
        if value in (None, ""):
            continue
        try:
            number = int(value)
        except (TypeError, ValueError):
            raise ErmError("{} 必须是整数，当前为 {!r}".format(label, value))
        if number < 0:
            raise ErmError("{} 不能为负数: {}".format(label, number))
        if label == "length":
            length = number
        else:
            decimal = number

    low = _normalize_type_text(raw)

    # 1) 用户直接写了合法的类型 id
    if low in ERM_TYPE_ID_SET and ("(" in low or (length is None and decimal is None)):
        return low, length, decimal

    # 2) 形如 base(10,2) / base(64)
    m = re.match(r"^(.*?)\(\s*([0-9]+)\s*(?:,\s*([0-9]+)\s*)?\)(.*)$", low)
    if m:
        base = (m.group(1).strip() + (m.group(4) or "").strip()).strip()
        if m.group(3) is not None:
            length, decimal = int(m.group(2)), int(m.group(3))
        else:
            length = int(m.group(2))
            decimal = None
    else:
        base = low

    base = TYPE_ALIASES.get(base, base)
    params = _PARAM_INDEX.get(base, {})

    # 3) 带小数的类型，优先 (p,s)
    if decimal is not None:
        for key in ("p,s", "m,d"):
            if key in params:
                return params[key], length, decimal
        raise ErmError("类型 {} 不支持小数位设置".format(raw))

    # 4) 带长度的类型
    if length is not None:
        literal = "{}({})".format(base, length)
        if literal in ERM_TYPE_ID_SET:      # year(4) 这类字面量参数
            return literal, None, None
        for key in ("n", "p", "m"):
            if key in params:
                return params[key], length, None

    # 5) 无参类型
    if base in ERM_TYPE_ID_SET:
        return base, None, None
    for key in ("n", "p"):
        if key in params:
            return params[key], length, decimal

    raise ErmError(
        "未知类型: {!r}，请使用 ERM 类型 id（如 varchar、decimal、datetime、text）".format(raw))


# ---------------------------------------------------------------------------
# 构造基础节点
# ---------------------------------------------------------------------------

def build_color(parent, tag, rgb):
    """构造 <color><r><g><b></color>。"""
    color = ensure_child(parent, tag)
    for child in list(color):
        color.remove(child)
    set_scalar(color, "r", rgb[0])
    set_scalar(color, "g", rgb[1])
    set_scalar(color, "b", rgb[2])
    return color


def build_sequence_element():
    """构造列级 <sequence>（自增/序列设置），字段与 ERMaster 输出一致。"""
    seq = ET.Element("sequence")
    set_scalar(seq, "name", "")
    set_scalar(seq, "schema", "")
    set_scalar(seq, "increment", "")
    set_scalar(seq, "min_value", "")
    set_scalar(seq, "max_value", "")
    set_scalar(seq, "start", "")
    set_scalar(seq, "cache", "")
    set_scalar(seq, "nocache", "false")
    set_scalar(seq, "cycle", "false")
    set_scalar(seq, "order", "false")
    set_scalar(seq, "description", "")
    set_scalar(seq, "data_type", "")
    set_scalar(seq, "decimal_size", "0")
    return seq


def build_node_fields(element, node_id, x, y, height, width,
                      color=DEFAULT_COLOR, font=DEFAULT_FONT, font_size=DEFAULT_FONT_SIZE):
    """写入节点（表/视图/备注）的通用字段。"""
    set_scalar(element, "id", node_id)
    set_scalar(element, "height", int(height))
    set_scalar(element, "width", int(width))
    set_scalar(element, "font_name", font)
    set_scalar(element, "font_size", int(font_size))
    set_scalar(element, "x", int(x))
    set_scalar(element, "y", int(y))
    build_color(element, "color", color)
    ensure_empty_child(element, "connections")


def build_word_element(word_id, physical, logical, type_id, length, decimal,
                       description="", args="", char_semantics=False):
    """构造字典词条 <word>。"""
    word = ET.Element("word")
    set_scalar(word, "id", word_id)
    set_scalar(word, "length", word_num_text(length))
    set_scalar(word, "decimal", word_num_text(decimal))
    set_scalar(word, "array", "false")
    set_scalar(word, "array_dimension", "null")
    set_scalar(word, "unsigned", "false")
    set_scalar(word, "zerofill", "false")
    set_scalar(word, "binary", "false")
    set_scalar(word, "args", args or "")
    set_scalar(word, "char_semantics", bool_text(char_semantics))
    set_scalar(word, "description", description or "")
    set_scalar(word, "logical_name", logical or "")
    set_scalar(word, "physical_name", physical or "")
    set_scalar(word, "type", type_id or "")
    reorder_children(word, WORD_TAGS)
    return word


def build_normal_column(column_id, physical, logical, type_id, word_id=None,
                        referenced_column=None, relation=None, description="",
                        not_null=False, primary_key=False, unique_key=False,
                        auto_increment=False, default_value="", constraint="",
                        unique_key_name="", character_set="", collation=""):
    """
    构造 <normal_column>。

    注意：ERMaster 保存普通列时，physical_name / logical_name / description 均为空，
    名称与注释统一存放在字典词条（word_id）里；只有显式改名过的外键列才写 physical_name。
    这里保持同样的写法，确保输出与 ERMaster 自身保存的结果一致。
    """
    col = ET.Element("normal_column")
    if word_id:
        set_scalar(col, "word_id", word_id)
    set_scalar(col, "id", column_id)
    if referenced_column:
        set_scalar(col, "referenced_column", referenced_column)
    if relation:
        set_scalar(col, "relation", relation)
    set_scalar(col, "description", "" if word_id else (description or ""))
    set_scalar(col, "unique_key_name", unique_key_name or "")
    set_scalar(col, "logical_name", "" if word_id else (logical or ""))
    set_scalar(col, "physical_name", "" if word_id else (physical or ""))
    set_scalar(col, "type", type_id or "")
    set_scalar(col, "constraint", constraint or "")
    set_scalar(col, "default_value", default_value or "")
    set_scalar(col, "auto_increment", bool_text(auto_increment))
    set_scalar(col, "foreign_key", bool_text(bool(referenced_column)))
    set_scalar(col, "not_null", bool_text(not_null))
    set_scalar(col, "primary_key", bool_text(primary_key))
    set_scalar(col, "unique_key", bool_text(unique_key))
    set_scalar(col, "character_set", character_set or "")
    set_scalar(col, "collation", collation or "")
    col.append(build_sequence_element())
    reorder_children(col, COLUMN_TAGS)
    return col


def build_relation_element(relation_id, parent_id, child_id, referenced_column_id,
                           parent_cardinality="1", child_cardinality="1..n",
                           name="", on_delete="RESTRICT", on_update="RESTRICT",
                           reference_for_pk=False, referenced_complex_unique_key="null"):
    """构造 <relation>（写在子表的 <connections> 中）。"""
    rel = ET.Element("relation")
    set_scalar(rel, "id", relation_id)
    set_scalar(rel, "source", parent_id)
    set_scalar(rel, "target", child_id)
    set_scalar(rel, "source_xp", "-1")
    set_scalar(rel, "source_yp", "-1")
    set_scalar(rel, "target_xp", "-1")
    set_scalar(rel, "target_yp", "-1")
    build_color(rel, "color", (0, 0, 0))
    set_scalar(rel, "child_cardinality", child_cardinality or "1..n")
    set_scalar(rel, "parent_cardinality", parent_cardinality or "1")
    set_scalar(rel, "reference_for_pk", bool_text(reference_for_pk))
    set_scalar(rel, "name", name or "")
    set_scalar(rel, "on_delete_action", on_delete or "RESTRICT")
    set_scalar(rel, "on_update_action", on_update or "RESTRICT")
    set_scalar(rel, "referenced_column", referenced_column_id or "null")
    set_scalar(rel, "referenced_complex_unique_key", referenced_complex_unique_key or "null")
    reorder_children(rel, RELATION_TAGS)
    return rel


# ---------------------------------------------------------------------------
# 文档骨架
# ---------------------------------------------------------------------------

def build_empty_diagram(database="StandardSQL", environment_name="Default",
                       use_jeesite_convention=True):
    """
    构造一份最小且完整的 ERM 文档骨架（所有加载器要求的节点都齐备）。

    use_jeesite_convention=True 时，沿用 core.erm 的风格：
    table_style=funny、notation=IE、zoom=0.8、初始化 6 个公共列分组。
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    environment_id = make_environment_id(environment_name)

    # JeeSite 约定
    table_style = JEESITE_DEFAULT_TABLE_STYLE if use_jeesite_convention else ""
    notation = JEESITE_DEFAULT_NOTATION if use_jeesite_convention else ""
    zoom = JEESITE_DEFAULT_ZOOM if use_jeesite_convention else "1.0"

    root = ET.Element("diagram")

    # page_setting
    page = ET.SubElement(root, "page_setting")
    set_scalar(page, "direction_horizontal", "true")
    set_scalar(page, "scale", "100")
    set_scalar(page, "paper_size", "A4 210 x 297 mm")
    set_scalar(page, "top_margin", "30")
    set_scalar(page, "left_margin", "30")
    set_scalar(page, "bottom_margin", "30")
    set_scalar(page, "right_margin", "30")

    set_scalar(root, "category_index", "0")
    set_scalar(root, "zoom", zoom)
    set_scalar(root, "x", "0")
    set_scalar(root, "y", "18")
    build_color(root, "default_color", DEFAULT_COLOR)
    build_color(root, "color", DEFAULT_COLOR)
    set_scalar(root, "font_name", DEFAULT_FONT)
    set_scalar(root, "font_size", str(DEFAULT_FONT_SIZE))

    # settings
    settings = ET.SubElement(root, "settings")
    set_scalar(settings, "database", database)
    set_scalar(settings, "capital", "false")
    set_scalar(settings, "table_style", table_style)
    set_scalar(settings, "notation", notation)
    set_scalar(settings, "notation_level", "0")
    set_scalar(settings, "notation_expand_group", "true")
    set_scalar(settings, "view_mode", "2")
    set_scalar(settings, "outline_view_mode", "1")
    set_scalar(settings, "view_order_by", "1")
    set_scalar(settings, "auto_ime_change", "false")
    set_scalar(settings, "validate_physical_name", "true")
    set_scalar(settings, "use_bezier_curve", "false")
    set_scalar(settings, "suspend_validator", "false")

    export = ET.SubElement(settings, "export_setting")
    ddl = ET.SubElement(export, "export_ddl_setting")
    set_scalar(ddl, "output_path", "db/dbms.sql")
    set_scalar(ddl, "encoding", "UTF-8")
    set_scalar(ddl, "line_feed", "CR+LF")
    set_scalar(ddl, "is_open_after_saved", "false")
    set_scalar(ddl, "environment_id", environment_id)
    set_scalar(ddl, "category_id", "null")
    ddl_target = ET.SubElement(ddl, "ddl_target")
    for tag, value in (
        ("create_comment", "true"), ("create_foreignKey", "false"), ("create_index", "true"),
        ("create_sequence", "false"), ("create_table", "true"), ("create_tablespace", "false"),
        ("create_trigger", "false"), ("create_view", "false"), ("drop_index", "false"),
        ("drop_sequence", "false"), ("drop_table", "false"), ("drop_tablespace", "false"),
        ("drop_trigger", "false"), ("drop_view", "false"), ("inline_column_comment", "false"),
        ("inline_table_comment", "true"), ("comment_value_description", "false"),
        ("comment_value_logical_name", "true"), ("comment_value_logical_name_description", "false"),
        ("comment_replace_line_feed", "false"), ("comment_replace_string", ""),
    ):
        set_scalar(ddl_target, tag, value)

    excel = ET.SubElement(export, "export_excel_setting")
    set_scalar(excel, "category_id", "null")
    set_scalar(excel, "output_path", "db/dbms.xls")
    set_scalar(excel, "template", "")
    set_scalar(excel, "template_path", "")
    set_scalar(excel, "used_default_template_lang", "zh")
    set_scalar(excel, "image_output", "")
    set_scalar(excel, "is_open_after_saved", "true")
    set_scalar(excel, "is_put_diagram", "true")
    set_scalar(excel, "is_use_logical_name", "true")

    html = ET.SubElement(export, "export_html_setting")
    set_scalar(html, "output_dir", "")
    set_scalar(html, "with_category_image", "true")
    set_scalar(html, "with_image", "true")
    set_scalar(html, "is_open_after_saved", "true")

    image = ET.SubElement(export, "export_image_setting")
    set_scalar(image, "output_file_path", "db/dbms.png")
    set_scalar(image, "category_dir_path", "")
    set_scalar(image, "with_category_image", "true")
    set_scalar(image, "is_open_after_saved", "true")

    java = ET.SubElement(export, "export_java_setting")
    set_scalar(java, "java_output", "")
    set_scalar(java, "package_name", "")
    set_scalar(java, "class_name_suffix", "")
    set_scalar(java, "src_file_encoding", "")
    set_scalar(java, "with_hibernate", "false")

    testdata = ET.SubElement(export, "export_testdata_setting")
    set_scalar(testdata, "file_encoding", "")
    set_scalar(testdata, "file_path", "")
    set_scalar(testdata, "format", "0")

    category_settings = ET.SubElement(settings, "category_settings")
    set_scalar(category_settings, "free_layout", "false")
    set_scalar(category_settings, "show_referred_tables", "false")
    ET.SubElement(category_settings, "categories")

    translation_settings = ET.SubElement(settings, "translation_settings")
    set_scalar(translation_settings, "use", "false")
    ET.SubElement(translation_settings, "translations")

    model_properties = ET.SubElement(settings, "model_properties")
    build_node_fields(model_properties, "", 50, 50, -1, -1, color=(255, 255, 255))
    set_scalar(model_properties, "display", "false")
    set_scalar(model_properties, "creation_date", now)
    for name in ("Project Name", "Model Name", "Version", "Company", "Author"):
        prop = ET.SubElement(model_properties, "model_property")
        set_scalar(prop, "name", name)
        set_scalar(prop, "value", "")
    reorder_children(model_properties, [
        "id", "height", "width", "font_name", "font_size", "x", "y", "color", "connections",
        "display", "creation_date", "model_property",
    ])

    table_properties = ET.SubElement(settings, "table_properties")
    set_scalar(table_properties, "schema", "")

    environment_setting = ET.SubElement(settings, "environment_setting")
    environment = ET.SubElement(environment_setting, "environment")
    set_scalar(environment, "id", environment_id)
    set_scalar(environment, "name", environment_name)

    # 其余顶层容器
    ET.SubElement(root, "dictionary")
    ET.SubElement(root, "tablespace_set")
    ET.SubElement(root, "contents")
    column_groups_el = ET.SubElement(root, "column_groups")
    ET.SubElement(root, "test_data_list")
    ET.SubElement(root, "sequence_set")
    ET.SubElement(root, "trigger_set")
    ET.SubElement(root, "change_tracking_list")

    # 初始化 JeeSite 6 个公共列分组
    if use_jeesite_convention:
        build_jeesite_column_groups(root, column_groups_el)

    return root


def build_jeesite_column_groups(root, column_groups_el):
    """
    在 column_groups 节点下注册 JeeSite 的 6 个公共列分组，
    同时把每个分组内的列写入 dictionary（column_group 里的列只有 word_id 引用）。
    """
    dictionary = root.find("dictionary")

    def _normalise_length(val):
        """把 word 元素里存的 length/decimal 统一成比较用的字符串。"""
        if val is None:
            return ""
        v = val.strip() if isinstance(val, str) else str(val)
        if v in ("", "null", "None"):
            return ""
        return v

    def _ensure_word(name, logical, type_id, length, decimal, description):
        """向 dictionary 追加词条（id 已存在时跳过）。"""
        # 先按完整 id 查找（最快）
        existing_by_key = None
        for w in dictionary.findall("word"):
            if (w.findtext("physical_name") == name
                    and w.findtext("type") == type_id
                    and _normalise_length(w.findtext("length")) == _normalise_length(length)):
                existing_by_key = w
                break
        if existing_by_key is not None:
            return text_of(existing_by_key, "id")
        wid = sha1_id("WORD_{}_{}_{}_{}_{}_{}".format(
            name or "", logical or "", type_id or "",
            length if length is not None else None,
            decimal if decimal is not None else None,
            description or ""))
        # 即使物理类型相同但长度不同，wid 也应该不同；如果意外同了就跳过
        for w in dictionary.findall("word"):
            if text_of(w, "id") == wid:
                return wid
        word = ET.SubElement(dictionary, "word")
        set_scalar(word, "id", wid)
        set_scalar(word, "length", str(length) if length is not None else "null")
        set_scalar(word, "decimal", str(decimal) if decimal is not None else "null")
        set_scalar(word, "array", "false")
        set_scalar(word, "array_dimension", "null")
        set_scalar(word, "unsigned", "false")
        set_scalar(word, "zerofill", "false")
        set_scalar(word, "binary", "false")
        set_scalar(word, "args", "")
        set_scalar(word, "char_semantics", "false")
        set_scalar(word, "description", description or "")
        set_scalar(word, "logical_name", logical or "")
        set_scalar(word, "physical_name", name or "")
        set_scalar(word, "type", type_id or "")
        return wid

    for cg_def in JEESITE_COLUMN_GROUPS:
        cg_id = sha1_id("COLUMN_GROUP_" + (cg_def.get("physical_name") or cg_def.get("logical_name") or ""))
        cg = ET.SubElement(column_groups_el, "column_group")
        set_scalar(cg, "id", cg_id)
        set_scalar(cg, "physical_name", cg_def.get("physical_name", ""))
        set_scalar(cg, "logical_name", cg_def.get("logical_name", ""))
        set_scalar(cg, "description", "")
        cols_el = ET.SubElement(cg, "columns")
        for col in cg_def.get("columns", []):
            type_id, length, decimal = resolve_type(col.get("type"), col.get("length"), col.get("decimal"))
            wid = _ensure_word(col.get("name", ""), col.get("logical", ""),
                                type_id, length, decimal, col.get("comment", ""))
            c_col = ET.SubElement(cols_el, "column")
            set_scalar(c_col, "word_id", wid)


# ---------------------------------------------------------------------------
# 规格解析与写入
# ---------------------------------------------------------------------------

class IdRegistry(object):
    """维护 id 索引，避免重复写入同一个节点。"""

    def __init__(self, root):
        self.root = root
        self.words = {}          # word id -> word 元素
        self.word_keys = {}      # (物理名, 逻辑名, 类型, 长度, 精度, 描述) -> word id
        self.columns = {}        # column id -> normal_column
        self.tables = {}         # 表物理名 -> table 元素
        self.refresh()

    def refresh(self):
        """扫描文档，重建字典词条与列索引。"""
        dictionary = self.root.find("dictionary")
        if dictionary is not None:
            for word in dictionary.findall("word"):
                wid = text_of(word, "id")
                if not wid:
                    continue
                self.words[wid] = word
                key = self._word_key(
                    text_of(word, "physical_name"), text_of(word, "logical_name"),
                    text_of(word, "type"), text_of(word, "length"),
                    text_of(word, "decimal"), text_of(word, "description"))
                self.word_keys.setdefault(key, wid)
        contents = self.root.find("contents")
        if contents is not None:
            for table in contents.findall("table"):
                name = text_of(table, "physical_name")
                if name:
                    self.tables[name] = table
                for col in table.iter("normal_column"):
                    cid = text_of(col, "id")
                    if cid:
                        self.columns[cid] = col
            for view in contents.findall("view"):
                for col in view.iter("normal_column"):
                    cid = text_of(col, "id")
                    if cid:
                        self.columns[cid] = col

    @staticmethod
    def _word_key(physical, logical, type_id, length, decimal, description):
        return (physical or "", logical or "", type_id or "",
                "" if length in (None, "null") else str(length),
                "" if decimal in (None, "null") else str(decimal), description or "")

    def ensure_word(self, physical, logical, type_id, length, decimal, description="",
                    args="", char_semantics=False):
        """确保字典中存在对应词条，返回词条 id。"""
        key = self._word_key(physical, logical, type_id, length, decimal, description)
        wid = self.word_keys.get(key)
        if wid and wid in self.words:
            return wid
        wid = make_word_id(physical, logical, type_id, length, decimal, description)
        if wid not in self.words:
            dictionary = self.root.find("dictionary")
            if dictionary is None:
                dictionary = ET.SubElement(self.root, "dictionary")
            word = build_word_element(wid, physical, logical, type_id, length, decimal,
                                      description, args, char_semantics)
            dictionary.append(word)
            self.words[wid] = word
        self.word_keys[key] = wid
        return wid

    def ensure_table(self, contents, physical_name):
        """按物理名查找表，不存在则创建空表节点。"""
        for table in contents.findall("table"):
            if text_of(table, "physical_name") == physical_name:
                self.tables[physical_name] = table
                return table, False
        table = ET.SubElement(contents, "table")
        return table, True

    def replace(self, old, new):
        """用新构造的元素替换旧元素，保持其在父节点中的位置。"""
        parent = self.find_parent(old)
        if parent is None:
            return new
        index = list(parent).index(old)
        parent.remove(old)
        parent.insert(index, new)
        return new

    def find_parent(self, target):
        """在文档树中查找 target 的父节点。"""
        return _find_parent(self.root, target)

    def resolve_column(self, column):
        """沿 referenced_column 链找到承载字典词条的列（外键列自身没有 word_id）。"""
        seen = set()
        current = column
        while True:
            cid = text_of(current, "id")
            ref = text_of(current, "referenced_column")
            if not ref or ref in seen:
                return current
            seen.add(cid)
            nxt = self.columns.get(ref)
            if nxt is None:
                return current
            current = nxt

    def column_field(self, column, tag):
        """
        读取列的有效字段值（与 NormalColumn 的 getter 行为一致）：
        先取列自身的值，为空则回溯到所引用列对应的字典词条。
        """
        own = text_of(column, tag)
        if own:
            return own
        source = self.resolve_column(column)
        word = self.words.get(text_of(source, "word_id"))
        if word is not None:
            return text_of(word, tag)
        return text_of(source, tag)

    def column_name(self, column):
        """列的有效物理名。"""
        return self.column_field(column, "physical_name")

    def find_column(self, table, name, include_foreign_key=True):
        """
        按有效物理名查找表内列。

        ERMaster 的普通列不写 physical_name（名称在字典词条里），
        因此必须通过 word 解析后再比较。
        """
        columns = table.find("columns")
        if columns is None:
            return None
        for col in columns.findall("normal_column"):
            is_fk = bool(text_of(col, "referenced_column"))
            if is_fk and not include_foreign_key:
                continue
            if self.column_name(col) == name:
                return col
        return None


def parse_position(spec, default_x, default_y):
    """解析 position / x / y 规格。"""
    position = spec.get("position") or {}
    x = spec.get("x", position.get("x", default_x))
    y = spec.get("y", position.get("y", default_y))
    return int(x), int(y)


def estimate_table_size(columns):
    """按列数估算表格显示尺寸（ERMaster 打开后仍可正常使用）。"""
    height = max(DEFAULT_TABLE_HEIGHT, 30 + 22 * max(1, len(columns)))
    width = DEFAULT_TABLE_WIDTH
    for col in columns:
        name = col.get("name") or ""
        width = max(width, 12 * len(name) + 120)
    return min(width, 400), height


def upsert_column(table_el, table_name, spec, registry):
    """
    在表中新增或更新一列，返回 normal_column 元素。

    - 普通列：写入 word_id，长度/精度记录在字典词条中；
    - 外键列（带 references 规格时由关系逻辑创建，不在此处理）。
    """
    columns_el = ensure_empty_child(table_el, "columns")
    name = (spec.get("name") or "").strip()
    if not name:
        raise ErmError("表 {} 中存在缺少 name 的列".format(table_name))

    existing = registry.find_column(table_el, name, include_foreign_key=False)

    if existing is None:
        col = ET.SubElement(columns_el, "normal_column")
    else:
        col = existing

    # 类型：规格未给出时沿用已有列（优先取其字典词条，保证长度/精度不丢失）
    type_name = spec.get("type")
    length = spec.get("length", spec.get("size"))
    decimal = spec.get("decimal", spec.get("scale"))
    if type_name is None and length is None and decimal is None and existing is not None:
        old_word = registry.words.get(text_of(registry.resolve_column(col), "word_id"))
        if old_word is not None:
            type_name = text_of(old_word, "type")
            length = text_of(old_word, "length")
            decimal = text_of(old_word, "decimal")
            length = None if length in ("", "null") else int(length)
            decimal = None if decimal in ("", "null") else int(decimal)
        else:
            type_name = text_of(col, "type")
    # 新列且规格未给 type：按 JeeSite 字段名习惯推断
    if type_name is None and existing is None:
        inferred = jeesite_infer_column_type(name)
        if inferred is not None:
            type_name, length, decimal = inferred
    if not type_name:
        raise ErmError("列 {}.{} 缺少 type".format(table_name, name))
    type_id, length, decimal = resolve_type(type_name, length, decimal)

    # 未在规格中出现的字段沿用已有值（含字典词条中的名称与注释）
    logical = spec.get("logical_name", registry.column_field(col, "logical_name"))
    description = spec.get("description", spec.get(
        "comment", registry.column_field(col, "description")))
    primary_key = bool(spec.get("primary_key", spec.get("pk", bool_of(col, "primary_key"))))
    not_null = bool(spec.get("not_null", spec.get("nn", primary_key or bool_of(col, "not_null"))))
    unique_key = bool(spec.get("unique_key", bool_of(col, "unique_key")))
    auto_increment = bool(spec.get("auto_increment", bool_of(col, "auto_increment")))
    default_value = spec.get("default_value", text_of(col, "default_value", ""))
    constraint = spec.get("constraint", text_of(col, "constraint", ""))
    unique_key_name = spec.get("unique_key_name", text_of(col, "unique_key_name", ""))
    character_set = spec.get("character_set", text_of(col, "character_set", ""))
    collation = spec.get("collation", text_of(col, "collation", ""))

    word_id = registry.ensure_word(name, logical, type_id, length, decimal, description)
    column_id = text_of(col, "id") or make_column_id(table_name, name)

    fresh = build_normal_column(
        column_id=column_id, physical=name, logical=logical, type_id=type_id,
        word_id=word_id, description=description, not_null=not_null,
        primary_key=primary_key, unique_key=unique_key, auto_increment=auto_increment,
        default_value=default_value, constraint=constraint,
        unique_key_name=unique_key_name, character_set=character_set, collation=collation)

    registry.replace(col, fresh)
    registry.columns[column_id] = fresh
    return fresh


def _find_parent(root, target):
    """在树中查找 target 的父节点。"""
    if root is None:
        return None
    for child in root:
        if child is target:
            return root
        found = _find_parent(child, target)
        if found is not None:
            return found
    return None


def upsert_table(root, spec, registry, default_x=100, default_y=100):
    """新增或更新一张表（含列、索引、唯一键、表属性）。"""
    contents = root.find("contents")
    if contents is None:
        contents = ET.SubElement(root, "contents")
    name = (spec.get("name") or "").strip()
    if not name:
        raise ErmError("表规格缺少 name")

    table, is_new = registry.ensure_table(contents, name)
    columns_spec = spec.get("columns") or []

    # 已有表未指定坐标/尺寸时保持原值，避免无谓改动
    est_width, est_height = estimate_table_size(columns_spec)
    if is_new:
        x, y = parse_position(spec, default_x, default_y)
        width = int(spec.get("width", est_width))
        height = int(spec.get("height", est_height))
    else:
        x, y = parse_position(spec, int_of(table, "x", default_x), int_of(table, "y", default_y))
        width = int(spec.get("width", int_of(table, "width", est_width)))
        height = int(spec.get("height", int_of(table, "height", est_height)))
    table_id = text_of(table, "id") or make_node_id(name)

    build_node_fields(table, table_id, x, y, height, width)
    set_scalar(table, "physical_name", name)
    set_scalar(table, "logical_name", spec.get("logical_name", text_of(table, "logical_name")))
    set_scalar(table, "description", spec.get("description", text_of(table, "description")))
    set_scalar(table, "constraint", spec.get("constraint", text_of(table, "constraint")))
    pk_name = (spec.get("primary_key_name")
               or text_of(table, "primary_key_name")
               or make_constraint_name("pk", name))
    if _is_reserved_word(pk_name):
        _warn("主键名 {} 命中 SQL 关键字（表 {}）".format(pk_name, name))
    if len(pk_name) > MAX_IDENTIFIER_LEN:
        _warn("主键名 {} 长度 {} 超过上限 {}（表 {}）".format(
            pk_name, len(pk_name), MAX_IDENTIFIER_LEN, name))
    set_scalar(table, "primary_key_name", pk_name)
    set_scalar(table, "option", spec.get("option", text_of(table, "option")))
    ensure_empty_child(table, "columns")
    ensure_empty_child(table, "indexes")
    ensure_empty_child(table, "complex_unique_key_list")
    props = table.find("table_properties")
    ensure_table_properties(table, spec.get("schema", text_of(props, "schema") if props is not None else ""))
    reorder_children(table, TABLE_TAGS)

    for column_spec in columns_spec:
        upsert_column(table, name, column_spec, registry)

    for drop_name in spec.get("drop_columns") or []:
        drop_column(table, name, drop_name, registry)

    if "indexes" in spec:
        build_indexes(table, name, spec.get("indexes") or [], registry)
    if "unique_keys" in spec:
        build_unique_keys(table, name, spec.get("unique_keys") or [], registry)

    registry.tables[name] = table
    return table


def ensure_table_properties(table, schema):
    """确保 <table_properties> 存在并写入 schema。"""
    props = ensure_empty_child(table, "table_properties")
    set_scalar(props, "schema", schema or "")
    return props


def normalize_table_properties(root):
    """
    MySQL 图在保存时，ERMaster 会为每处 table_properties 补写
    character_set / collation / storage_engine / primary_key_length_of_text，
    这里同步补齐（已有值保持不变），保证与 ERMaster 的输出一致。
    """
    settings = root.find("settings")
    if text_of(settings, "database") != "MySQL":
        return
    tags = ["schema", "character_set", "collation", "storage_engine",
            "primary_key_length_of_text"]
    for props in root.iter("table_properties"):
        defaults = {
            "schema": "",
            "character_set": "",
            "collation": "",
            "storage_engine": "",
            "primary_key_length_of_text": "null",
        }
        for tag in tags:
            if props.find(tag) is None:
                set_scalar(props, tag, defaults[tag])
        reorder_children(props, tags)


def build_indexes(table, table_name, indexes_spec, registry):
    """重建表的索引列表（<indexes> 下沿用 ERMaster 的 <inidex> 拼写）。

    索引名 name 可选：未写时按 make_constraint_name("idx", 表名, *列名) 自动生成。
    生成的名字自动裁到 MAX_IDENTIFIER_LEN=30 以内（Oracle 兼容），
    命中 SQL 关键字时输出警告（不中断）。
    """
    indexes = ensure_empty_child(table, "indexes")
    for child in list(indexes):
        indexes.remove(child)
    for item in indexes_spec:
        cols = list(item.get("columns") or [])
        name = item.get("name") or make_constraint_name("idx", table_name, *cols)
        # 最终关键字/长度二次校验
        if _is_reserved_word(name):
            _warn("索引名 {} 命中 SQL 关键字（表 {}）".format(name, table_name))
        if len(name) > MAX_IDENTIFIER_LEN:
            _warn("索引名 {} 长度 {} 超过上限 {}（表 {}）".format(
                name, len(name), MAX_IDENTIFIER_LEN, table_name))
        index = ET.SubElement(indexes, "inidex")
        set_scalar(index, "full_text", bool_text(bool(item.get("full_text", False))))
        set_scalar(index, "non_unique", bool_text(not bool(item.get("unique", False))))
        set_scalar(index, "name", name)
        set_scalar(index, "type", item.get("type", "") or "")
        set_scalar(index, "description", item.get("description", "") or "")
        columns_el = ET.SubElement(index, "columns")
        for col_name in cols:
            column_el = registry.find_column(table, col_name, include_foreign_key=False)
            if column_el is None:
                raise ErmError("表 {} 的索引 {} 引用了不存在的列 {}".format(
                    table_name, name, col_name))
            column_el_parent = ET.SubElement(columns_el, "column")
            set_scalar(column_el_parent, "id", text_of(column_el, "id"))
            set_scalar(column_el_parent, "desc", bool_text(bool(item.get("desc", False))))
        reorder_children(index, INDEX_TAGS)


def build_unique_keys(table, table_name, unique_keys_spec, registry):
    """重建表的复合唯一键列表。name 可选，自动生成 uk_<表后缀>_<列缩写>。"""
    container = ensure_empty_child(table, "complex_unique_key_list")
    for child in list(container):
        container.remove(child)
    for item in unique_keys_spec:
        cols = list(item.get("columns") or [])
        name = item.get("name") or make_constraint_name("uk", table_name, *cols)
        if _is_reserved_word(name):
            _warn("唯一键名 {} 命中 SQL 关键字（表 {}）".format(name, table_name))
        if len(name) > MAX_IDENTIFIER_LEN:
            _warn("唯一键名 {} 长度 {} 超过上限 {}（表 {}）".format(
                name, len(name), MAX_IDENTIFIER_LEN, table_name))
        key = ET.SubElement(container, "complex_unique_key")
        set_scalar(key, "id", sha1_id("COMPLEX_UNIQUE_KEY_{}_{}".format(table_name, name)))
        set_scalar(key, "name", name)
        columns_el = ET.SubElement(key, "columns")
        for col_name in item.get("columns") or []:
            column_el = registry.find_column(table, col_name, include_foreign_key=False)
            if column_el is None:
                raise ErmError("表 {} 的唯一键 {} 引用了不存在的列 {}".format(
                    table_name, name, col_name))
            wrapper = ET.SubElement(columns_el, "column")
            set_scalar(wrapper, "id", text_of(column_el, "id"))


def find_relation_column(table, column_name, registry):
    """查找列：既支持自定义物理名，也支持名称存放在字典词条中的情况。"""
    return registry.find_column(table, column_name)


def drop_column(table, table_name, column_name, registry):
    """删除列，并清理索引/唯一键中的引用；外键列需先删除关系。"""
    column_el = registry.find_column(table, column_name)
    if column_el is None:
        raise ErmError("表 {} 中不存在列 {}".format(table_name, column_name))
    if text_of(column_el, "referenced_column") or text_of(column_el, "relation"):
        raise ErmError("列 {}.{} 是外键列，请先删除对应关系".format(table_name, column_name))
    column_id = text_of(column_el, "id")
    columns = table.find("columns")
    columns.remove(column_el)

    indexes = table.find("indexes")
    if indexes is not None:
        for index in list(indexes):
            cols_el = index.find("columns")
            if cols_el is None:
                continue
            for wrapper in list(cols_el):
                if text_of(wrapper, "id") == column_id:
                    cols_el.remove(wrapper)

    container = table.find("complex_unique_key_list")
    if container is not None:
        for key in list(container):
            cols_el = key.find("columns")
            if cols_el is None:
                continue
            for wrapper in list(cols_el):
                if text_of(wrapper, "id") == column_id:
                    cols_el.remove(wrapper)


def create_foreign_key_column(child_table, child_name, parent_column, parent_column_name,
                              relation_id, child_column_name=None):
    """
    在子表中创建外键列（与 ERMaster Relation.setTargetTableView 的行为一致）：
    不写 word_id，类型与注释由 referenced_column 继承。

    外键列名与父列同名时留空 physical_name（ERMaster 的默认继承方式）；
    需要自定义外键列名时写入 physical_name。
    """
    columns = ensure_empty_child(child_table, "columns")
    if child_column_name is None or child_column_name == parent_column_name:
        physical = ""
        column_id = make_column_id(child_name, parent_column_name)
    else:
        physical = child_column_name
        column_id = make_column_id(child_name, child_column_name)
    column = build_normal_column(
        column_id=column_id,
        physical=physical, logical="", type_id=text_of(parent_column, "type"),
        referenced_column=text_of(parent_column, "id"),
        relation=relation_id,
        description="",
        not_null=bool_of(parent_column, "not_null", False),
        primary_key=False,
        unique_key=False,
        auto_increment=False)
    columns.append(column)
    return column


def upsert_relation(root, spec, registry):
    """新增或更新一条关系（父表 -> 子表）。"""
    parent_name = spec.get("parent") or spec.get("parent_table")
    child_name = spec.get("child") or spec.get("child_table")
    parent_column_name = spec.get("parent_column") or "id"
    child_column_name = spec.get("child_column")
    if not parent_name or not child_name:
        raise ErmError("关系规格必须包含 parent 与 child")

    parent_table = registry.tables.get(parent_name)
    child_table = registry.tables.get(child_name)
    if parent_table is None:
        raise ErmError("关系中引用了不存在的父表: " + parent_name)
    if child_table is None:
        raise ErmError("关系中引用了不存在的子表: " + child_name)

    parent_column = registry.find_column(parent_table, parent_column_name,
                                         include_foreign_key=False)
    if parent_column is None:
        raise ErmError("父表 {} 中不存在列 {}".format(parent_name, parent_column_name))
    # 未指定外键列名时默认与父列同名（ERMaster 的继承方式）
    if not child_column_name:
        child_column_name = parent_column_name

    parent_column_id = text_of(parent_column, "id")
    parent_table_id = text_of(parent_table, "id")
    child_table_id = text_of(child_table, "id")

    child_column = find_relation_column(child_table, child_column_name, registry)
    relation_id = None
    if child_column is not None:
        relation_id = text_of(child_column, "relation")

    connections = ensure_empty_child(child_table, "connections")
    relation = None
    if relation_id:
        for rel in connections.findall("relation"):
            if text_of(rel, "id") == relation_id:
                relation = rel
                break

    if relation is None:
        relation_id = make_relation_id(child_table_id, child_column_name,
                                       parent_table_id, parent_column_name)
        if child_column is None:
            child_column = create_foreign_key_column(
                child_table, child_name, parent_column, parent_column_name,
                relation_id, child_column_name)
        else:
            # 已有同名普通列：改写为外键列（保留列 id）
            set_scalar(child_column, "referenced_column", parent_column_id)
            set_scalar(child_column, "relation", relation_id)
            set_scalar(child_column, "foreign_key", "true")
            word_el = child_column.find("word_id")
            if word_el is not None:
                child_column.remove(word_el)
            set_scalar(child_column, "physical_name",
                       "" if child_column_name == registry.column_name(parent_column)
                       else child_column_name)
            set_scalar(child_column, "logical_name", "")
            set_scalar(child_column, "type", text_of(parent_column, "type"))
            reorder_children(child_column, COLUMN_TAGS)
        relation = build_relation_element(
            relation_id=relation_id, parent_id=parent_table_id, child_id=child_table_id,
            referenced_column_id=parent_column_id,
            child_cardinality=spec.get("child_cardinality", "1..n"),
            parent_cardinality=spec.get("parent_cardinality", "1"),
            name=spec.get("name", "") or "",
            on_delete=spec.get("on_delete", "RESTRICT"),
            on_update=spec.get("on_update", "RESTRICT"),
            reference_for_pk=bool(spec.get("reference_for_pk", False)))
        connections.append(relation)
    else:
        set_scalar(relation, "child_cardinality", spec.get("child_cardinality",
                                                           text_of(relation, "child_cardinality")))
        set_scalar(relation, "parent_cardinality", spec.get("parent_cardinality",
                                                            text_of(relation, "parent_cardinality")))
        set_scalar(relation, "name", spec.get("name", text_of(relation, "name")))
        set_scalar(relation, "on_delete_action", spec.get("on_delete",
                                                          text_of(relation, "on_delete_action")))
        set_scalar(relation, "on_update_action", spec.get("on_update",
                                                          text_of(relation, "on_update_action")))
        set_scalar(relation, "reference_for_pk",
                   bool_text(bool(spec.get("reference_for_pk",
                                           bool_of(relation, "reference_for_pk")))))
        reorder_children(relation, RELATION_TAGS)
    return relation


def drop_relation(root, child_name, child_column_name, registry):
    """删除关系及其外键列（与 ERMaster 删除关系的行为一致）。"""
    child_table = registry.tables.get(child_name)
    if child_table is None:
        raise ErmError("子表不存在: " + child_name)
    child_column = find_relation_column(child_table, child_column_name, registry)
    if child_column is None:
        raise ErmError("子表 {} 中不存在外键列 {}".format(child_name, child_column_name))
    relation_id = text_of(child_column, "relation")
    connections = child_table.find("connections")
    if connections is not None and relation_id:
        for rel in connections.findall("relation"):
            if text_of(rel, "id") == relation_id:
                connections.remove(rel)
    columns = child_table.find("columns")
    if columns is not None:
        columns.remove(child_column)


def upsert_note(root, spec, index=0):
    """新增或更新备注节点（按 text 匹配）。"""
    contents = root.find("contents")
    text = spec.get("text", "") or ""
    if contents is None:
        contents = ET.SubElement(root, "contents")
    note = None
    for candidate in contents.findall("note"):
        if text_of(candidate, "text") == text:
            note = candidate
            break
    if note is None:
        note = ET.SubElement(contents, "note")
    x = int(spec.get("x", 100))
    y = int(spec.get("y", 100))
    width = int(spec.get("width", 200))
    height = int(spec.get("height", 80))
    build_node_fields(note, text_of(note, "id") or make_node_id(text), x, y, height, width)
    set_scalar(note, "text", text)
    reorder_children(note, NOTE_TAGS)
    return note


def upsert_view(root, spec, registry):
    """新增或更新视图。"""
    contents = root.find("contents")
    name = (spec.get("name") or "").strip()
    if not name:
        raise ErmError("视图规格缺少 name")
    if contents is None:
        contents = ET.SubElement(contents, "contents")
    view = None
    for candidate in contents.findall("view"):
        if text_of(candidate, "physical_name") == name:
            view = candidate
            break
    if view is None:
        view = ET.SubElement(contents, "view")

    x, y = parse_position(spec, 100, 100)
    width, height = estimate_table_size(spec.get("columns") or [])
    build_node_fields(view, text_of(view, "id") or make_node_id(name), x, y,
                      int(spec.get("height", height)), int(spec.get("width", width)))
    set_scalar(view, "physical_name", name)
    set_scalar(view, "logical_name", spec.get("logical_name", "") or "")
    set_scalar(view, "description", spec.get("description", "") or "")
    set_scalar(view, "sql", spec.get("sql", "") or "")
    ensure_empty_child(view, "columns")
    view_properties = ensure_empty_child(view, "view_properties")
    set_scalar(view_properties, "schema", spec.get("schema", "") or "")
    reorder_children(view, VIEW_TAGS)

    for column_spec in spec.get("columns") or []:
        upsert_view_column(view, name, column_spec, registry)
    return view


def upsert_view_column(view, view_name, spec, registry):
    """写入视图列（视图列同样通过字典词条记录类型长度）。"""
    columns = ensure_empty_child(view, "columns")
    name = (spec.get("name") or "").strip()
    if not name:
        raise ErmError("视图 {} 中存在缺少 name 的列".format(view_name))
    column = registry.find_column(view, name)
    if column is None:
        column = ET.SubElement(columns, "normal_column")

    type_id, length, decimal = resolve_type(
        spec.get("type"), spec.get("length", spec.get("size")), spec.get("decimal"))
    logical = spec.get("logical_name", spec.get("comment", "")) or ""
    description = spec.get("description", spec.get("comment", "")) or ""
    word_id = registry.ensure_word(name, logical, type_id, length, decimal, description)
    column_id = text_of(column, "id") or make_column_id("VIEW_" + view_name, name)
    fresh = build_normal_column(column_id=column_id, physical=name, logical=logical,
                                type_id=type_id, word_id=word_id, description=description,
                                not_null=bool(spec.get("not_null", False)))
    if registry.find_parent(column) is not None:
        registry.replace(column, fresh)
    else:
        columns.append(fresh)
    registry.columns[column_id] = fresh


def upsert_sequence(root, spec):
    """新增或更新序列（sequence_set）。"""
    name = spec.get("name") or ""
    if not name:
        raise ErmError("序列规格缺少 name")
    sequence_set = root.find("sequence_set")
    if sequence_set is None:
        sequence_set = ET.SubElement(root, "sequence_set")
    sequence = None
    for candidate in sequence_set.findall("sequence"):
        if text_of(candidate, "name") == name:
            sequence = candidate
            break
    if sequence is None:
        sequence = ET.SubElement(sequence_set, "sequence")
    for tag, default in (
        ("schema", ""), ("increment", ""), ("min_value", ""), ("max_value", ""),
        ("start", ""), ("cache", ""), ("description", ""), ("data_type", ""),
    ):
        set_scalar(sequence, tag, num_text(spec.get(tag, default)))
    set_scalar(sequence, "nocache", bool_text(bool(spec.get("nocache", False))))
    set_scalar(sequence, "cycle", bool_text(bool(spec.get("cycle", False))))
    set_scalar(sequence, "order", bool_text(bool(spec.get("order", False))))
    set_scalar(sequence, "decimal_size", num_text(spec.get("decimal_size", 0)) or "0")
    set_scalar(sequence, "name", name)
    reorder_children(sequence, SEQUENCE_TAGS)
    return sequence


def upsert_trigger(root, spec):
    """新增或更新触发器（trigger_set）。"""
    name = spec.get("name") or ""
    if not name:
        raise ErmError("触发器规格缺少 name")
    trigger_set = root.find("trigger_set")
    if trigger_set is None:
        trigger_set = ET.SubElement(root, "trigger_set")
    trigger = None
    for candidate in trigger_set.findall("trigger"):
        if text_of(candidate, "name") == name:
            trigger = candidate
            break
    if trigger is None:
        trigger = ET.SubElement(trigger_set, "trigger")
    set_scalar(trigger, "name", name)
    set_scalar(trigger, "schema", spec.get("schema", "") or "")
    set_scalar(trigger, "sql", spec.get("sql", "") or "")
    set_scalar(trigger, "description", spec.get("description", "") or "")
    reorder_children(trigger, ["name", "schema", "sql", "description"])
    return trigger


def auto_layout(tables, start_x=100, start_y=100, per_row=4, gap_x=80, gap_y=80):
    """为未指定坐标的表按网格自动排布。"""
    row_height = 0
    x, y = start_x, start_y
    count = 0
    for table in tables:
        width = int_of(table, "width", DEFAULT_TABLE_WIDTH)
        height = int_of(table, "height", DEFAULT_TABLE_HEIGHT)
        if count and count % per_row == 0:
            x = start_x
            y += row_height + gap_y
            row_height = 0
        set_scalar(table, "x", x)
        set_scalar(table, "y", y)
        x += width + gap_x
        row_height = max(row_height, height)
        count += 1


def drop_table(root, table_name, registry):
    """删除表，同时清理其他表指向它的关系、分类引用与外键列。"""
    contents = root.find("contents")
    table = registry.tables.get(table_name)
    if table is None:
        raise ErmError("表不存在: " + table_name)
    table_id = text_of(table, "id")
    removed_column_ids = set()
    for col in table.iter("normal_column"):
        cid = text_of(col, "id")
        if cid:
            removed_column_ids.add(cid)

    for other in contents.findall("table"):
        if other is table:
            continue
        connections = other.find("connections")
        if connections is not None:
            for rel in list(connections.findall("relation")):
                if text_of(rel, "source") == table_id or text_of(rel, "target") == table_id:
                    connections.remove(rel)
        columns = other.find("columns")
        if columns is None:
            continue
        for col in list(columns.findall("normal_column")):
            ref = text_of(col, "referenced_column")
            if ref and ref in removed_column_ids:
                columns.remove(col)

    categories = root.find("settings/category_settings/categories")
    if categories is not None:
        for category in categories.findall("category"):
            for node in list(category.findall("node_element")):
                if node.text == table_id:
                    category.remove(node)

    contents.remove(table)
    registry.tables.pop(table_name, None)


# ---------------------------------------------------------------------------
# 备份与恢复
# ---------------------------------------------------------------------------

def backup_root():
    """备份根目录，可用环境变量 ERM_BACKUP_DIR 覆盖。"""
    custom = os.environ.get("ERM_BACKUP_DIR")
    if custom:
        return custom
    cache_home = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(cache_home, "jeesite-erm-backups")


def file_sha1(path):
    """计算文件 SHA1，用于恢复前校验备份是否完整。"""
    digest = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_backup(path, command, note=""):
    """
    在临时缓存中为文件生成一份备份。

    每次执行生成一个独立的运行目录：
        <备份根目录>/<run_id>/<原文件名>
        <备份根目录>/<run_id>/manifest.json

    :param path: 被修改（或即将被覆盖）的文件路径
    :param command: 产生备份的命令（create / apply / restore）
    :param note: 附加说明
    :return: 备份信息字典；文件不存在时返回 None
    """
    abs_path = os.path.abspath(path)
    if not os.path.isfile(abs_path):
        return None

    run_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-") + os.urandom(2).hex()
    run_dir = os.path.join(backup_root(), run_id)
    os.makedirs(run_dir, exist_ok=True)
    backup_path = os.path.join(run_dir, os.path.basename(abs_path))
    shutil.copy2(abs_path, backup_path)

    manifest = {
        "run_id": run_id,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "command": command,
        "target": abs_path,
        "backup_file": backup_path,
        "sha1": file_sha1(backup_path),
        "size": os.path.getsize(backup_path),
        "note": note or "",
    }
    with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    prune_backups()
    return manifest


def list_backup_runs(target=None):
    """列出备份运行记录（按时间倒序），可按目标文件过滤。"""
    root = backup_root()
    if not os.path.isdir(root):
        return []
    runs = []
    for name in sorted(os.listdir(root), reverse=True):
        manifest_path = os.path.join(root, name, "manifest.json")
        if not os.path.isfile(manifest_path):
            continue
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if target and os.path.abspath(target) != manifest.get("target"):
            continue
        manifest["exists"] = os.path.isfile(manifest.get("backup_file", ""))
        runs.append(manifest)
    return runs


def restore_backup(run_id, out_path=None):
    """
    恢复指定备份；恢复前会先为当前文件再留一份备份（可反悔）。

    :param run_id: create_backup 返回的 run_id
    :param out_path: 可选，恢复到别处；默认写回原文件
    :return: 恢复结果字典
    """
    manifest_path = os.path.join(backup_root(), run_id, "manifest.json")
    if not os.path.isfile(manifest_path):
        raise ErmError("备份记录不存在: {}".format(run_id))
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    backup_path = manifest.get("backup_file", "")
    if not os.path.isfile(backup_path):
        raise ErmError("备份文件已丢失: " + str(backup_path))
    if manifest.get("sha1") and file_sha1(backup_path) != manifest["sha1"]:
        raise ErmError("备份文件校验失败（SHA1 不一致）: " + backup_path)

    target = os.path.abspath(out_path or manifest["target"])
    safety = None
    if os.path.isfile(target) and target == os.path.abspath(manifest["target"]):
        # 回滚同样是一次修改，先保存当前状态，避免恢复错了无法再回退
        safety = create_backup(target, "restore", "恢复 {} 前的现场".format(run_id))

    directory = os.path.dirname(target)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    shutil.copy2(backup_path, target)
    return {
        "ok": True,
        "restored_from": run_id,
        "target": target,
        "backup_sha1": manifest.get("sha1"),
        "safety_backup_run": safety["run_id"] if safety else None,
    }


def prune_backups(max_runs=200):
    """只保留最近的若干次备份，避免缓存无限增长。"""
    root = backup_root()
    if not os.path.isdir(root):
        return
    names = sorted([n for n in os.listdir(root)
                    if os.path.isfile(os.path.join(root, n, "manifest.json"))], reverse=True)
    for name in names[max_runs:]:
        shutil.rmtree(os.path.join(root, name), ignore_errors=True)


# ---------------------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------------------

def read_spec(path):
    """读取 JSON 规格文件（支持 - 表示标准输入）。"""
    if path == "-":
        try:
            return json.load(sys.stdin)
        except json.JSONDecodeError as e:
            raise ErmError("JSON 解析失败: {}".format(e))
    if not os.path.isfile(path):
        raise ErmError("规格文件不存在: " + path)
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise ErmError("JSON 解析失败: {} ({})".format(path, e))


def cmd_create(args):
    """create 子命令：按规格生成新的 ERM 文件。"""
    spec = read_spec(args.spec)
    database = spec.get("database") or args.database or "StandardSQL"
    if database not in ERM_DATABASES:
        raise ErmError("不支持的数据库: {}，可选值: {}".format(database, ", ".join(ERM_DATABASES)))

    root = build_empty_diagram(database, spec.get("environment", "Default"))
    registry = IdRegistry(root)

    tables = []
    for table_spec in spec.get("tables") or []:
        table = upsert_table(root, table_spec, registry,
                             default_x=0, default_y=0)
        tables.append(table)

    # 未显式指定坐标时自动排布
    explicit = any(("position" in t or "x" in t) for t in (spec.get("tables") or []))
    if tables and not explicit:
        auto_layout(tables)
        for table in tables:
            reorder_children(table, TABLE_TAGS)

    for relation_spec in spec.get("relations") or []:
        upsert_relation(root, relation_spec, registry)
    for view_spec in spec.get("views") or []:
        upsert_view(root, view_spec, registry)
    for note_spec in spec.get("notes") or []:
        upsert_note(root, note_spec)
    for sequence_spec in spec.get("sequences") or []:
        upsert_sequence(root, sequence_spec)
    for trigger_spec in spec.get("triggers") or []:
        upsert_trigger(root, trigger_spec)

    errors, _warnings = validate_root(root)
    if errors:
        raise ErmError("生成的 ERM 未通过自检:\n  - " + "\n  - ".join(errors))

    normalize_table_properties(root)

    # 覆盖已有文件前先备份，便于回退
    backup = None if args.no_backup else create_backup(args.out, "create", "生成前备份")
    write_erm(root, args.out)
    result = {
        "ok": True,
        "file": os.path.abspath(args.out),
        "database": database,
        "tables": len(root.findall("contents/table")),
        "views": len(root.findall("contents/view")),
        "notes": len(root.findall("contents/note")),
        "relations": count_relations(root),
        "words": len(root.findall("dictionary/word")),
        "backup_run": backup["run_id"] if backup else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_apply(args):
    """apply 子命令：在保留原有内容的前提下增量修改 ERM 文件。"""
    root = load_erm(args.file)
    registry = IdRegistry(root)
    spec = read_spec(args.spec)

    if spec.get("database"):
        database = spec["database"]
        if database not in ERM_DATABASES:
            raise ErmError("不支持的数据库: " + database)
        settings = root.find("settings")
        if settings is None:
            settings = ET.SubElement(root, "settings")
        set_scalar(settings, "database", database)

    for table_spec in spec.get("tables") or []:
        upsert_table(root, table_spec, registry)

    for relation_spec in spec.get("relations") or []:
        upsert_relation(root, relation_spec, registry)

    for item in spec.get("drop_relations") or []:
        drop_relation(root, item.get("child"), item.get("child_column"), registry)

    for table_name in spec.get("drop_tables") or []:
        drop_table(root, table_name, registry)

    for view_spec in spec.get("views") or []:
        upsert_view(root, view_spec, registry)
    for note_spec in spec.get("notes") or []:
        upsert_note(root, note_spec)
    for sequence_spec in spec.get("sequences") or []:
        upsert_sequence(root, sequence_spec)
    for trigger_spec in spec.get("triggers") or []:
        upsert_trigger(root, trigger_spec)

    # 新增列后统一补齐规范顺序
    for table in root.findall("contents/table"):
        reorder_children(table, TABLE_TAGS)
    for view in root.findall("contents/view"):
        reorder_children(view, VIEW_TAGS)
    for note in root.findall("contents/note"):
        reorder_children(note, NOTE_TAGS)
    for word in root.findall("dictionary/word"):
        reorder_children(word, WORD_TAGS)

    pruned = prune_unused_words(root)
    normalize_table_properties(root)

    errors, _warnings = validate_root(root)
    if errors:
        raise ErmError("修改后的 ERM 未通过自检:\n  - " + "\n  - ".join(errors))

    out_path = args.out or args.file
    backup = None
    if not args.dry_run:
        if not args.no_backup:
            backup = create_backup(args.file, "apply", "修改前备份")
            if os.path.abspath(out_path) != os.path.abspath(args.file):
                create_backup(out_path, "apply", "输出文件覆盖前备份")
        write_erm(root, out_path)

    result = {
        "ok": True,
        "file": os.path.abspath(out_path),
        "dry_run": bool(args.dry_run),
        "tables": len(root.findall("contents/table")),
        "views": len(root.findall("contents/view")),
        "notes": len(root.findall("contents/note")),
        "relations": count_relations(root),
        "words": len(root.findall("dictionary/word")),
        "pruned_words": pruned,
        "backup_run": backup["run_id"] if backup else None,
        "backup_file": backup["backup_file"] if backup else None,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def count_relations(root):
    """统计文件中的关系数量。"""
    total = 0
    for table in root.findall("contents/table"):
        connections = table.find("connections")
        if connections is not None:
            total += len(connections.findall("relation"))
    return total


def prune_unused_words(root):
    """
    清理没有列引用的字典词条。

    ERMaster 保存时只为“被列引用的词条”重建 dictionary，
    这里保持相同行为，避免反复修改后字典不断膨胀。
    返回被清理的词条数量。
    """
    dictionary = root.find("dictionary")
    if dictionary is None:
        return 0
    used = set()
    for el in root.iter("word_id"):
        value = (el.text or "").strip()
        if value:
            used.add(value)
    removed = 0
    for word in list(dictionary.findall("word")):
        if text_of(word, "id") not in used:
            dictionary.remove(word)
            removed += 1
    return removed


def format_type(type_id, length, decimal):
    """把类型 id + 长度/精度还原为可读类型，例如 varchar(64)、decimal(10,2)。"""
    if not type_id:
        return ""
    if length in (None, "", "null"):
        return type_id
    if "(p,s)" in type_id:
        return type_id.replace("(p,s)", "({},{})".format(
            length, decimal if decimal not in (None, "", "null") else 0))
    if "(p)" in type_id:
        return type_id.replace("(p)", "({})".format(length))
    if "(n)" in type_id:
        return type_id.replace("(n)", "({})".format(length))
    return type_id


def cmd_info(args):
    """info 子命令：输出 ERM 的结构化 JSON 摘要。"""
    root = load_erm(args.file)
    settings = root.find("settings")
    registry = IdRegistry(root)
    dictionary = registry.words

    def column_json(col):
        source = registry.resolve_column(col)
        word_id = text_of(source, "word_id")
        word = dictionary.get(word_id)
        if word is not None:
            type_id = text_of(word, "type")
            length = text_of(word, "length")
            decimal = text_of(word, "decimal")
        else:
            type_id = text_of(source, "type")
            length = ""
            decimal = ""
        return {
            "name": registry.column_field(col, "physical_name"),
            "logical_name": registry.column_field(col, "logical_name"),
            "type": format_type(type_id, length, decimal),
            "type_id": type_id,
            "length": None if length in ("", "null") else int(length),
            "decimal": None if decimal in ("", "null") else int(decimal),
            "primary_key": bool_of(col, "primary_key"),
            "not_null": bool_of(col, "not_null"),
            "unique_key": bool_of(col, "unique_key"),
            "auto_increment": bool_of(col, "auto_increment"),
            "default_value": text_of(col, "default_value"),
            "comment": registry.column_field(col, "description"),
            "foreign_key": bool_of(col, "foreign_key"),
            "referenced_column_id": text_of(col, "referenced_column") or None,
        }

    tables_json = []
    relations_json = []
    node_names = {}
    column_names = {}
    for table in root.findall("contents/table"):
        node_names[text_of(table, "id")] = text_of(table, "physical_name")
    for cid, col in registry.columns.items():
        column_names[cid] = registry.column_name(col)

    group_names = {}
    for group in root.findall("column_groups/column_group"):
        group_names[text_of(group, "id")] = text_of(group, "group_name")

    def column_id_to_name(column_id):
        return column_names.get(column_id, column_id)

    for table in root.findall("contents/table"):
        columns_el = table.find("columns")
        columns = []
        if columns_el is not None:
            for col in columns_el.findall("normal_column"):
                columns.append(column_json(col))
        indexes = []
        indexes_el = table.find("indexes")
        if indexes_el is not None:
            for index in indexes_el:
                col_ids = [text_of(c, "id") for c in index.findall("columns/column")]
                indexes.append({
                    "name": text_of(index, "name"),
                    "unique": not bool_of(index, "non_unique", True),
                    "full_text": bool_of(index, "full_text"),
                    "type": text_of(index, "type"),
                    "description": text_of(index, "description"),
                    "columns": [column_id_to_name(i) for i in col_ids],
                })
        unique_keys = []
        keys_el = table.find("complex_unique_key_list")
        if keys_el is not None:
            for key in keys_el.findall("complex_unique_key"):
                col_ids = [text_of(c, "id") for c in key.findall("columns/column")]
                unique_keys.append({
                    "name": text_of(key, "name"),
                    "columns": [column_id_to_name(i) for i in col_ids],
                })
        props = table.find("table_properties")
        groups = []
        if columns_el is not None:
            for child in columns_el.findall("column_group"):
                gid = (child.text or "").strip()
                if gid:
                    groups.append(group_names.get(gid, gid))
        tables_json.append({
            "name": text_of(table, "physical_name"),
            "logical_name": text_of(table, "logical_name"),
            "description": text_of(table, "description"),
            "primary_key_name": text_of(table, "primary_key_name"),
            "schema": text_of(props, "schema") if props is not None else "",
            "column_groups": groups,
            "position": {"x": int_of(table, "x"), "y": int_of(table, "y")},
            "size": {"width": int_of(table, "width"), "height": int_of(table, "height")},
            "columns": columns,
            "indexes": indexes,
            "unique_keys": unique_keys,
        })
        connections = table.find("connections")
        if connections is not None:
            for rel in connections.findall("relation"):
                ref_col = registry.columns.get(text_of(rel, "referenced_column"))
                relations_json.append({
                    "parent": node_names.get(text_of(rel, "source"), text_of(rel, "source")),
                    "child": text_of(table, "physical_name"),
                    "parent_column": registry.column_name(ref_col) if ref_col is not None else "",
                    "child_cardinality": text_of(rel, "child_cardinality"),
                    "parent_cardinality": text_of(rel, "parent_cardinality"),
                    "on_delete": text_of(rel, "on_delete_action"),
                    "on_update": text_of(rel, "on_update_action"),
                    "name": text_of(rel, "name"),
                    "reference_for_pk": bool_of(rel, "reference_for_pk"),
                })

    views = []
    for view in root.findall("contents/view"):
        views.append({
            "name": text_of(view, "physical_name"),
            "logical_name": text_of(view, "logical_name"),
            "description": text_of(view, "description"),
            "sql": text_of(view, "sql"),
            "columns": [column_json(c) for c in view.findall("columns/normal_column")],
        })

    notes = [{"text": text_of(n, "text"),
              "position": {"x": int_of(n, "x"), "y": int_of(n, "y")}}
             for n in root.findall("contents/note")]

    result = {
        "file": os.path.abspath(args.file),
        "database": text_of(settings, "database") if settings is not None else "",
        "counts": {
            "tables": len(tables_json),
            "views": len(views),
            "notes": len(notes),
            "relations": len(relations_json),
            "words": len(dictionary),
            "sequences": len(root.findall("sequence_set/sequence")),
            "triggers": len(root.findall("trigger_set/trigger")),
            "column_groups": len(root.findall("column_groups/column_group")),
            "categories": len(root.findall("settings/category_settings/categories/category")),
        },
        "tables": tables_json,
        "relations": relations_json,
        "views": views,
        "notes": notes,
        "sequences": [{"name": text_of(s, "name")} for s in root.findall("sequence_set/sequence")],
        "triggers": [{"name": text_of(t, "name")} for t in root.findall("trigger_set/trigger")],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

def validate_root(root):
    """
    校验 ERM 结构，返回 (errors, warnings)。

    覆盖：
        1. 根节点与必需容器；
        2. 各类 id 的唯一性；
        3. 引用完整性（word_id / referenced_column / relation / column_group /
           node_element / tablespace_id / environment_id）；
        4. 类型 id 是否合法。
    """
    errors = []
    warnings = []

    if root.tag != "diagram":
        return ["根节点必须是 <diagram>"], warnings

    settings = root.find("settings")
    if settings is None:
        errors.append("缺少 <settings>")
        settings = ET.Element("settings")

    # 加载器无空判的必需节点
    for parent, path in (
        (root, "dictionary"), (root, "tablespace_set"), (root, "contents"),
        (root, "column_groups"),
        (settings, "category_settings"), (settings, "category_settings/categories"),
        (settings, "translation_settings"), (settings, "translation_settings/translations"),
        (settings, "model_properties"), (settings, "table_properties"),
    ):
        if parent.find(path) is None:
            errors.append("缺少必需节点 <{}>".format(path))

    if not text_of(settings, "database"):
        warnings.append("<settings><database> 为空，ERMaster 会回退为默认数据库")

    # id 唯一性
    def check_unique(elements, label, path_desc):
        seen = {}
        for el in elements:
            eid = text_of(el, "id")
            if not eid:
                errors.append("{}（{}）缺少 id".format(label, path_desc))
                continue
            if eid in seen:
                errors.append("{} id 重复: {}（{}）".format(label, eid, path_desc))
            seen[eid] = el
        return seen

    word_ids = check_unique(root.findall("dictionary/word"), "字典词条", "dictionary/word")

    table_ids = {}
    column_ids = {}
    connection_ids = {}
    complex_key_ids = {}
    for table in root.findall("contents/table"):
        table_name = text_of(table, "physical_name")
        if not table_name:
            errors.append("存在未设置 physical_name 的表")
        tid = text_of(table, "id")
        if not tid:
            errors.append("表 {} 缺少 id".format(table_name))
        elif tid in table_ids:
            errors.append("表 id 重复: {}".format(tid))
        table_ids[tid] = table
        for col in table.iter("normal_column"):
            cid = text_of(col, "id")
            if not cid:
                errors.append("表 {} 存在缺少 id 的列".format(table_name))
                continue
            if cid in column_ids:
                errors.append("列 id 重复: {}（表 {}）".format(cid, table_name))
            column_ids[cid] = col
        connections = table.find("connections")
        if connections is not None:
            for rel in connections.findall("relation"):
                rid = text_of(rel, "id")
                if not rid:
                    errors.append("表 {} 存在缺少 id 的关系".format(table_name))
                elif rid in connection_ids:
                    errors.append("关系 id 重复: {}".format(rid))
                connection_ids[rid] = rel
        keys = table.find("complex_unique_key_list")
        if keys is not None:
            for key in keys.findall("complex_unique_key"):
                kid = text_of(key, "id")
                if not kid:
                    errors.append("表 {} 存在缺少 id 的唯一键".format(table_name))
                elif kid in complex_key_ids:
                    errors.append("唯一键 id 重复: {}".format(kid))
                complex_key_ids[kid] = key

    for view in root.findall("contents/view"):
        vid = text_of(view, "id")
        if not vid:
            errors.append("视图 {} 缺少 id".format(text_of(view, "physical_name")))
        for col in view.iter("normal_column"):
            cid = text_of(col, "id")
            if cid:
                column_ids.setdefault(cid, col)

    group_ids = {}
    for group in root.findall("column_groups/column_group"):
        gid = text_of(group, "id")
        if not gid:
            errors.append("列组 {} 缺少 id".format(text_of(group, "group_name")))
        else:
            group_ids[gid] = group

    # 引用完整性
    for table in root.findall("contents/table"):
        table_name = text_of(table, "physical_name")
        columns = table.find("columns")
        if columns is None:
            errors.append("表 {} 缺少 <columns>".format(table_name))
        else:
            for child in list(columns):
                if child.tag == "column_group":
                    ref = (child.text or "").strip()
                    if ref and ref not in group_ids:
                        errors.append("表 {} 引用了不存在的列组 {}".format(table_name, ref))
        if table.find("indexes") is None:
            errors.append("表 {} 缺少 <indexes>".format(table_name))
        if table.find("table_properties") is None:
            errors.append("表 {} 缺少 <table_properties>".format(table_name))
        for col in table.iter("normal_column"):
            word_id = text_of(col, "word_id")
            if word_id and word_id not in word_ids:
                errors.append("表 {} 的列 {} 引用了不存在的字典词条 {}".format(
                    table_name, text_of(col, "physical_name") or "(外键列)", word_id))
            ref = text_of(col, "referenced_column")
            if ref and ref not in column_ids:
                errors.append("表 {} 的列 {} 引用了不存在的列 {}".format(
                    table_name, text_of(col, "physical_name") or "(外键列)", ref))
            rel = text_of(col, "relation")
            if rel and rel not in connection_ids:
                errors.append("表 {} 的列 {} 引用了不存在的关系 {}".format(
                    table_name, text_of(col, "physical_name") or "(外键列)", rel))
            type_id = text_of(col, "type")
            if type_id and type_id not in ERM_TYPE_ID_SET:
                warnings.append("表 {} 的列 {} 使用了非标准类型 {}".format(
                    table_name, text_of(col, "physical_name") or "(外键列)", type_id))

        connections = table.find("connections")
        if connections is not None:
            for rel in connections.findall("relation"):
                rid = text_of(rel, "id")
                source = text_of(rel, "source")
                target = text_of(rel, "target")
                if source not in table_ids:
                    errors.append("关系 {} 的 source 指向不存在的节点 {}".format(rid, source))
                if target not in table_ids:
                    errors.append("关系 {} 的 target 指向不存在的节点 {}".format(rid, target))
                ref = text_of(rel, "referenced_column")
                if ref and ref != "null" and ref not in column_ids:
                    errors.append("关系 {} 的 referenced_column 指向不存在的列 {}".format(rid, ref))

    for word in root.findall("dictionary/word"):
        type_id = text_of(word, "type")
        if type_id and type_id not in ERM_TYPE_ID_SET:
            warnings.append("字典词条 {} 使用了非标准类型 {}".format(text_of(word, "id"), type_id))

    # 环境与表空间引用
    environment_ids = {text_of(e, "id") for e in root.findall("settings/environment_setting/environment")}
    ddl = settings.find("export_setting/export_ddl_setting")
    if ddl is not None:
        env_id = text_of(ddl, "environment_id")
        if env_id and env_id != "null" and env_id not in environment_ids:
            warnings.append("导出设置引用了不存在的环境 {}".format(env_id))

    tablespace_ids = {text_of(t, "id") for t in root.findall("tablespace_set/tablespace")}
    for props in list(root.iter("table_properties")) + list(root.iter("view_properties")):
        ts = text_of(props, "tablespace_id")
        if ts and ts not in tablespace_ids:
            errors.append("table_properties 引用了不存在的表空间 {}".format(ts))

    # 分类引用
    for category in root.findall("settings/category_settings/categories/category"):
        for node in category.findall("node_element"):
            ref = (node.text or "").strip()
            if ref and ref not in table_ids:
                errors.append("分类 {} 引用了不存在的节点 {}".format(text_of(category, "name"), ref))

    return errors, warnings


def cmd_validate(args):
    """validate 子命令：结构校验。"""
    try:
        root = load_erm(args.file)
    except ErmError as e:
        result = {"ok": False, "file": os.path.abspath(args.file), "errors": [str(e)], "warnings": []}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    errors, warnings = validate_root(root)
    result = {
        "ok": not errors,
        "file": os.path.abspath(args.file),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def cmd_backups(args):
    """backups 子命令：列出临时缓存中的备份记录。"""
    runs = list_backup_runs(args.file if getattr(args, "file", None) else None)
    result = {
        "ok": True,
        "backup_root": backup_root(),
        "count": len(runs),
        "runs": runs,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_restore(args):
    """
    restore 子命令：把文件恢复到某次备份。

    两种用法：
        --run <run_id>   恢复到指定备份
        --file <path>    恢复该文件最近一次备份
    """
    if args.run:
        run_id = args.run
    else:
        runs = list_backup_runs(args.file)
        if not runs:
            raise ErmError("没有找到 {} 的备份记录".format(os.path.abspath(args.file)))
        run_id = runs[0]["run_id"]
    result = restore_backup(run_id, args.out)
    result["backup_root"] = backup_root()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_schema(_args):
    """schema 子命令：输出 JSON 规格模板，便于 AI 直接照写。

    列如果没写 type，会按 JeeSite 字段名习惯自动推断（见 JEESITE_NAME_TYPE_HINTS）；
    索引/唯一键/主键名没写时会自动按 "idx_<表后缀>_<列缩写>" 模式生成，
    并自动裁到 Oracle 兼容的 30 字符以内，命中关键字时警告。
    """
    template = {
        "database": "StandardSQL",
        "environment": "Default",
        "tables": [{
            "name": "js_demo",
            "logical_name": "示例表",
            "description": "",
            # "primary_key_name" 可省略：自动生成 pk_demo
            "columns": [
                {"name": "id", "logical_name": "编号", "pk": True, "nn": True, "comment": "主键"},
                {"name": "status", "logical_name": "状态", "default_value": "0"},
                {"name": "create_date", "logical_name": "创建时间"},
                {"name": "create_by", "logical_name": "创建人"},
                {"name": "update_date", "logical_name": "更新时间"},
                {"name": "update_by", "logical_name": "更新人"},
                {"name": "remarks", "logical_name": "备注"},
            ],
            "indexes": [
                # name 可省略：自动生成 idx_demo_status
                {"columns": ["status"]},
                {"columns": ["create_date"], "unique": False},
                {"columns": ["module_code", "status"], "unique": False},
                # 也可以显式写：
                # {"name": "idx_demo_status", "columns": ["status"]},
            ],
            "unique_keys": [{"columns": ["id"]}],  # 自动生成 uk_demo_id
        }],
        "relations": [{
            "parent": "js_demo", "child": "js_demo_item", "child_column": "demo_id",
            "parent_column": "id",
        }],
        "notes": [{"text": "自动推断规则: id→varchar(64)、*_code→varchar(64)、*_name→nvarchar(100)、*_date→datetime、is_*/has_*→character(1) 等，详见脚本 JEESITE_NAME_TYPE_HINTS。", "x": 100, "y": 100}],
    }
    print(json.dumps(template, ensure_ascii=False, indent=2))
    print("\n# 命名规则: 主键 pk_<表后缀>、索引 idx_<表后缀>_<列缩写>、唯一键 uk_<表后缀>_<列缩写>、外键 fk_<子表后缀>_<父表后缀>")
    print("# 所有标识符自动裁到 30 字符以内（Oracle 兼容），命中 SQL 关键字时警告")
    print("# use_jeesite_convention=True（默认）时，新图会自动初始化 6 个 JeeSite 公共列分组")
    return 0


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def build_parser():
    """构造命令行解析器。"""
    parser = argparse.ArgumentParser(
        description="ERMaster（ERM）文件生成与修改工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  python3 erm_tools.py create --spec spec.json --out db/test.erm\n"
               "  python3 erm_tools.py apply --file db/test.erm --spec patch.json\n"
               "  python3 erm_tools.py info --file db/test.erm\n"
               "  python3 erm_tools.py validate --file db/test.erm\n")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="生成新的 ERM 文件")
    create.add_argument("--spec", required=True, help="JSON 规格文件，- 表示标准输入")
    create.add_argument("--out", required=True, help="输出 ERM 文件路径")
    create.add_argument("--database", help="数据库类型，默认取规格中的 database 或 StandardSQL")
    create.add_argument("--no-backup", action="store_true", help="覆盖已有文件时不生成备份")
    create.set_defaults(func=cmd_create)

    apply_cmd = subparsers.add_parser("apply", help="增量修改已有 ERM 文件")
    apply_cmd.add_argument("--file", required=True, help="待修改的 ERM 文件")
    apply_cmd.add_argument("--spec", required=True, help="JSON 变更规格，- 表示标准输入")
    apply_cmd.add_argument("--out", help="输出路径，默认原地写回")
    apply_cmd.add_argument("--dry-run", action="store_true", help="只校验不写文件")
    apply_cmd.add_argument("--no-backup", action="store_true", help="不生成临时缓存备份")
    apply_cmd.set_defaults(func=cmd_apply)

    info = subparsers.add_parser("info", help="输出 ERM 结构化摘要（JSON）")
    info.add_argument("--file", required=True, help="ERM 文件路径")
    info.set_defaults(func=cmd_info)

    validate = subparsers.add_parser("validate", help="校验 ERM 结构与引用完整性")
    validate.add_argument("--file", required=True, help="ERM 文件路径")
    validate.set_defaults(func=cmd_validate)

    backups = subparsers.add_parser("backups", help="列出临时缓存中的备份记录")
    backups.add_argument("--file", help="只看某个文件的备份")
    backups.set_defaults(func=cmd_backups)

    restore = subparsers.add_parser("restore", help="从备份恢复 ERM 文件")
    restore.add_argument("--run", help="备份运行 id（backups 命令可查）")
    restore.add_argument("--file", help="恢复到该文件最近一次备份")
    restore.add_argument("--out", help="恢复到其他路径（默认写回原文件）")
    restore.set_defaults(func=cmd_restore)

    schema = subparsers.add_parser("schema", help="输出 JSON 规格模板")
    schema.set_defaults(func=cmd_schema)

    return parser


def main():
    """命令行入口。"""
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except ErmError as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False, indent=2),
              file=sys.stderr)
        return 2
    except OSError as e:
        print(json.dumps({"ok": False, "error": "文件操作失败: {}".format(e)},
                         ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
