---
name: xmind
description: Use when the user wants to read, create, edit, or manipulate XMind mind map files (.xmind). For creating new mind maps, ALWAYS generate Markdown first then convert with md_to_xmind.py — never construct the XMind JSON structure manually.
---

# XMind File Operations

## Overview

Two workflows for two scenarios:

| Scenario | Method |
|----------|--------|
| **Creating a NEW mind map** | 1. AI generates Markdown → 2. `md_to_xmind.py` converts to `.xmind` |
| **Reading / Editing an EXISTING .xmind** | Use `xmind_tools.py` read/export/modify commands |

## Creating: Markdown → XMind (Primary)

### Step 1: AI generates Markdown

Use heading levels to represent the mind map tree:

```
# {根主题 ─ 即 Sheet 标题}

## {一级分支}
非标题行作为备注（note），可选。

### {二级分支}

#### {三级分支}

## {另一个一级分支}
```

- `# H1` = Sheet 的根主题。**多个 `#` 创建多个 Sheet**
- `## H2` = 根主题的直接子节点
- `### H3` = 上一个 H2 的子节点
- `#### H4` = 上一个 H3 的子节点
- 标题之间的段落/列表文本 → 作为该主题的备注
- `---` 分隔符会被忽略

**AI 操作步骤：**
1. 先输出 Markdown 让用户确认结构
2. 将 Markdown 内容写入 `.md` 文件
3. 运行转换命令

### Step 2: Convert

```bash
# 基础转换
python .claude/skills/xmind/md_to_xmind.py input.md output.xmind

# 带模板（继承样式/主题）
python .claude/skills/xmind/md_to_xmind.py input.md output.xmind --template existing.xmind
```

**模板建议：** 使用项目中的 `.xmind` 文件作为模板可继承其配色和样式。

## Reading Existing XMind

```bash
# 列出所有主题及 ID（树形结构）
python .claude/skills/xmind/xmind_tools.py file.xmind list

# 打印完整 JSON 结构
python .claude/skills/xmind/xmind_tools.py file.xmind read
```

## Editing Existing XMind

```bash
# 添加子主题（需要先 list 获取 parent_id）
python .claude/skills/xmind/xmind_tools.py file.xmind add "新主题" -p <parent_id>

# 修改标题
python .claude/skills/xmind/xmind_tools.py file.xmind update <topic_id> "新标题"

# 删除主题（含子节点）
python .claude/skills/xmind/xmind_tools.py file.xmind delete <topic_id>

# 移动主题到另一个父级下
python .claude/skills/xmind/xmind_tools.py file.xmind move <topic_id> <new_parent_id>

# 添加新 Sheet
python .claude/skills/xmind/xmind_tools.py file.xmind add-sheet "新画布" --root "根主题"
```

## Exporting

```bash
python .claude/skills/xmind/xmind_tools.py file.xmind export -f md     # Markdown
python .claude/skills/xmind/xmind_tools.py file.xmind export -f json   # JSON
python .claude/skills/xmind/xmind_tools.py file.xmind export -f yaml   # YAML
python .claude/skills/xmind/xmind_tools.py file.xmind export -f xml    # XML
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Trying to manually construct XMind JSON/dict in Python | **Don't.** Generate Markdown and use `md_to_xmind.py` instead |
| Using wrong parent ID in edit commands | Run `list` first to see all IDs |
| Deleting rootTopic | Cannot delete root — delete child topics or recreate via markdown |
| Forgetting `--template` on new files | Without template, file has no styles; pass any `.xmind` as `--template` |
| Markdown heading levels skip a level (e.g. ## → ####) | Keep levels contiguous; a skipped level causes the topic to attach to a higher ancestor |

## Implementation Notes

- **Dependency:** `xmindparser` (pip install xmindparser) — required for reading/exporting
- **Conversion:** `md_to_xmind.py` is standalone — no xmindparser needed for markdown→xmind
- **Zen format only:** Write operations target `content.json` (modern XMind). Legacy `content.xml` format is read-only.
- **Encoding:** All files use UTF-8. Topic IDs are auto-generated 26-char hex strings.
