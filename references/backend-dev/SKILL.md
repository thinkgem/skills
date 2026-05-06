---
name: "backend-dev"
description: "检索JeeSite后端开发文档（安装部署、代码生成、DAO、数据权限、Shiro等）。Invoke when user asks about backend development, installation, code generation, MyBatis DAO, or Shiro permission."
---

# 后端开发手册

JeeSite 后端开发指南，包括安装部署、代码生成、持久层、业务层、控制层、权限认证等。

## 文档获取方式

按需缓存，有效期3天。优先从本地缓存读取，缓存过期或不存在时自动下载并转换为 Markdown：

- **缓存目录**: `references/.cache/backend-dev/`（权限不足时自动回退到 `~/.cache/jeesite/backend-dev/`）
- **缓存命令**: `python3 scripts/cache_docs.py --skill backend-dev --permalink <permalink>`
- **强制更新**: `python3 scripts/cache_docs.py --skill backend-dev --permalink <permalink> --force`

## 关键词

安装、部署、环境搭建、代码生成、DAO、MyBatis、数据权限、Service、Shiro、权限、工具类、数据库管理、REST API、FAQ

## 触发场景

- 如何安装部署JeeSite
- 如何生成代码
- DAO怎么写
- MyBatis怎么用
- 数据权限怎么配置
- Shiro权限怎么控制
- 系统工具类有哪些
- 数据库管理怎么用
- REST API接口
- 后端常见问题

## 文档映射

| 文档标题 | sidebarTitle | permalink | 完整URL | 主题 |
|----------|-------------|-----------|---------|------|
| 安装部署 | 快速开始、安装部署 | /install-deploy/ | https://jeesite.com/docs/install-deploy/ | 环境搭建、新建模块、修改包名、正式部署 |
| 代码生成 | 代码生成、表结构ER图 | /code-gen/ | https://jeesite.com/docs/code-gen/ | 代码生成器、自动生成、业务代码、ER图 |
| DAO与MyBatis | 持久层、@Table、多数据源 | /dao-mybatis/ | https://jeesite.com/docs/dao-mybatis/ | MyBatis、DAO、数据访问、SQL映射、多数据源 |
| 数据权限 | 业务层、数据权限、库事务 | /service-datascope/ | https://jeesite.com/docs/service-datascope/ | 数据权限、数据范围、Service层、事务 |
| 权限与Shiro | 控制层、功能权限、Shiro | /permi-shiro/ | https://jeesite.com/docs/permi-shiro/ | Shiro、权限认证、角色权限、按钮权限、控制层 |
| 系统工具类 | 系统工具类 | /sys-utils/ | https://jeesite.com/docs/sys-utils/ | 工具类、系统工具、常用API |
| 数据库管理 | 动态维护数据、表、实体 | /dbm/ | https://jeesite.com/docs/dbm/ | 数据库管理、数据表建模、数据源、实体 |
| REST API | REST API | /mobile-rest-api/ | https://jeesite.com/docs/mobile-rest-api/ | REST接口、API、移动端接口 |
| 常见问题 | 常见问题 | /faq/ | https://jeesite.com/docs/faq/ | FAQ、常见问题、问题排查 |

## 检索策略

1. 根据用户问题匹配"触发场景"或"关键词"
2. 在"文档映射"表中定位最相关的文档，获取 permalink
3. 执行缓存命令：`python3 scripts/cache_docs.py --skill backend-dev --permalink <permalink>`
   - 若缓存有效（3天内），直接返回缓存文件路径
   - 若缓存过期或不存在，自动下载并转换为 Markdown 保存
4. 使用 Read 工具读取返回的缓存文件路径
5. 基于文档内容回答用户

## 常见问题映射

| 用户问题 | 推荐文档 | WebFetch URL |
|----------|----------|-------------|
| 如何安装部署？ | 安装部署 | https://jeesite.com/docs/install-deploy/ |
| 如何使用代码生成？ | 代码生成 | https://jeesite.com/docs/code-gen/ |
| DAO层怎么写？ | DAO与MyBatis | https://jeesite.com/docs/dao-mybatis/ |
| 数据权限怎么配？ | 数据权限 | https://jeesite.com/docs/service-datascope/ |
| Shiro权限怎么用？ | 权限与Shiro | https://jeesite.com/docs/permi-shiro/ |
| 有哪些工具类？ | 系统工具类 | https://jeesite.com/docs/sys-utils/ |
| 数据库管理怎么用？ | 数据库管理 | https://jeesite.com/docs/dbm/ |
| REST API怎么写？ | REST API | https://jeesite.com/docs/mobile-rest-api/ |
| 后端常见问题？ | 常见问题 | https://jeesite.com/docs/faq/ |
