---
name: "support"
description: "检索JeeSite技术支持与服务文档。Invoke when user asks about technical support, licensing, version differences, or contact information."
---

# 技术支持与服务

JeeSite 技术支持服务，包括版本区别、联系方式、授权许可等。

## 使用流程

1. **匹配文档**：根据用户问题，在「文档映射」表中查找最相关的 permalink
2. **获取缓存**：执行 `python3 scripts/cache_docs.py --skill support --permalink <permalink>` 脚本，缓存目录为 `references/.cache/support/`，不存在时自动回退到 `~/.cache/jeesite/support/`
3. **读取内容**：先读 `__00.md` 目录索引文件，了解章节结构，按需读取 `__01.md`~`__NN.md`
4. **回答问题**：缓存文件有效期3天，自动更新缓存，并基于读取的文档内容回答

## 关键词

技术支持、版本区别、联系我们、授权、许可、商业版、社区版、服务

## 触发场景

- 技术支持怎么联系
- 版本有什么区别
- 商业版和社区版区别
- 如何购买授权
- 联系方式

## 文档映射

| 文档标题 | sidebarTitle | permalink | 摘要与关键章节 | 关联文档 |
|----------|-------------|-----------|---------------|---------|
| 技术支持 | 版本区别、联系我们 | /support/ | 技术支持服务、版本区别、授权方案、联系方式。关键章节：版本区别、联系我们 | /overview/、/feature/ |


## 常见问题映射

| 用户问题 | 推荐文档 | WebFetch URL |
|----------|----------|-------------|
| 技术支持怎么联系？ | 技术支持 | https://jeesite.com/docs/support/ |
| 版本有什么区别？ | 技术支持 | https://jeesite.com/docs/support/ |
| 如何购买授权？ | 技术支持 | https://jeesite.com/docs/support/ |
