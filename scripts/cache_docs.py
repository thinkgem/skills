#!/usr/bin/env python3
# Copyright (c) 2013-Now https://jeesite.com All rights reserved.
# No deletion without permission, or be held responsible to law.
"""
JeeSite 文档按需缓存脚本

按需缓存单篇文档，缓存有效期为3天。超过3天自动重新下载更新。
**不支持全量缓存**，仅缓存实际需要的页面，避免给文档服务带来压力。
缓存的页面转换为 Markdown 格式，方便 AI 直接读取。

用法:
    python3 scripts/cache_docs.py --skill quick-start --permalink /overview/
    python3 scripts/cache_docs.py --skill backend-dev --permalink /install-deploy/
    python3 scripts/cache_docs.py --skill frontend-vue --permalink /vue-basic-form/ --force

注意:
    - 必须同时提供 --skill 和 --permalink 参数
    - 为避免文档服务压力过大，全量更新功能已禁用
    - 强制更新(--force)仅对单篇文档生效

退出码:
    0 - 缓存有效或已成功更新
    1 - 缓存失败
"""

import os
import re
import sys
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

import requests
import html2text

SKILLS_DIR = Path(__file__).resolve().parent.parent
REFERENCES_DIR = SKILLS_DIR / "references"
DOCS_BASE_URL = "https://jeesite.com/docs/"

def get_cache_dir() -> Path:
    """获取缓存目录，支持权限自动回退机制"""
    # 默认缓存目录
    default_cache = REFERENCES_DIR / ".cache"
    
    # 检查默认目录是否可写
    try:
        # 尝试创建测试文件来验证可写性
        test_file = default_cache / ".test_write_permission"
        default_cache.mkdir(parents=True, exist_ok=True)
        test_file.touch(exist_ok=True)
        test_file.unlink()
        return default_cache
    except (PermissionError, OSError):
        # 默认目录不可写，使用用户主目录
        home_cache = Path.home() / ".cache" / "jeesite"
        home_cache.mkdir(parents=True, exist_ok=True)
        return home_cache

CACHE_DIR = get_cache_dir()
MANIFEST_FILE = CACHE_DIR / "manifest.json"

# 打印缓存目录信息（仅在首次加载时）
print(f"INFO: 缓存目录: {CACHE_DIR}", file=sys.stderr)

CACHE_EXPIRE_DAYS = 3
REQUEST_TIMEOUT = 30

h2t = html2text.HTML2Text()
h2t.ignore_links = False
h2t.ignore_images = False
h2t.body_width = 0
h2t.skip_internal_links = True
h2t.ignore_emphasis = False
h2t.protect_links = True
h2t.wrap_links = False


def permalink_to_filename(permalink: str) -> str:
    """将 permalink 转换为文件名，如 /overview/ -> overview.md"""
    slug = permalink.strip("/")
    if not slug:
        slug = "index"
    return slug.replace("/", "_") + ".md"


def permalink_to_url(permalink: str) -> str:
    """将 permalink 转换为完整URL"""
    slug = permalink.strip("/")
    return DOCS_BASE_URL.rstrip("/") + "/" + slug + "/"


def load_manifest() -> dict:
    """加载缓存清单文件"""
    if MANIFEST_FILE.exists():
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"version": "2.0", "skills": {}}


def save_manifest(manifest: dict):
    """保存缓存清单文件"""
    manifest["updatedAt"] = datetime.now().isoformat()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def is_cache_expired(cached_at: str) -> bool:
    """判断缓存是否超过有效期（3天）"""
    try:
        cached_time = datetime.fromisoformat(cached_at)
        expire_time = cached_time + timedelta(days=CACHE_EXPIRE_DAYS)
        return datetime.now() > expire_time
    except (ValueError, TypeError):
        return True


# 常见代码块 language 类名前缀（按匹配优先级排序）
_CODE_LANG_CLASS_PATTERNS = [
    r'language-([a-zA-Z0-9_+\-]+)',
    r'lang-([a-zA-Z0-9_+\-]+)',
    r'highlight-([a-zA-Z0-9_+\-]+)',
    r'syntaxhl\s+([a-zA-Z0-9_+\-]+)',
]


def _extract_lang_from_class(attr_str: str) -> str:
    """从 class/style 等属性字符串中提取语言名称，找不到返回空字符串"""
    if not attr_str:
        return ""
    for pat in _CODE_LANG_CLASS_PATTERNS:
        m = re.search(pat, attr_str, flags=re.IGNORECASE)
        if m:
            lang = m.group(1).lower()
            # 过滤掉常见的非语言值
            if lang not in ("none", "text", "plain", "default", "markup"):
                return lang
    return ""


def _extract_lang_from_pre(pre_html: str, wrapper_html: str = "") -> str:
    """综合 pre 自身和外层 wrapper 的 class 提取语言名称"""
    # 优先从外层 wrapper 提取（如 <div class="language-java highlight">）
    for source in (wrapper_html, pre_html):
        class_match = re.search(r'class\s*=\s*"([^"]*)"', source, flags=re.IGNORECASE)
        if class_match:
            lang = _extract_lang_from_class(class_match.group(1))
            if lang:
                return lang
        class_match2 = re.search(r"class\s*=\s*'([^']*)'", source, flags=re.IGNORECASE)
        if class_match2:
            lang = _extract_lang_from_class(class_match2.group(1))
            if lang:
                return lang
    return ""


def _extract_inner_code(block_html: str) -> str:
    """
    从代码块 HTML 中提取真实代码内容：
    1. 优先取 <code> 内部
    2. 其次取 <pre> 内部
    3. 若存在行号表格 <table><tbody><tr><td class="linenos">...</td><td class="code"><pre>...</pre></td></tr></tbody></table>，
       则跳过行号列，仅取 code 列中的 <pre>/<code> 内容
    """
    # 处理行号表格：取第二个 td (code 列) 中的内容
    td_code_match = re.search(
        r'<td[^>]*class\s*=\s*"[^"]*(?<![a-z])code(?![a-z])[^"]*"[^>]*>(.*?)</td>',
        block_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if td_code_match:
        block_html = td_code_match.group(1)

    # 优先 <code>
    code_match = re.search(r'<code[^>]*>(.*?)</code>', block_html, flags=re.DOTALL | re.IGNORECASE)
    if code_match:
        inner = code_match.group(1)
    else:
        pre_match = re.search(r'<pre[^>]*>(.*?)</pre>', block_html, flags=re.DOTALL | re.IGNORECASE)
        if pre_match:
            inner = pre_match.group(1)
        else:
            inner = block_html

    # 清除内部残留的行号元素：<span class="line-numbers-rows"> 等
    inner = re.sub(
        r'<span[^>]*class="[^"]*(line-number|linenos|gutter|line-numbers)[^"]*"[^>]*>.*?</span>',
        '', inner, flags=re.DOTALL | re.IGNORECASE,
    )
    # 清除每行前的行号数字包裹：<span class="line">N</span> 之类
    inner = re.sub(
        r'<(span|div)[^>]*\bclass\s*=\s*"[^"]*\blinen?o\b[^"]*"[^>]*>\s*\d+\s*</\1>',
        '', inner, flags=re.DOTALL | re.IGNORECASE,
    )
    return inner


def normalize_code_blocks(html: str) -> str:
    """
    规范化 HTML 中的代码块结构：
    - 将 <div class="highlight language-xxx"> 包裹的 pre / 行号表格
      统一转换为标准的 <!--LANG:xxx--><pre><code>...</code></pre> 结构
    - 孤立的 <pre> 也补充 <code> 层，便于 html2text 稳定识别为围栏代码块
    - 语言信息通过前后 HTML 注释标记传递给后续 Markdown 后处理阶段
    """
    # 计数器：为每个代码块生成唯一 id，语言信息通过 id 映射写入 HTML 注释
    # 但为了简化，直接在 <pre> 前插入注释即可

    # 1. 处理带 wrapper 的代码块：<div ...highlight...>...</div>
    #    wrapper 内部常嵌套其他 div（行号容器、代码高亮容器等），
    #    不能用非贪婪正则 .*?，需要基于层级计数找到匹配的 </div>
    _wrapper_open_re = re.compile(
        r'<div\b([^>]*\bclass\s*=\s*"[^"]*(highlight|language-|lang-)[^"]*"[^>]*)>',
        flags=re.IGNORECASE,
    )
    _any_div_open_re = re.compile(r'<div\b[^>]*>', flags=re.IGNORECASE)
    _any_div_close_re = re.compile(r'</div\s*>', flags=re.IGNORECASE)

    new_html_parts: list[str] = []
    last_end = 0
    pos = 0
    while True:
        m = _wrapper_open_re.search(html, pos)
        if not m:
            break
        new_html_parts.append(html[last_end:m.start()])
        wrapper_attrs = m.group(1)  # div 开标签内的属性串（含 class，用于提取语言）
        inner_start = m.end()
        depth = 1
        scan = inner_start
        matched_close_start = -1
        # 交替扫描 <div> 与 </div>，按层级深度匹配最外层 wrapper 的闭合位置
        while depth > 0:
            n_open = _any_div_open_re.search(html, scan)
            n_close = _any_div_close_re.search(html, scan)
            if not n_close:
                break
            if n_open and n_open.start() < n_close.start():
                depth += 1
                scan = n_open.end()
            else:
                depth -= 1
                if depth == 0:
                    matched_close_start = n_close.start()
                scan = n_close.end()
        if matched_close_start == -1:
            # 异常 HTML：找不到闭合，保留原标签避免内容丢失
            new_html_parts.append(m.group(0))
            last_end = m.end()
            pos = m.end()
            continue
        inner_html = html[inner_start:matched_close_start]
        # 提取语言和代码内容，生成标准化结构
        lang = _extract_lang_from_pre(inner_html, wrapper_attrs)
        code_text = _extract_inner_code(inner_html)
        lang_comment = f'<!--LANG:{lang}-->' if lang else ''
        new_html_parts.append(
            f'{lang_comment}<pre class="jeesite-norm"><code>{code_text}</code></pre>'
        )
        # 跳过整个 wrapper 及尾随空白，继续扫描
        after_close = html[matched_close_start + len("</div>"):]
        skip_len_match = re.match(r'\s*', after_close)
        skip_len = skip_len_match.end() if skip_len_match else 0
        last_end = matched_close_start + len("</div>") + skip_len
        pos = last_end

    new_html_parts.append(html[last_end:])
    html = "".join(new_html_parts)

    # 2. 处理剩余的孤立 <pre>（未被标准化的），确保内部有 <code>
    def _replace_pre(match: re.Match) -> str:
        pre_open = match.group(1)
        pre_inner = match.group(2)
        lang = _extract_lang_from_class(pre_open)

        # 如果 pre 内已经有完整 <code>...</code>，只在前面补语言注释
        has_code = re.search(r'<code[^>]*>.*?</code>', pre_inner, flags=re.DOTALL | re.IGNORECASE)
        if has_code:
            code_text = pre_inner
        else:
            # 清理孤立 pre 中的内部行号后包一层 code
            code_text = _extract_inner_code(pre_inner)
            code_text = f'<code>{code_text}</code>'

        lang_comment = f'<!--LANG:{lang}-->' if lang else ''
        return f'{lang_comment}<pre class="jeesite-norm"{pre_open[pre_open.find(" "):] if " " in pre_open else ""}>{code_text}</pre>'

    html = re.sub(
        r'<pre\b([^>]*)>(.*?)</pre>',
        _replace_pre,
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # 3. 处理行号 table（无外层 highlight wrapper 时）：<table class="codehilitetable"> 或 class 含 linenos
    #    捕获组：group(1) = table 开标签属性串；group(2) = class 中的关键字；
    #            group(3) = table 内部完整 HTML
    def _replace_table(match: re.Match) -> str:
        table_open = match.group(1)
        table_inner = match.group(3)
        lang = _extract_lang_from_class(table_open)
        code_text = _extract_inner_code(f'<table><tbody><tr>{table_inner}</tr></tbody></table>')
        lang_comment = f'<!--LANG:{lang}-->' if lang else ''
        return f'{lang_comment}<pre class="jeesite-norm"><code>{code_text}</code></pre>'

    html = re.sub(
        r'<table\b([^>]*\bclass\s*=\s*"[^"]*(codehilitetable|highlighttable|linenos)[^"]*"[^>]*)>'
        r'(.*?)</table>',
        _replace_table,
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    return html


def clean_html(html: str) -> str:
    """在转换为 Markdown 前，清理 HTML 中不需要的元素，并规范化代码块结构"""
    # 1) 先规范化代码块结构（在清除行号之前，便于行号 table 被正确识别并剥离）
    html = normalize_code_blocks(html)

    # 2) 清理无关元素
    html = re.sub(r'<div[^>]*class="[^"]*line-numbers-wrapper[^"]*"[^>]*>.*?</div>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<a[^>]*class="[^"]*header-anchor[^"]*"[^>]*>.*?</a>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<span[^>]*class="[^"]*sr-only[^"]*"[^>]*>.*?</span>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # 3) 清理代码块内部残留的行号列（防止行号 table 未被完全匹配时仍残留行号）
    #    注意：此操作放在 normalize_code_blocks 之后，避免破坏结构识别
    html = re.sub(
        r'<td[^>]*\bclass\s*=\s*"[^"]*(linenos|gutter|line-number)[^"]*"[^>]*>.*?</td>',
        '', html, flags=re.DOTALL | re.IGNORECASE,
    )

    # 4) 清理 Vdoing 主题的复制按钮
    html = re.sub(
        r'<(button|div|span)[^>]*\bclass\s*=\s*"[^"]*(copy-button|copycode|copy-btn)[^"]*"[^>]*>.*?</\1>',
        '', html, flags=re.DOTALL | re.IGNORECASE,
    )

    return html


# 根据代码内容启发式判断语言（用于兜底，覆盖常见 JeeSite 场景）
_LANG_HINTS = [
    # (识别特征正则, 语言标签)
    (re.compile(r'^\s*<\?xml\s', re.MULTILINE), 'xml'),
    (re.compile(r'^\s*<\?php\s', re.MULTILINE), 'php'),
    (re.compile(r'^\s*<!DOCTYPE\s+html', re.IGNORECASE | re.MULTILINE), 'html'),
    (re.compile(r'^\s*package\s+[\w.]+\s*;\s*(//|/\*|import|public|private|class|@)', re.MULTILINE), 'java'),
    (re.compile(r'^\s*import\s+static\s+[\w.]+;', re.MULTILINE), 'java'),
    (re.compile(r'@(RequestMapping|GetMapping|PostMapping|Service|Controller|Autowired|Bean)\b'), 'java'),
    (re.compile(r'^\s*export\s+default\s*\{?', re.MULTILINE), 'js'),
    (re.compile(r'^\s*(const|let|var)\s+\w+\s*=\s*require\s*\(', re.MULTILINE), 'js'),
    (re.compile(r'<(template|script|style)\b'), 'vue'),
    (re.compile(r'^\s*<template\b'), 'vue'),
    (re.compile(r'^\s*def\s+\w+\s*\(.*?\)\s*:\s*\w+\s*:', re.MULTILINE), 'python'),
    (re.compile(r'^\s*#include\s*<', re.MULTILINE), 'cpp'),
    (re.compile(r'^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER)\s+', re.IGNORECASE | re.MULTILINE), 'sql'),
    (re.compile(r'^\s*--\s.*$', re.MULTILINE), 'sql'),
    (re.compile(r'^\s*docker\s+(run|build|compose|exec)\s', re.IGNORECASE | re.MULTILINE), 'bash'),
    (re.compile(r'^\s*\$\s+\S+', re.MULTILINE), 'bash'),
    (re.compile(r'^\s*yum\s+install\s|^\s*apt(-get)?\s+install\s', re.MULTILINE), 'bash'),
    (re.compile(r'^\s*server\s*\{|^\s*location\s+\S+\s*\{', re.MULTILINE), 'nginx'),
    # ini: 同时出现 [section] 与 key=value
    (re.compile(r'\[[\w.]+\].*\n\s*\w+\s*=\s*\S+', re.MULTILINE | re.DOTALL), 'ini'),
    # yaml: 同时出现 key: value 与列表项 - xxx
    (re.compile(r'^[\w-]+\s*:\s*\S.*\n\s*-\s+\S', re.MULTILINE), 'yaml'),
]


def _guess_language(code: str) -> str:
    """根据代码内容启发式判断语言，失败返回空字符串"""
    if not code.strip():
        return ""
    score_map: dict[str, int] = {}
    for pat, lang in _LANG_HINTS:
        # 注意 _LANG_HINTS 中有一项是 tuple of compiled regex 与 bool 的特殊情况需要跳过
        # 这里直接判断是否为 re.Pattern
        if isinstance(pat, re.Pattern) and pat.search(code):
            score_map[lang] = score_map.get(lang, 0) + 1
    if score_map:
        return max(score_map.items(), key=lambda kv: kv[1])[0]
    return ""


def postprocess_markdown(markdown: str) -> str:
    """
    Markdown 后处理：修复代码块围栏问题
    1) 将前置的 <!--LANG:xxx--> 注释注入到紧随其后的 ``` 围栏上
    2) 校验 ``` / ~~~ 围栏配对，自动补齐未闭合的围栏
    3) 启发式把"看起来像代码却没被围栏包裹"的连续缩进段落包进 ``` 围栏
    4) 清理残留的 LANG 注释和多余空行
    """
    lines = markdown.split("\n")
    out_lines: list[str] = []
    in_fence = False          # 是否处于代码块围栏内部
    fence_char = ""           # 当前围栏字符 ``` 或 ~~~
    fence_len = 0             # 当前围栏长度
    pending_lang = ""         # 前一行读到的 <!--LANG:xxx--> 信息，待写入下一个围栏开头

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 1. 识别 LANG 注释（注入语言标签）
        lang_match = re.match(r'\s*<!--\s*LANG\s*:\s*([a-zA-Z0-9_+\-]*)\s*-->\s*$', line)
        if lang_match and not in_fence:
            pending_lang = lang_match.group(1).strip().lower()
            i += 1
            continue

        # 2. 识别代码块围栏（``` 或 ~~~，允许前导空格，可选 info string）
        fence_match = re.match(r'^(\s*)(```+|~~~+)(\s*[a-zA-Z0-9_+\-]*)\s*$', line)
        if fence_match:
            indent = fence_match.group(1)
            mark = fence_match.group(2)
            info = fence_match.group(3).strip()
            char = mark[0]
            length = len(mark)

            if not in_fence:
                # 开启围栏：如有 pending_lang 且 info 为空，写入语言标签
                if pending_lang and not info:
                    info = pending_lang
                pending_lang = ""
                out_lines.append(f"{indent}{char * length}{(' ' + info) if info else ''}")
                in_fence = True
                fence_char = char
                fence_len = length
                i += 1
                continue
            else:
                # 关闭围栏：只有字符匹配且长度>=开启长度时才算闭合
                if char == fence_char and length >= fence_len:
                    out_lines.append(f"{indent}{char * fence_len}")
                    in_fence = False
                    fence_char = ""
                    fence_len = 0
                    i += 1
                    continue
                # 否则当作代码块内部普通行
                out_lines.append(line)
                i += 1
                continue

        # 3. 围栏内：原样输出
        if in_fence:
            out_lines.append(line)
            i += 1
            continue

        # 4. 围栏外：检查"疑似代码但未被围栏包裹"的情况
        #    启发式：连续 N 行（>=2）具有相同前导 4/8 空格缩进，且首行/末行之间呈现代码特征。
        #    先向前看收集 candidate 块
        if re.match(r'^( {4,}|\t)', line) and stripped:
            # 至少 4 空格或 Tab 缩进，非空行 -> 候选代码块
            start_i = i
            candidate_lines: list[str] = []
            min_indent = None
            while i < len(lines):
                cur = lines[i]
                s = cur.strip()
                # 允许块内空行
                if s == "":
                    candidate_lines.append(cur)
                    i += 1
                    continue
                # 必须满足 4 空格/Tab 缩进（或与首行缩进一致）
                if re.match(r'^( {4,}|\t)', cur):
                    lead_spaces = len(cur) - len(cur.lstrip(" "))
                    tabs = 0
                    if cur.startswith("\t"):
                        tabs = len(cur) - len(cur.lstrip("\t"))
                        indent_val = tabs * 4
                    else:
                        indent_val = lead_spaces
                    if min_indent is None or indent_val < min_indent:
                        min_indent = indent_val
                    candidate_lines.append(cur)
                    i += 1
                    continue
                break
            # 去掉 trailing 空行（用于截断判断）
            trailing = 0
            for c in reversed(candidate_lines):
                if c.strip() == "":
                    trailing += 1
                else:
                    break
            trimmed = candidate_lines[:len(candidate_lines) - trailing] if trailing else candidate_lines

            # 块内至少 1 行有效缩进内容；若只有 1 行则要求有较强代码特征
            non_empty = [c for c in trimmed if c.strip() != ""]
            if len(non_empty) >= 1:
                stripped_sample = "\n".join(c.strip() for c in non_empty)
                code_like = False
                if len(non_empty) >= 3:
                    code_like = True
                elif len(non_empty) == 2:
                    code_like = True
                else:
                    # 单行：必须含代码特征
                    one = stripped_sample
                    if (";" in one or "{" in one or "}" in one or "=>" in one
                            or " <- " in one or one.startswith("#") or one.startswith("$")
                            or one.startswith("import ") or one.startswith("package ")
                            or " = " in one or re.search(r'[A-Za-z_]\(.*\)', one)):
                        code_like = True

                if code_like:
                    # 去一层统一缩进（去掉最外层 4 空格或 Tab）
                    def _dedent(c: str) -> str:
                        if c.strip() == "":
                            return ""
                        if c.startswith("\t"):
                            return c[1:]
                        if c.startswith("    "):
                            return c[4:]
                        return c
                    dedented = [_dedent(c) for c in candidate_lines]
                    code_block_content = "\n".join(dedented)
                    # 优先用 pending_lang，其次内容猜测
                    lang = pending_lang or _guess_language(stripped_sample)
                    pending_lang = ""
                    out_lines.append("```" + lang)
                    out_lines.append(code_block_content.rstrip("\n"))
                    out_lines.append("```")
                    continue
                else:
                    # 非代码：还原（原样输出）
                    out_lines.extend(candidate_lines)
                    continue
            else:
                # 无有效内容：空行输出
                out_lines.extend(candidate_lines)
                continue

        # 5. 普通行直接输出，并清空可能悬而未决的 pending_lang（LANG 没紧贴到围栏时忽略）
        pending_lang = ""
        out_lines.append(line)
        i += 1

    # 6. 文档末尾：如仍有未闭合围栏，自动补齐闭合
    if in_fence:
        out_lines.append(fence_char * fence_len)
        in_fence = False
        fence_char = ""
        fence_len = 0

    # 7. 重新连接 + 清理残留的其他 HTML 注释
    result = "\n".join(out_lines)
    # 清理普通 HTML 注释（保护代码块内的除外——简单处理：仅处理围栏外）
    # 这里用简易做法：删除行首独立出现的 HTML 注释行
    result_lines = result.split("\n")
    cleaned: list[str] = []
    in_fence2 = False
    fc = ""
    fl = 0
    for line in result_lines:
        m = re.match(r'^(```+|~~~+)', line)
        if m and (not in_fence2 or (m.group(1)[0] == fc and len(m.group(1)) >= fl)):
            if not in_fence2:
                in_fence2 = True
                fc = m.group(1)[0]
                fl = len(m.group(1))
            else:
                in_fence2 = False
                fc = ""
                fl = 0
            cleaned.append(line)
            continue
        if not in_fence2:
            # 删除明显的仅包含 HTML 注释的行
            if re.match(r'\s*<!--.*?-->\s*$', line):
                continue
            # 删除剩单的注释残片
            line = re.sub(r'\s*<!--.*?-->', '', line)
        cleaned.append(line)
    result = "\n".join(cleaned)

    # 8. 基础清理（与原有流程保持一致）
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = re.sub(r"^(#{1,6})\s{2,}", r"\1 ", result, flags=re.MULTILINE)
    return result.strip()


def fetch_and_convert(url: str) -> str | None:
    """请求 URL 获取 HTML 并转换为 Markdown"""
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers={
            "User-Agent": "JeeSite-Docs-Cache/2.0",
            "Accept": "text/html",
        })
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        html_content = resp.text

        content_match = re.search(
            r'<div[^>]*class="[^"]*theme-vdoing-content[^"]*"[^>]*>(.*?)</div>\s*<footer',
            html_content,
            re.DOTALL,
        )
        if content_match:
            html_fragment = content_match.group(1)
        else:
            content_match2 = re.search(
                r'<div[^>]*class="[^"]*theme-vdoing-content[^"]*"[^>]*>(.*)',
                html_content,
                re.DOTALL,
            )
            if content_match2:
                html_fragment = content_match2.group(1)
                footer_idx = html_fragment.find('<footer')
                if footer_idx > 0:
                    html_fragment = html_fragment[:footer_idx]
                page_nav_idx = html_fragment.find('<div class="page-nav')
                if page_nav_idx > 0:
                    html_fragment = html_fragment[:page_nav_idx]
            else:
                html_fragment = html_content

        html_fragment = clean_html(html_fragment)

        markdown = h2t.handle(html_fragment)
        # 使用后处理修复代码块围栏、注入语言 tag、补齐未闭合围栏
        markdown = postprocess_markdown(markdown)
        return markdown

    except requests.RequestException as e:
        print(f"ERROR: 请求失败 {url} - {e}", file=sys.stderr)
        return None


def download_images(markdown: str, doc_url: str, skill_name: str, cache_file_dir: Path) -> str:
    """
    下载文档中引用的图片到本地缓存，并替换 Markdown 中的图片链接。
    支持相对路径和绝对 URL。
    cache_file_dir: 缓存 Markdown 文件所在目录，用于计算图片相对路径。
    """
    img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    img_cache_dir = CACHE_DIR / "images" / skill_name
    img_cache_dir.mkdir(parents=True, exist_ok=True)

    def replace_img(match):
        alt_text = match.group(1)
        img_src = match.group(2).strip()

        if not img_src:
            return match.group(0)

        img_url = img_src
        if not img_url.startswith(("http://", "https://")):
            img_url = urljoin(doc_url, img_url)

        url_hash = hashlib.md5(img_url.encode()).hexdigest()[:12]
        parsed = urlparse(img_url)
        ext = os.path.splitext(parsed.path)[1]
        if not ext or len(ext) > 6:
            ext = ".png"
        local_name = f"{url_hash}{ext}"
        local_path = img_cache_dir / local_name

        if not local_path.exists():
            try:
                img_resp = requests.get(img_url, timeout=REQUEST_TIMEOUT, headers={
                    "User-Agent": "JeeSite-Docs-Cache/2.0",
                })
                img_resp.raise_for_status()
                local_path.write_bytes(img_resp.content)
            except requests.RequestException as e:
                print(f"WARN: 图片下载失败 {img_url} - {e}", file=sys.stderr)
                return match.group(0)

        relative_path = os.path.relpath(str(local_path), str(cache_file_dir))
        return f"![{alt_text}]({relative_path})"

    return img_pattern.sub(replace_img, markdown)


def split_document(markdown: str, title: str, url: str, cache_path: Path) -> list[Path]:
    """
    按一级标题（##）将文档拆分为多个子文件。
    前言部分保留在主索引文件中，仅 ## 章节拆分为独立子文件。
    每个子文件包含：文档标题头部、章节内容、章节导航。
    返回拆分后的文件路径列表（不含主索引文件）。
    """
    stem = cache_path.stem
    parent_dir = cache_path.parent
    
    # 索引文件使用 __00.md 命名，确保在所有系统中排在最前面
    index_filename = f"{stem}__00.md"
    index_path = parent_dir / index_filename
    
    # 清理旧的缓存文件：明确删除不带 __ 的主文件和所有 __*.md 拆分文件
    deleted_count = 0
    
    # 1. 删除旧的主文件（如 code-gen.md）
    old_main_file = parent_dir / f"{stem}.md"
    if old_main_file.exists() and old_main_file != cache_path:
        try:
            old_main_file.unlink()
            deleted_count += 1
            print(f"CLEANUP: 删除旧主文件 {old_main_file.name}", file=sys.stderr)
        except Exception as e:
            print(f"WARN: 删除旧主文件失败 {old_main_file.name} - {e}", file=sys.stderr)
    
    # 2. 删除所有旧的拆分文件（如 code-gen__01.md, code-gen__00.md 等）
    old_split_files = list(parent_dir.glob(f"{stem}__*.md"))
    for old_file in old_split_files:
        try:
            old_file.unlink()
            deleted_count += 1
        except Exception as e:
            print(f"WARN: 删除旧拆分文件失败 {old_file.name} - {e}", file=sys.stderr)
    
    if deleted_count > 0:
        print(f"CLEANUP: 共删除 {deleted_count} 个旧文件", file=sys.stderr)

    lines = markdown.split("\n")
    preamble_lines = []
    chapters = []
    current_chapter = []
    current_heading = ""
    in_preamble = True

    for line in lines:
        if re.match(r'^##\s+', line):
            in_preamble = False
            if current_chapter:
                chapters.append((current_heading, "\n".join(current_chapter)))
            current_heading = line.strip()
            current_chapter = [line]
        elif in_preamble:
            # 过滤掉重复的标题和元信息行
            if not re.match(r'^#\s+', line) and not re.match(r'^>\s*(来源|缓存时间|章节):', line):
                preamble_lines.append(line)
        else:
            current_chapter.append(line)

    if current_chapter:
        chapters.append((current_heading, "\n".join(current_chapter)))

    # 如果没有章节（纯前言文档），创建一个空章节
    if not chapters:
        chapters.append(("", ""))

    split_files = []

    for i, (heading, content) in enumerate(chapters):
        chapter_num = i + 1
        chapter_title = heading.lstrip("#").strip() if heading else "概述"
        split_filename = f"{stem}__{chapter_num:02d}.md"
        split_path = parent_dir / split_filename

        header = f"# {title}\n\n> 来源: {url}\n> 缓存时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n> 章节: {chapter_num}/{len(chapters)} - {chapter_title}\n\n"

        nav_lines = ["\n---\n\n**章节导航：**\n"]
        if i > 0:
            prev_file = f"{stem}__{i:02d}.md"
            nav_lines.append(f"- [上一章：{chapters[i-1][0].lstrip('#').strip() if chapters[i-1][0] else '概述'}]({prev_file})\n")
        if i < len(chapters) - 1:
            next_file = f"{stem}__{i+2:02d}.md"
            nav_lines.append(f"- [下一章：{chapters[i+1][0].lstrip('#').strip() if chapters[i+1][0] else '概述'}]({next_file})\n")
        nav_lines.append(f"- [返回目录]({index_filename})\n")

        full_content = header + content + "".join(nav_lines)
        split_path.write_text(full_content, encoding="utf-8")
        split_files.append(split_path)

    preamble = "\n".join(preamble_lines).strip()
    
    index_lines = [f"# {title} - 目录\n\n", f"> 来源: {url}\n> 缓存时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n> 共 {len(chapters)} 个章节\n"]
    if preamble:
        index_lines.append("\n---\n\n" + preamble)
    index_lines.append("\n---\n\n")
    for i, (heading, _) in enumerate(chapters):
        chapter_title = heading.lstrip("#").strip() if heading else "概述"
        split_filename = f"{stem}__{i+1:02d}.md"
        index_lines.append(f"{i+1}. [{chapter_title}]({split_filename})\n")

    index_path.write_text("".join(index_lines), encoding="utf-8")

    return split_files


def parse_skill_md(skill_md_path: Path) -> dict:
    """
    解析 SKILL.md 文件，提取 name 和文档映射表中的 permalink、url 信息。
    """
    content = skill_md_path.read_text(encoding="utf-8")
    name_match = re.search(r'^name:\s*"?([^"\n]+)"?', content, re.MULTILINE)
    skill_name = name_match.group(1).strip() if name_match else skill_md_path.parent.name

    documents = []
    lines = content.split("\n")
    in_table = False
    headers = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and "---" in stripped:
            in_table = True
            continue
        if not stripped.startswith("|"):
            if in_table and documents:
                break
            continue
        if not in_table:
            header_line = stripped
            headers = [h.strip() for h in header_line.split("|")[1:-1]]
            continue

        cells = [c.strip() for c in stripped.split("|")[1:-1]]
        if len(cells) < 4:
            continue

        row = dict(zip(headers, cells))

        permalink = row.get("permalink", "").strip()
        url = row.get("完整URL", row.get("url", "")).strip()
        title = row.get("文档标题", row.get("title", "")).strip()

        if not permalink and not url:
            continue

        if not url and permalink:
            url = permalink_to_url(permalink)

        if not permalink and url:
            m = re.search(r"/docs(/.+?)/?$", url)
            permalink = m.group(1) + "/" if m else "/"

        documents.append({
            "title": title,
            "permalink": permalink,
            "url": url,
        })

    return {"name": skill_name, "documents": documents}


def resolve_doc_info(skill_name: str, permalink: str) -> dict | None:
    """
    从 SKILL.md 中解析文档标题和URL。
    如果解析失败，根据 permalink 推算URL。
    """
    skill_md = REFERENCES_DIR / skill_name / "SKILL.md"
    if not skill_md.exists():
        return None

    content = skill_md.read_text(encoding="utf-8")
    url = permalink_to_url(permalink)
    title = permalink.strip("/").split("/")[-1]

    lines = content.split("\n")
    headers = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and "---" in stripped:
            in_table = True
            continue
        if not stripped.startswith("|"):
            if in_table:
                break
            continue
        if not in_table:
            headers = [h.strip() for h in stripped.split("|")[1:-1]]
            continue

        cells = [c.strip() for c in stripped.split("|")[1:-1]]
        if len(cells) < 4:
            continue

        row = dict(zip(headers, cells))
        row_permalink = row.get("permalink", "").strip()

        if row_permalink == permalink:
            title = row.get("文档标题", row.get("title", title)).strip()
            row_url = row.get("完整URL", row.get("url", "")).strip()
            if row_url:
                url = row_url
            return {"title": title, "permalink": permalink, "url": url}

    return {"title": title, "permalink": permalink, "url": url}


def cache_page(skill_name: str, permalink: str, force: bool = False) -> str:
    """
    缓存单篇文档。
    返回缓存文件的绝对路径，失败返回空字符串。
    """
    doc_info = resolve_doc_info(skill_name, permalink)
    if not doc_info:
        print(f"ERROR: 未找到 Skill '{skill_name}' 或 permalink '{permalink}'", file=sys.stderr)
        return ""

    title = doc_info["title"]
    url = doc_info["url"]
    filename = permalink_to_filename(permalink)
    skill_cache_dir = CACHE_DIR / skill_name
    cache_path = skill_cache_dir / filename
    
    # 索引文件使用 __00.md 命名
    stem = cache_path.stem
    index_filename = f"{stem}__00.md"
    index_path = skill_cache_dir / index_filename

    manifest = load_manifest()
    skill_manifest = manifest["skills"].get(skill_name, {"documents": {}})
    if "documents" not in skill_manifest:
        skill_manifest["documents"] = {}

    doc_manifest = skill_manifest["documents"].get(permalink, {})

    if not force and index_path.exists():
        cached_at = doc_manifest.get("updatedAt", "")
        if cached_at and not is_cache_expired(cached_at):
            print(f"CACHED: {title} (缓存有效，{cached_at[:10]})")
            print(f"FILE: {index_path}")
            return str(index_path)
        else:
            print(f"EXPIRED: {title} (缓存已过期，需更新)")

    print(f"FETCH: {title} <- {url}")

    markdown = fetch_and_convert(url)
    if markdown is None:
        if index_path.exists():
            print(f"FALLBACK: 使用过期缓存 {index_path}")
            return str(index_path)
        return ""

    header = f"# {title}\n\n> 来源: {url}\n> 缓存时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    full_content = header + markdown

    full_content = download_images(full_content, url, skill_name, skill_cache_dir)

    skill_cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(full_content, encoding="utf-8")

    split_files = split_document(full_content, title, url, cache_path)
    
    # 删除临时主文件，只保留索引文件和拆分文件
    if cache_path.exists():
        try:
            cache_path.unlink()
        except Exception as e:
            print(f"WARN: 删除临时文件失败 {cache_path.name} - {e}", file=sys.stderr)
    
    # 返回索引文件路径（__00.md）
    result_path = index_path if index_path.exists() else cache_path

    skill_manifest["documents"][permalink] = {
        "title": title,
        "url": url,
        "file": str(index_path.relative_to(CACHE_DIR)),
        "splitFiles": [str(p.relative_to(CACHE_DIR)) for p in split_files],
        "updatedAt": datetime.now().isoformat(),
    }
    manifest["skills"][skill_name] = skill_manifest
    save_manifest(manifest)

    print(f"SAVED: {result_path} ({len(full_content)} 字符)")
    return str(result_path)


def discover_skills() -> list[dict]:
    """自动发现所有子 Skill 目录并解析"""
    skills = []
    for item in sorted((REFERENCES_DIR).iterdir()):
        if not item.is_dir():
            continue
        skill_md = item / "SKILL.md"
        if skill_md.exists():
            skill_info = parse_skill_md(skill_md)
            skills.append(skill_info)
    return skills


def main():
    parser = argparse.ArgumentParser(description="JeeSite 文档按需缓存工具（3天有效期）")
    parser.add_argument("--skill", help="Skill 名称，如 quick-start、backend-dev")
    parser.add_argument("--permalink", help="文档 permalink，如 /overview/、/install-deploy/")
    parser.add_argument("--force", action="store_true", help="强制更新（忽略缓存有效期）")
    args = parser.parse_args()

    if not args.skill or not args.permalink:
        parser.print_help()
        print("\nERROR: 必须提供 --skill 和 --permalink 参数", file=sys.stderr)
        print("注意：为避免文档服务压力过大，已禁用全量更新功能", file=sys.stderr)
        sys.exit(1)

    result = cache_page(args.skill, args.permalink, force=args.force)
    if result:
        print(f"OK: {result}")
        sys.exit(0)
    else:
        print("FAIL: 缓存失败", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
