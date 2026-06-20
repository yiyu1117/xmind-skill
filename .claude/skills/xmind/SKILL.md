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

### CRITICAL: Use Headings ONLY

**XMind 的"正文/备注"需要点击图标才能看到，默认是隐藏的。因此 Markdown 中所有内容必须用标题（`#`）表示，不要用列表或段落 — 这样 XMind 中所有节点都直接可见。**

```markdown
# 根主题

## 一级分支 A
### 分支 A 的说明点 1
### 分支 A 的说明点 2

## 一级分支 B
### 分支 B 的子点
#### 更细的细节
```

**规则：**
- 每一行都以 `#` 开头 — 没有例外
- 需要表达多句话 → 拆成多个 `###` 子标题
- 列表要点 → 每个要点一个 `###` 或 `####`
- 绝不用 `- item` 列表或正文段落
- 除非用户明确说「备注」「正文」，才可以用正文 + `--keep-notes`

### AI Workflow

1. **输出 Markdown 给用户确认** — 纯标题，无列表/正文
2. **写入 `.md` 文件**
3. **转换：**
   ```bash
   python .claude/skills/xmind/md_to_xmind.py input.md output.xmind --template existing.xmind
   ```

### 格式速查

| Markdown | XMind 中 |
|----------|----------|
| `# 标题` | 新 Sheet（根主题）。多个 `#` = 多个 Sheet |
| `## 标题` | 根主题的直接子节点 |
| `### 标题` | 父标题的子节点 |
| `#### 标题` | 更深层级 |
| 正文 / `- list` | **默认转为子主题**（每行一个），XMind 中直接可见 |
| 正文 + `--keep-notes` | 正文作为备注（隐藏，需点图标） ← 仅用户明确要求时使用 |

### 带模板创建

```bash
python .claude/skills/xmind/md_to_xmind.py input.md output.xmind --template existing.xmind
```

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
