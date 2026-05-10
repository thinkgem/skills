---
name: "support"
description: "检索JeeSite技术支持与服务文档。Invoke when user asks about technical support, licensing, version differences, or contact information."
---

# 技术支持与服务

JeeSite 技术支持服务，包括版本区别、联系方式、授权许可等。

## 文档获取方式

按需缓存，有效期3天。优先从本地缓存读取，缓存过期或不存在时自动下载并转换为 Markdown：

- **缓存目录**: `references/.cache/support/`（权限不足时自动回退到 `~/.cache/jeesite/support/`）
- **缓存命令**: `python3 scripts/cache_docs.py --skill support --permalink <permalink>`
- **强制更新**: `python3 scripts/cache_docs.py --skill support --permalink <permalink> --force`

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

## 检索策略

1. 根据用户问题匹配"触发场景"或"关键词"
2. 在"文档映射"表中定位最相关的文档，获取 permalink
3. 执行缓存命令：`python3 scripts/cache_docs.py --skill support --permalink <permalink>`
   - 若缓存有效（3天内），直接返回缓存文件路径
   - 若缓存过期或不存在，自动下载并转换为 Markdown 保存
4. 使用 Read 工具读取返回的缓存文件路径
5. 基于文档内容回答用户

## 常见问题映射

| 用户问题 | 推荐文档 | WebFetch URL |
|----------|----------|-------------|
| 技术支持怎么联系？ | 技术支持 | https://jeesite.com/docs/support/ |
| 版本有什么区别？ | 技术支持 | https://jeesite.com/docs/support/ |
| 如何购买授权？ | 技术支持 | https://jeesite.com/docs/support/ |
