---
name: "erm-tools"
description: "生成、修改、校验 ERMaster .erm 文件（ER 图 / 数据库表结构设计图）的命令行工具用法。Invoke when user asks to create, edit, validate, or restore ERMaster .erm diagram files."
---

# ERM 文件工具（erm_tools.py）用法说明

用于生成、修改、校验 ERMaster（`.erm`）文件的命令行工具。输出严格遵循 ERMaster 自身的 XML 写法，
生成的文件可直接用 ERMaster 打开，也可被 ERMaster 再次保存。

文件位置（均在 jeesite skill 内）：

- 脚本：`scripts/erm_tools.py`（相对于 jeesite skill 根目录）
- 本文档：`references/erm-tools/SKILL.md`

下文命令都假定当前目录为 jeesite skill 根目录（即 `scripts/`、`references/` 的上一级）。

## 1. 触发条件（何时使用本工具）

满足以下任一情况，就用本工具处理，**不要**凭记忆手写或手工编辑 ERM 的 XML：

**生成**
- 要求生成 `.erm` 文件、ER 图、ERD、实体关系图、数据库表结构设计图
- 要把一份表结构设计（表名、字段、类型、注释）落成可被 ERMaster 打开的文件
- 需要新建一套 JeeSite 模块的 ER 图作为建表依据

**修改（增量）**
- 给已有 `.erm` 加表、加列、改列类型/长度/精度/注释/默认值/非空
- 加索引、复合唯一键、主键名、表说明
- 加外键关系（父子表连线）、改级联动作与基数
- 加/改备注（Note）、视图（View）、序列（Sequence）、触发器（Trigger）
- 删除表、列、关系
- 要求"在现有 ER 图上补几张表"这类增量变更

**查看与校验**
- 给出 `.erm` 文件，要求梳理有哪些表、字段、索引、外键
- 怀疑 ERM 文件损坏、ERMaster 打不开、引用了不存在的列/词条，需要定位
- 改动后需要确认文件仍合法

**回退**
- 上一次 `create`/`apply` 改错了，需要恢复到改动前
- 需要查看某个文件的历史备份

**不适用**：只写 SQL DDL、连接数据库执行 SQL、查询表数据、绘制非 ERMaster 格式的图表。

## 2. 运行环境与依赖

- Python 3.8 及以上（仅用标准库，无需 pip 安装任何依赖）
- 不依赖 ERMaster 运行环境，可独立使用
- 输入输出均为 UTF-8 编码的 `.erm` 文件

```bash
python3 scripts/erm_tools.py --help
```

## 3. JeeSite 约定（内置默认）

`create` 新图时默认启用，风格与 `core.erm` 完全一致：

### 设置风格

| 项目 | 默认值 | 说明 |
| --- | --- | --- |
| 数据库 | `StandardSQL` | JeeSite 全系列 ER 图统一 |
| 表风格 | `funny` | ERMaster 五种风格之一 |
| 记法 | `IE` | IE/Crow's Foot 标记法 |
| 视图模式 | `view_mode=2`、`outline_view_mode=1`、`view_order_by=1` | |
| 字体 | `Arial` / 14pt | |
| 缩放 | `0.8` | |
| 默认颜色 | 表颜色 `rgb(128,128,192)`（淡紫灰） | |
| 表名前缀 | `js_` | JeeSite 所有表的物理名统一以此开头 |

### 字段名 → 类型自动推断

规格里列如果没写 `type`，会按字段名自动填上（完整规则见脚本 `JEESITE_NAME_TYPE_HINTS`）：

| 字段名模式 | 推断类型 | 示例 |
| --- | --- | --- |
| `id` | `varchar(64)` | 主键 |
| `*_code` | `varchar(64)` | `user_code`、`office_code`、`module_code` |
| `*_codes` | `varchar(500)` | 多编码串联 |
| `*_id` | `varchar(64)` | 外键 id |
| `*_by` | `varchar(64)` | `create_by`、`update_by`（操作人编码）|
| `*_date` | `datetime` | `create_date`、`send_date`、`read_date` |
| `status` | `character(1)` | 状态位 |
| `is_*` / `has_*` / `can_*` | `character(1)` | 布尔标志 |
| `*_type` / `*_scope` | `character(1)` 或 `varchar(16)` | 视字段而定 |
| `*_name` / `*_label` | `nvarchar(100)` | 中文名用 nvarchar |
| `*_title` | `varchar(200)` | 短标题 |
| `*_desc` / `*_content` / `*_info` | `clob` | 大文本 |
| `*_sort` / `*_weight` | `decimal(10)` 或 `decimal(4)` | 排序 |
| `description` / `comments` / `remarks` | `nvarchar(500)` | |
| `phone` | `varchar(100)` | |
| `email` | `varchar(300)` | |
| `*_ip` | `varchar(100)` | |
| `*_size` / `file_size` | `decimal(31)` | 大整数 |
| 其他未匹配 | `varchar(255)` | 兜底 |

列还支持简写别名：`pk` = `primary_key`、`nn` = `not_null`。

### 公共列分组

新图自动初始化 6 个分组（完整定义见脚本 `JEESITE_COLUMN_GROUPS`），
每张表可以通过"列组引用"一次挂上去多个公共字段：

| 分组 | 包含字段 | 用途 |
| --- | --- | --- |
| `cg_basic` | id、status | 最小主键 + 状态 |
| `cg_corp` | corp_code、corp_name | 公司维度 |
| `cg_audit_full` | status、create_by、create_date、update_by、update_date、remarks | 完整审计（最常用） |
| `cg_audit_simple` | create_by、create_date、update_by、update_date、remarks | 简化审计（无 status）|
| `cg_extend` | extend_s1-8、extend_i1-4、extend_f1-4、extend_d1-4、extend_json | 21 个预留扩展槽位 |
| `cg_tree` | parent_code、parent_codes、tree_sort、tree_sorts、tree_leaf、tree_level、tree_names | 树形结构 7 字段 |

分组里的列已经预注册进字典词条（长度/类型按上表），
你在 create 规格里可以直接在表的 `column_group_names` 里引用分组名。

### 索引 / 约束命名（全自动生成）

规格里**可以完全不写**索引/唯一键/主键的 `name`，脚本会自动按
**`表后缀_名称`** 模式生成，规格里显式写了 name 也会被校验：

| 类型 | 自动规则 | 示例 |
| --- | --- | --- |
| 主键 (pk) | `pk_<表后缀>` | `pk_demo_item` |
| 普通索引 (idx) | `idx_<表后缀>_<列缩写>` | `idx_sys_job_log_s`（status）、`idx_sys_user_lc`（login_code）|
| 复合索引 | `idx_<表后缀>_<列1>_<列2>` | `idx_demo_item_ic_in`（item_code + item_name）|
| 唯一键 (uk) | `uk_<表后缀>_<列缩写>` | `uk_sys_user_lc` |
| 外键 (fk) | `fk_<子表后缀>_<父表后缀>` | `fk_user_role_sys_user` |

**表后缀** = 去掉 `js_`/`ts_`/`biz_`/`gen_` 等公共前缀的后半段（`js_sys_job_log` → `sys_job_log`）。

**列缩写** 规则：下划线/驼峰拆分后各单词首字母（`item_code` → `ic`，`sort_no` → `sn`），
单单词取前 2 字符（`status` → `st`，`name` → `na`）。

#### 长度限制（跨数据库安全）

| 数据库 | 默认标识符长度上限 |
| --- | --- |
| Oracle 12.1 及以下 | **30** |
| MySQL 5.7+ | 64 |
| PostgreSQL 7.3+ | 63 |
| SQL Server | 128 |
| DB2 | 128 |

脚本统一取 **30**（Oracle 兼容），生成/校验时自动裁剪，
超过上限会在 stderr 打印 `[WARN]` 但不中断流程。

#### SQL 关键字警告

跨库公共保留字 500+（覆盖 Oracle / MySQL / PostgreSQL / SQL Server / DB2）。
生成的名字命中关键字时，stderr 打印 `[WARN]`，流程继续。
建议改为：`idx_user_status` → `idx_user_sts` 或 `idx_u_sts`。

#### 规格示例（name 全部省略）

```json
"indexes": [
  {"columns": ["status"]},
  {"columns": ["create_date"]},
  {"columns": ["module_code", "status"], "unique": false}
],
"unique_keys": [{"columns": ["item_code"]}],
// primary_key_name 也可省略，自动生成 pk_demo_item
```

### 关闭 JeeSite 约定

极少数场景（非 JeeSite 项目）需要关闭：

```python
import erm_tools
root = erm_tools.build_empty_diagram(use_jeesite_convention=False)
```

## 4. 命令总览

| 命令 | 作用 |
| --- | --- |
| `create` | 按 JSON 规格生成新的 ERM 文件 |
| `apply` | 在保留原有内容的前提下增量修改已有 ERM 文件 |
| `info` | 输出 ERM 的结构化 JSON 摘要（表、列、索引、外键、备注等） |
| `validate` | 校验结构、id 唯一性与引用完整性 |
| `backups` | 列出临时缓存中的备份记录 |
| `restore` | 从备份恢复文件 |
| `schema` | 输出 JSON 规格模板，可直接照抄修改 |

所有命令的最终结果都以 JSON 打印到标准输出，便于程序/AI 解析；出错时以 JSON 输出到标准错误，退出码见文末。

## 5. create：生成新文件

```bash
python3 scripts/erm_tools.py create --spec spec.json --out db/demo.erm
python3 scripts/erm_tools.py create --spec - --out db/demo.erm < spec.json   # 从标准输入读取规格
```

参数：

- `--spec`：JSON 规格文件路径，`-` 表示标准输入
- `--out`：输出 ERM 路径（目录不存在会自动创建）
- `--database`：数据库类型，缺省取规格里的 `database`，再缺省为 `StandardSQL`
  可选值：`StandardSQL`、`MySQL`、`Oracle`、`PostgreSQL`、`DB2`、`H2`、`HSQLDB`、`SQLite`、
  `SQLServer`、`SQLServer 2008`、`MSAccess`、`Tibero`、`CUBRID`、`Informix`
- `--no-backup`：`--out` 已存在时默认先备份，加此参数可跳过

示例规格：

```json
{
  "database": "MySQL",
  "tables": [
    {
      "name": "js_demo",
      "logical_name": "示例表",
      "description": "示例说明",
      "primary_key_name": "pk_js_demo",
      "columns": [
        {"name": "id", "logical_name": "编号", "type": "varchar", "length": 64,
         "primary_key": true, "not_null": true, "comment": "主键"},
        {"name": "status", "logical_name": "状态", "type": "char", "length": 1,
         "not_null": true, "default_value": "0"},
        {"name": "sort", "logical_name": "排序", "type": "decimal(10,2)"},
        {"name": "create_date", "logical_name": "创建时间", "type": "datetime"}
      ],
      "indexes": [{"name": "idx_js_demo_status", "columns": ["status"]}],
      "unique_keys": [{"name": "uk_js_demo", "columns": ["id", "status"]}]
    },
    {
      "name": "js_demo_item",
      "logical_name": "示例明细",
      "columns": [
        {"name": "id", "type": "varchar", "length": 64, "primary_key": true, "not_null": true},
        {"name": "item_name", "type": "text"}
      ]
    }
  ],
  "relations": [
    {"parent": "js_demo", "child": "js_demo_item", "child_column": "demo_id", "parent_column": "id"}
  ],
  "notes": [{"text": "说明文字", "x": 700, "y": 100}]
}
```

不指定 `position`/`x`/`y` 时，表会按网格自动排布。

### 自动排版规则（create 与 apply 通用）

| 项目 | 默认值 |
| --- | --- |
| 每行列数 | 4 列（排满换行）|
| 起始留白 | x=60、y=60 |
| 表间距 | 横向 80、纵向 80 |
| 最小表宽 / 行高 | 220 / 96 |

- 每列宽度按该列最宽的表计算，每行高度按该行最高的表计算，保证表之间不重叠；
- `create`：所有未指定坐标的表一起排布；
- `apply`：新追加的表从第一个不与现有表重叠的格子开始排，排满 4 列换行；
- 想控制位置时，在表规格里写 `position: {x, y}` 或 `x`/`y`，该表会跳过自动排版。

## 6. apply：修改已有文件

```bash
python3 scripts/erm_tools.py apply --file db/demo.erm --spec patch.json
python3 scripts/erm_tools.py apply --file db/demo.erm --spec patch.json --dry-run
python3 scripts/erm_tools.py apply --file db/demo.erm --spec patch.json --out db/demo_new.erm
```

参数：

- `--file`：待修改的 ERM 文件
- `--spec`：JSON 变更规格（结构同 create，只写要改的部分）
- `--out`：输出路径，缺省原地写回
- `--dry-run`：只做修改与自检，不写文件
- `--no-backup`：不生成备份

语义要点：

- 表、列、关系、备注、视图、序列、触发器都按名字**增量更新**，未提及的内容原样保留；
- 只写部分字段时，其余字段沿用原值（例如只改某列 `comment`，不会动它的类型和索引）；
- 未提及 `indexes` / `unique_keys` 时不动原索引；显式给出则整体替换该表的索引列表；
- 新增外键时若子表没有该列，会自动创建外键列（沿用父列类型，与 ERMaster 行为一致）；
- `drop_columns` 只能删普通列，外键列需先用 `drop_relations` 删除关系；
- 删除表会级联清理指向它的关系、外键列与分类引用；
- 写入前会完整自检（结构 + 引用），自检不通过则不改动文件；
- 文件先写临时文件再原子替换，避免写入中断损坏原文件。

示例变更规格：

```json
{
  "tables": [
    {
      "name": "js_demo",
      "logical_name": "示例表（改名）",
      "columns": [
        {"name": "status", "comment": "状态：0 停用 1 正常"},
        {"name": "remark", "logical_name": "备注", "type": "varchar", "length": 500}
      ],
      "drop_columns": ["sort"]
    }
  ],
  "relations": [
    {"parent": "js_sys_user", "child": "js_demo", "child_column": "user_code", "parent_column": "user_code",
     "on_delete": "CASCADE"}
  ],
  "drop_relations": [{"child": "js_demo_item", "child_column": "demo_id"}],
  "drop_tables": ["js_demo_item"],
  "notes": [{"text": "2026-11 新增说明"}]
}
```

## 7. 规格字段速查

### 表（tables[]）

| 字段 | 说明 |
| --- | --- |
| `name` | 物理名，必填，也是更新时的匹配键 |
| `logical_name` / `description` / `constraint` / `option` | 逻辑名、说明、约束、选项 |
| `primary_key_name` | 主键约束名 |
| `schema` | 表空间名（写入 `table_properties`） |
| `position` 或 `x`/`y` | 图上坐标 |
| `width` / `height` | 图上尺寸（缺省按列数估算） |
| `columns[]` | 列定义，见下 |
| `indexes[]` | 索引，`{name, columns[], unique, full_text, type, description}` |
| `unique_keys[]` | 复合唯一键，`{name, columns[]}` |
| `drop_columns[]` | 要删除的列名 |

### 列（columns[]）

| 字段 | 说明 |
| --- | --- |
| `name` | 物理名，必填 |
| `type` | 类型，必填（新增时）。支持 `varchar`、`varchar(100)`、`decimal(10,2)`、`datetime` 等写法 |
| `length` / `decimal` | 长度、小数位（也可直接写在 `type` 里） |
| `logical_name` / `comment` / `description` | 逻辑名、注释 |
| `primary_key` / `not_null` / `unique_key` / `auto_increment` | 布尔标记 |
| `default_value` / `constraint` / `unique_key_name` | 默认值、约束、唯一键名 |
| `character_set` / `collation` | 字符集、排序规则 |

类型会被规范化为 ERMaster 的真实类型 id（如 `varchar(64)` → `varchar(n)` + 长度 64，
`char` → `character(n)`）。长度与精度存放在文件的字典词条中，这是 ERMaster 的存储方式。

### 关系（relations[]）

| 字段 | 说明 |
| --- | --- |
| `parent` / `child` | 父表、子表的物理名 |
| `parent_column` / `child_column` | 父列名、子表外键列名（缺省同名） |
| `child_cardinality` / `parent_cardinality` | 缺省 `1..n` / `1` |
| `on_delete` / `on_update` | 缺省 `RESTRICT` |
| `reference_for_pk` | 是否引用主键 |

### 其他

- `views[]`：`{name, logical_name, description, sql, schema, columns[]}`
- `notes[]`：`{text, x, y, width, height}`
- `sequences[]`：`{name, schema, increment, min_value, max_value, start, cache, cycle, nocache, order}`
- `triggers[]`：`{name, schema, sql, description}`
- `drop_tables[]`、`drop_relations[]`：删除表、删除关系

## 8. info：查看结构摘要

```bash
python3 scripts/erm_tools.py info --file db/demo.erm
```

输出包含 `database`、各类对象数量、每张表的列（名称/类型/长度/主键/非空/注释/是否外键）、
索引、唯一键、关系、视图、备注等。适合先读结构再决定怎么改。

每张表的 `column_groups` 字段列出该表引用的列组名称；列组内的公共列不在 `columns` 中展开，
修改这类表时只需追加本表自有列，列组引用会被原样保留。

## 9. validate：校验

```bash
python3 scripts/erm_tools.py validate --file db/demo.erm
```

检查项：

1. 根节点及加载器必需的容器节点是否齐全；
2. 表、列、关系、唯一键、字典词条、列组的 id 是否唯一；
3. 引用完整性：`word_id`、`referenced_column`、`relation`、列组引用、分类引用、表空间引用；
4. 类型 id 是否为 ERMaster 合法类型。

有 `errors` 时退出码为 1；`warnings` 不影响退出码。

## 10. 备份与回退

每次 `create`（覆盖已有文件）、`apply`、`restore` 执行时都会自动留一份备份。

- 备份位置：`$ERM_BACKUP_DIR`；未设置时为 `~/.cache/jeesite-erm-backups`
- 每次执行生成一个运行目录：

```
~/.cache/jeesite-erm-backups/
└── 20261114-101530-a1b2/
    ├── demo.erm        # 改动前的原文件
    └── manifest.json   # 时间、命令、原路径、SHA1、大小
```

- 默认保留最近 200 次，超出后自动清理最旧记录
- `create`/`apply` 的输出 JSON 里会返回 `backup_run`（运行 id）与 `backup_file`（备份路径）

查看备份：

```bash
python3 scripts/erm_tools.py backups
python3 scripts/erm_tools.py backups --file db/demo.erm
```

恢复：

```bash
python3 scripts/erm_tools.py restore --file db/demo.erm          # 恢复该文件最近一次备份
python3 scripts/erm_tools.py restore --run 20261114-101530-a1b2  # 恢复到指定备份
python3 scripts/erm_tools.py restore --run 20261114-101530-a1b2 --out db/demo_back.erm  # 恢复到别处
```

恢复前会先把当前文件再备份一次（`command` 为 `restore`），因此误恢复也能再退回去。

临时改备份目录（例如放到项目内）：

```bash
ERM_BACKUP_DIR=./.erm-backups python3 scripts/erm_tools.py apply --file db/demo.erm --spec patch.json
```

## 11. 退出码

| 退出码 | 含义 |
| --- | --- |
| 0 | 成功 |
| 1 | `validate` 校验未通过 |
| 2 | 参数/规格错误、类型不合法、文件读写失败、自检未通过 |

## 12. 注意事项

- 修改已有文件时，工具只重建被提及的表/列/关系节点，其余节点、注释、列组、分类、导出设置原样保留；
- 缩进与空元素写法会被规范化为 ERMaster 当前版本的输出风格（如 `<x/>` 写成 `<x></x>`），不影响内容；
- ERMaster 的字典词条会按列内容去重，`apply` 会清理不再被引用的孤立词条（与 ERMaster 保存行为一致）；
- 视图可以被本工具正常写入并通过 ERMaster 加载；但 ERMaster 自身保存含视图的图会抛异常（上游实现限制），
  如需在 ERMaster 中反复编辑保存，建议先不放视图。
