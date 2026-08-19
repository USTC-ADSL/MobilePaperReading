# PaperReading

这是小组共读论文的 MkDocs Material 知识库。

## 本地预览

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
mkdocs serve
```

网站内容位于 `docs/`。线上编辑入口位于 `/admin/`，通过 Decap CMS 登录后，在对应的会议年份集合中创建或修改论文。

论文文件按会议和会议年份归档，文件名由论文标题自动生成，例如：

```text
docs/papers/FAST/FAST'26/paper-title-a.md
docs/papers/FAST/FAST'26/paper-title-b.md
docs/papers/DAC/DAC'24/paper-title.md
```

内容管理后台按会议年份提供固定目录，例如 `FAST'26`、`DAC'24`，新建论文时不再手填文件路径。论文表单中的“会议”字段填写 `FAST`、`DAC` 等正式名称。

## 论文阅读模板

当前论文表单只需要填写：

- 标题
- 会议
- Markdown 笔记

年份由论文所在的目录表示，例如 `FAST/FAST'26`。
