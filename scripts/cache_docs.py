#!/usr/bin/env python3
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
import argparse
from pathlib import Path
from datetime import datetime, timedelta

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

    manifest = load_manifest()
    skill_manifest = manifest["skills"].get(skill_name, {"documents": {}})
    if "documents" not in skill_manifest:
        skill_manifest["documents"] = {}

    doc_manifest = skill_manifest["documents"].get(permalink, {})

    if not force and cache_path.exists():
        cached_at = doc_manifest.get("updatedAt", "")
        if cached_at and not is_cache_expired(cached_at):
            print(f"CACHED: {title} (缓存有效，{cached_at[:10]})")
            print(f"FILE: {cache_path}")
            return str(cache_path)
        else:
            print(f"EXPIRED: {title} (缓存已过期，需更新)")

    print(f"FETCH: {title} <- {url}")

    markdown = fetch_and_convert(url)
    if markdown is None:
        if cache_path.exists():
            print(f"FALLBACK: 使用过期缓存 {cache_path}")
            return str(cache_path)
        return ""

    header = f"# {title}\n\n> 来源: {url}\n> 缓存时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    full_content = header + markdown

    skill_cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(full_content, encoding="utf-8")

    skill_manifest["documents"][permalink] = {
        "title": title,
        "url": url,
        "file": str(cache_path.relative_to(CACHE_DIR)),
        "updatedAt": datetime.now().isoformat(),
    }
    manifest["skills"][skill_name] = skill_manifest
    save_manifest(manifest)

    print(f"SAVED: {cache_path} ({len(full_content)} 字符)")
    return str(cache_path)


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
