from pathlib import Path
import re

import yaml


FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _metadata(path):
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


def _paper_list(config):
    papers_dir = Path(config.docs_dir) / "papers"
    papers = []

    for path in papers_dir.rglob("*.md"):
        if path.name == "index.md" or path.name.startswith("_"):
            continue
        data = _metadata(path)
        relative_path = path.relative_to(config.docs_dir).as_posix()
        year = data.get("year", "")
        try:
            sort_year = int(year)
        except (TypeError, ValueError):
            sort_year = 0
        papers.append((sort_year, relative_path, data))

    papers.sort(key=lambda item: (-item[0], item[1]))
    if not papers:
        return "暂无论文。请从 [内容管理后台](/admin/) 新建一篇论文。"

    lines = []
    for _, relative_path, data in papers:
        title = str(data.get("title") or Path(relative_path).stem)
        conference = str(data.get("conference") or "")
        year = str(data.get("year") or "")
        status = str(data.get("status") or "")
        details = " · ".join(value for value in (conference, year, status) if value)
        suffix = f" — {details}" if details else ""
        lines.append(f"- [{title}]({relative_path}){suffix}")
    return "\n".join(lines)


def on_page_markdown(markdown, page, config, files):
    if page.file.src_uri != "index.md":
        return markdown
    return markdown.replace("<!-- PAPER_LIST -->", _paper_list(config))

