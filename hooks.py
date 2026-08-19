from pathlib import Path
import re

import yaml


FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _metadata(path):
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


def _path_context(path, papers_dir):
    parts = path.relative_to(papers_dir).parts
    if len(parts) < 3:
        return "", ""
    conference_names = {
        "dac": "DAC",
        "eurosys": "Eurosys",
        "fast": "FAST",
        "icml": "ICML",
        "mobicom": "MobiCom",
    }
    conference = conference_names.get(parts[0].lower(), parts[0])
    year_match = re.search(r"(\d{2,4})$", parts[1])
    year = year_match.group(1) if year_match else parts[1]
    return conference, year


def _sort_year(value):
    match = re.search(r"(\d{2,4})$", str(value).strip())
    value = match.group(1) if match else value
    try:
        year = int(value)
    except (TypeError, ValueError):
        return 0
    return year + 2000 if 0 <= year < 100 else year


def _paper_list(config):
    papers_dir = Path(config.docs_dir) / "papers"
    papers = []

    for path in papers_dir.rglob("*.md"):
        if path.name.startswith("_"):
            continue
        data = _metadata(path)
        relative_path = path.relative_to(config.docs_dir).as_posix()
        path_conference, path_year = _path_context(path, papers_dir)
        year = str(data.get("year") or path_year)
        sort_year = _sort_year(year)
        papers.append((sort_year, relative_path, data, path_conference, path_year))

    papers.sort(key=lambda item: (-item[0], item[1]))
    if not papers:
        return "暂无论文。请从 [内容管理后台](/admin/) 新建一篇论文。"

    lines = []
    for _, relative_path, data, path_conference, path_year in papers:
        title = str(data.get("title") or Path(relative_path).stem)
        conference = str(data.get("conference") or path_conference)
        year = str(data.get("year") or path_year)
        status = str(data.get("status") or "")
        details = " · ".join(value for value in (conference, year, status) if value)
        suffix = f" — {details}" if details else ""
        lines.append(f"- [{title}]({relative_path}){suffix}")
    return "\n".join(lines)


def on_page_markdown(markdown, page, config, files):
    if page.file.src_uri != "index.md":
        return markdown
    return markdown.replace("<!-- PAPER_LIST -->", _paper_list(config))
