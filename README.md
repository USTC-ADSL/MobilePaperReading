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
docs/papers/fast/24/paper.md
docs/papers/fast/25/paper.md
docs/papers/dac/24/paper.md
```

在内容管理后台的“文件路径”中填写相对 `docs/papers` 的小写路径，例如 `fast/24`。论文表单中的“会议”字段仍可填写 `FAST`、`DAC` 等正式名称。

## 论文阅读模板

当前论文表单只需要填写：

- 标题
- 会议
- Markdown 笔记

年份由论文所在的目录表示，例如 `fast/24`。
