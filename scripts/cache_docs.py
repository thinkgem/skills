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


def clean_html(html: str) -> str:
    """在转换为 Markdown 前，清理 HTML 中不需要的元素"""
    html = re.sub(r'<div[^>]*class="[^"]*line-numbers-wrapper[^"]*"[^>]*>.*?</div>', '', html, flags=re.DOTALL)
    html = re.sub(r'<a[^>]*class="[^"]*header-anchor[^"]*"[^>]*>.*?</a>', '', html, flags=re.DOTALL)
    html = re.sub(r'<span[^>]*class="[^"]*sr-only[^"]*"[^>]*>.*?</span>', '', html, flags=re.DOTALL)
    return html


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
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)
        markdown = re.sub(r"^(#{1,6})\s{2,}", r"\1 ", markdown, flags=re.MULTILINE)
        return markdown.strip()

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
