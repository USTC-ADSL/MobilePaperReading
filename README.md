# 论文共读

这是小组共读论文的 MkDocs Material 知识库。

## 本地预览

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
mkdocs serve
```

网站内容位于 `docs/`。线上编辑入口位于 `/admin/`，通过 Decap CMS 登录后，在 **会议论文** 集合中创建或修改论文。

论文文件按会议和年份归档，例如：

```text
docs/papers/FAST/2024/paper.md
docs/papers/FAST/2025/paper.md
docs/papers/DAC/2024/paper.md
```

## 论文阅读模板

一篇论文阅读通常包括：

- 论文元信息：标题、作者、年份、出处和 DOI
- 一句话摘要和研究问题
- 主要观点、方法、关键结果
- 小组讨论问题和待验证想法
- 正文 Markdown 笔记
