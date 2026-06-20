#!/usr/bin/env python3
"""
Markdown → XMind 转换器

将 Markdown 标题层级结构转换为 .xmind 思维导图文件。
AI 只需生成 Markdown，本脚本自动处理 XMind 内部格式。

Markdown 格式约定:
    # 中心主题               ← Sheet 的根主题（每个 # 开一个新 Sheet）
    ## 一级分支               ← 根主题的直接子节点
    ### 二级分支              ← 上一个 ## 的子节点
    #### 三级分支             ← 上一个 ### 的子节点
    ## 另一个一级分支
    ---                      ← 可选分隔符

    标题之间的段落/列表文本  → 作为该主题的备注 (note)

用法:
    python md_to_xmind.py input.md output.xmind
    python md_to_xmind.py input.md output.xmind --template base.xmind
"""

import json
import random
import sys
import zipfile
from pathlib import Path
from typing import Optional


# ============================================================================
# Markdown 解析
# ============================================================================


def parse_markdown(text: str) -> list[dict]:
    """
    解析 Markdown 文本为 sheet 列表。

    参数:
        text: Markdown 字符串

    返回:
        list[dict]: sheet 列表，每个 sheet 格式为:
            {
                'title': 'Sheet标题',
                'topic': {
                    'title': '根主题',
                    'topics': [...],   # 子主题列表（递归）
                    'note': '...',     # 备注文本（可选）
                }
            }
    """
    sheets = []
    current_sheet = None
    topic_stack = []       # [(heading_level, topic_dict)]
    pending_note_lines = []  # 收集当前主题下的备注文本
    last_heading_level = 0

    def flush_note():
        """将收集的备注文本写入栈顶主题。"""
        nonlocal pending_note_lines
        if pending_note_lines and topic_stack:
            note_text = '\n'.join(pending_note_lines).strip()
            if note_text:
                topic_stack[-1][1]['note'] = note_text
        pending_note_lines = []

    for raw_line in text.split('\n'):
        line = raw_line.rstrip()

        # 跳过空行
        if not line:
            continue

        # 跳过分隔符
        if line.strip() == '---':
            continue

        # 标题行
        if line.startswith('#'):
            # 计算标题级别
            level = 0
            for ch in line:
                if ch == '#':
                    level += 1
                else:
                    break

            title = line[level:].strip()
            if not title:
                continue

            flush_note()

            if level == 1:
                # 新 Sheet
                topic = {'title': title, 'topics': []}
                current_sheet = {'title': title, 'topic': topic}
                sheets.append(current_sheet)
                topic_stack = [(1, topic)]
                last_heading_level = 1

            elif current_sheet is not None:
                # 找父级：栈中最后一个 level 严格小于当前 level 的 topic
                while topic_stack and topic_stack[-1][0] >= level:
                    topic_stack.pop()

                if topic_stack:
                    parent = topic_stack[-1][1]
                    if 'topics' not in parent:
                        parent['topics'] = []
                    new_topic = {'title': title, 'topics': []}
                    parent['topics'].append(new_topic)
                    topic_stack.append((level, new_topic))
                    last_heading_level = level
            else:
                # 第一个标题不是 #，也作为一个 sheet 处理
                topic = {'title': title, 'topics': []}
                current_sheet = {'title': title, 'topic': topic}
                sheets.append(current_sheet)
                topic_stack = [(2, topic)]  # 当作 level=2 处理，这样后续 ### 等能正常挂载
                last_heading_level = 2

        else:
            # 非标题行 → 收集为备注
            pending_note_lines.append(line)

    flush_note()

    # 去除空的 topics 列表
    def clean_topics(topic):
        if 'topics' in topic and not topic['topics']:
            del topic['topics']
        if 'topics' in topic:
            for child in topic['topics']:
                clean_topics(child)

    for sheet in sheets:
        clean_topics(sheet['topic'])

    return sheets


# ============================================================================
# XMind 文件生成
# ============================================================================


def _generate_id() -> str:
    """生成 26 位十六进制 ID，与 XMind 格式一致。"""
    return ''.join(random.choices('0123456789abcdef', k=26))


def _build_topic(topic_data: dict) -> dict:
    """将简化格式的 topic dict 转换为完整的 XMind topic 结构。"""
    topic = {
        'id': _generate_id(),
        'class': 'topic',
        'title': topic_data.get('title', ''),
    }

    children = topic_data.get('topics', [])
    if children:
        attached = []
        for child_data in children:
            attached.append(_build_topic(child_data))
        topic['children'] = {'attached': attached}

    if 'note' in topic_data:
        topic['notes'] = {
            'plain': {
                'content': topic_data['note'],
            }
        }

    if 'labels' in topic_data and topic_data['labels']:
        topic['labels'] = topic_data['labels']

    return topic


def _sheets_to_content_json(sheets: list) -> list:
    """将 sheet 列表转换为 XMind content.json 格式。"""
    result = []
    for sheet_data in sheets:
        sheet = {
            'id': _generate_id(),
            'class': 'sheet',
            'title': sheet_data.get('title', 'Sheet 1'),
            'rootTopic': _build_topic(sheet_data.get('topic', {})),
            'theme': {},
        }
        result.append(sheet)
    return result


def _read_zip(path: str) -> dict:
    """读取 zip 文件的所有内容。返回 {filename: bytes}。"""
    files = {}
    with zipfile.ZipFile(path, 'r') as zf:
        for name in zf.namelist():
            try:
                files[name] = zf.read(name)
            except Exception:
                files[name] = b''
    return files


def _write_zip(path: str, files: dict):
    """将文件字典写入 zip 文件。"""
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            if name.endswith('/'):
                continue
            zf.writestr(name, data)


def md_to_xmind(md_path: str, xmind_path: str, template: Optional[str] = None):
    """
    将 Markdown 文件转换为 .xmind 思维导图文件。

    参数:
        md_path:   输入 .md 文件路径
        xmind_path: 输出 .xmind 文件路径
        template:  可选模板 .xmind 文件（继承其样式和元数据）

    示例:
        >>> md_to_xmind('思维导图.md', '输出.xmind')
        >>> md_to_xmind('思维导图.md', '输出.xmind', template='模板.xmind')
    """
    # 读取并解析 Markdown
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    sheets = parse_markdown(md_text)

    if not sheets:
        raise ValueError("Markdown 文件中未找到任何标题")

    # 生成 content.json
    content_json = _sheets_to_content_json(sheets)

    # 构建 zip 内容
    if template:
        files = _read_zip(template)
    else:
        files = {
            'manifest.json': json.dumps({
                "file-entries": {
                    "content.json": {},
                    "metadata.json": {},
                }
            }, ensure_ascii=False).encode('utf-8'),
            'metadata.json': json.dumps({
                "creator": {
                    "name": "xmind-skill",
                    "version": "2.0",
                }
            }, ensure_ascii=False).encode('utf-8'),
        }

    files['content.json'] = json.dumps(content_json, ensure_ascii=False).encode('utf-8')

    _write_zip(xmind_path, files)

    # 统计
    total_topics = 0
    for sheet in sheets:
        def count(t):
            nonlocal total_topics
            total_topics += 1
            for child in t.get('topics', []):
                count(child)
        count(sheet['topic'])

    print(f"Done: {xmind_path}")
    print(f"  {len(sheets)} sheet(s), {total_topics} topic(s)")


# ============================================================================
# CLI 入口
# ============================================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Markdown → XMind 转换器',
        epilog='示例: python md_to_xmind.py input.md output.xmind --template base.xmind',
    )
    parser.add_argument('input', help='输入的 .md 文件路径')
    parser.add_argument('output', help='输出的 .xmind 文件路径')
    parser.add_argument('--template', '-t', help='模板 .xmind 文件（继承样式）')

    args = parser.parse_args()

    try:
        md_to_xmind(args.input, args.output, args.template)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
