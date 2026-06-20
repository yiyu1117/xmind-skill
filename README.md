# XMind Skill — Claude Code XMind 文件操作技能

一个 Claude Code 技能，用于读取、创建和修改 XMind 思维导图文件（`.xmind`）。

**核心理念：AI 生成 Markdown，脚本转 .xmind。**

## 功能

- **创建** — 从 Markdown 一键生成 .xmind 思维导图
- **读取** — 解析 `.xmind` 为结构化数据或树形列表
- **修改** — 增/删/改/移动主题
- **画布管理** — 添加多个 Sheet 画布
- **导出** — 导出为 Markdown / JSON / YAML / XML

## 文件结构

```
.claude/skills/xmind/
├── SKILL.md           # 技能文档（AI 行为指南）
├── md_to_xmind.py     # Markdown → XMind 转换器（⭐ 核心）
└── xmind_tools.py     # 读取/修改/导出工具
```

## 快速开始

### 前提

```bash
pip install xmindparser
```

### 创建思维导图（Markdown → XMind）

```bash
# 1. 编写 Markdown
cat > 思维导图.md << 'EOF'
# Python 学习路线

## 基础语法
打好基础是关键。

### 变量与类型
### 控制流
### 函数与模块

## 面向对象
### 类与实例
### 继承与多态

## 常用库
### pandas
### flask
EOF

# 2. 转换为 .xmind
python .claude/skills/xmind/md_to_xmind.py 思维导图.md 输出.xmind

# 3. 带样式模板
python .claude/skills/xmind/md_to_xmind.py 思维导图.md 输出.xmind --template 模板.xmind
```

### 读取和修改已有文件

```bash
# 列出所有主题及 ID
python .claude/skills/xmind/xmind_tools.py 文件.xmind list

# 添加/修改/删除主题
python .claude/skills/xmind/xmind_tools.py 文件.xmind add "新主题" -p <父主题ID>
python .claude/skills/xmind/xmind_tools.py 文件.xmind update <主题ID> "新标题"
python .claude/skills/xmind/xmind_tools.py 文件.xmind delete <主题ID>
```

### 导出

```bash
python .claude/skills/xmind/xmind_tools.py 文件.xmind export -f md   # Markdown
```

## Markdown 格式约定

```
# 根主题（Sheet 标题）

## 一级分支
可选备注文本。

### 二级分支
#### 三级分支

## 另一个一级分支

# 第二个 Sheet  ← 新的 # 创建新画布
```

- `#` = Sheet 根主题，`##` = 一级子节点，`###` = 二级子节点...
- 标题间文本 = 该主题的备注
- 多个 `#` = 多个画布

## 技术原理

XMind 文件本质上是 ZIP 压缩包，其中 `content.json` 存储画布和主题树。

- **创建**：`md_to_xmind.py` 解析 Markdown 标题层级 → 生成 `content.json` → 打包为 `.xmind`
- **读取/导出**：使用 [xmindparser](https://pypi.org/project/xmindparser/)
- **修改**：直接操作 ZIP 内的 `content.json`，保持元数据完整
