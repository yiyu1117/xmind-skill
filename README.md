# XMind Skill — Claude Code XMind 文件操作技能

一个 Claude Code 技能，用于读取、创建和修改 XMind 思维导图文件（`.xmind`）。

## 功能

- **读取** — 解析 `.xmind` 文件为结构化数据
- **创建** — 从 JSON 数据新建思维导图
- **修改** — 增/删/改/移动主题
- **画布管理** — 添加多个 Sheet 画布
- **导出** — 导出为 Markdown / JSON / YAML / XML

## 文件结构

```
.claude/skills/xmind/
├── SKILL.md           # 技能文档（触发条件、API 参考、常见错误）
└── xmind_tools.py     # Python 工具脚本（读、写、增、删、改）
```

## 快速开始

### 前提

```bash
pip install xmindparser
```

### 使用

```bash
# 列出所有主题及 ID
python .claude/skills/xmind/xmind_tools.py 文件.xmind list

# 添加子主题
python .claude/skills/xmind/xmind_tools.py 文件.xmind add "新主题" -p <父主题ID>

# 修改主题标题
python .claude/skills/xmind/xmind_tools.py 文件.xmind update <主题ID> "新标题"

# 删除主题
python .claude/skills/xmind/xmind_tools.py 文件.xmind delete <主题ID>

# 创建新文件
python .claude/skills/xmind/xmind_tools.py 输出.xmind create data.json

# 导出 Markdown
python .claude/skills/xmind/xmind_tools.py 文件.xmind export -f md
```

也支持在 Python 代码中导入使用：

```python
from xmind_tools import *

data = read_xmind('文件.xmind')
new_id = add_topic('文件.xmind', parent_id='...', title='新主题')
```

## 技术原理

XMind 文件本质上是 ZIP 压缩包，其中 `content.json` 以 JSON 格式存储画布和主题树结构。

- **读取**：使用 [xmindparser](https://pypi.org/project/xmindparser/) 库
- **写入/修改**：直接操作 ZIP 内的 `content.json`，保持元数据、缩略图等文件完整
- **支持格式**：XMind Zen 格式（`content.json`）
