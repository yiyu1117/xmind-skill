---
name: xmind
description: Use when the user wants to read, create, edit, or manipulate XMind mind map files (.xmind) — including adding/updating/deleting topics, moving topics between parents, adding sheets, or exporting to Markdown/JSON/YAML/XML.
---

# XMind File Operations

## Overview

Read, create, and modify XMind mind map files (.xmind). Uses `xmindparser` for reading/exporting and `xmind_tools.py` for writing and editing. XMind files are ZIP archives containing `content.json` (Zen format) or `content.xml` (legacy format).

## When to Use

- Reading or exploring `.xmind` file structure
- Creating new mind maps programmatically
- Adding, renaming, or deleting topics
- Moving topics between branches
- Adding new sheets (canvases)
- Exporting to Markdown, JSON, YAML, or XML

## Quick Reference

### Reading

```python
# Full structure (sheets → topics tree)
data = read_xmind('file.xmind')

# Flat list of all topics with IDs
topics = get_all_topics('file.xmind')
# → [{'id': '...', 'title': '...', 'level': 0, 'sheet': '...'}, ...]
```

### Modifying (modifies file in-place by default; use `output_path` to save a copy)

```python
# Add child topic — returns new topic ID
new_id = add_topic('file.xmind', parent_id='...', title='New Topic')

# Update topic title
update_topic('file.xmind', topic_id='...', new_title='Renamed')

# Delete topic and all its children
delete_topic('file.xmind', topic_id='...')

# Move topic to a different parent
move_topic('file.xmind', topic_id='...', new_parent_id='...')

# Add a new sheet
add_sheet('file.xmind', sheet_title='Sheet 2', root_title='Center')
```

### Creating

```python
data = [{
    'title': 'Sheet 1',
    'topic': {
        'title': 'Root',
        'topics': [
            {'title': 'Child 1'},
            {'title': 'Child 2', 'topics': [
                {'title': 'Grandchild'}
            ]}
        ]
    }
}]
write_xmind('output.xmind', data, template='existing.xmind')  # template inherits styles
```

### Exporting

```python
md  = export_markdown('file.xmind')   # → str
json_str = export_json('file.xmind')   # → str
yaml_str = export_yaml('file.xmind')   # → str
xml_str  = export_xml('file.xmind')    # → str
```

### CLI

```bash
python xmind_tools.py file.xmind list              # 列出所有主题及 ID
python xmind_tools.py file.xmind read              # 打印完整结构
python xmind_tools.py file.xmind add "新主题" -p <parent_id>
python xmind_tools.py file.xmind update <topic_id> "新标题"
python xmind_tools.py file.xmind delete <topic_id>
python xmind_tools.py file.xmind move <topic_id> <new_parent_id>
python xmind_tools.py file.xmind add-sheet "新画布"
python xmind_tools.py file.xmind export -f md       # Markdown
python xmind_tools.py file.xmind create data.json -t template.xmind
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Passing wrong parent ID to `add_topic` | Use `get_all_topics()` first to list all valid IDs |
| Trying to delete rootTopic | Root topic cannot be deleted — delete child topics instead |
| Overwriting file unintentionally | Pass `output_path='copy.xmind'` to save a copy instead |
| Forgetting `ensure_ascii=False` when reading JSON manually | xmind_tools.py handles encoding internally — use the API |
| Using `add_topic` without `output_path` | This modifies the original file — back up first if needed |

## Implementation Notes

- **Zen format** (`content.json`): Modern XMind, uses JSON. Primary target.
- **Legacy format** (`content.xml`): Older XMind. Reading supported via xmindparser; writing not supported.
- `xmindparser` is **read-only**. All write/edit operations use `xmind_tools.py` which directly manipulates `content.json` inside the ZIP archive.
- Topic IDs are 26-char hex strings. New IDs are auto-generated in the same format.
- When creating files with `write_xmind()`, pass a `template` to inherit theme/stylesheet. Without a template, a minimal default is used.
