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

    标题之间的正文/列表      → 默认转为该主题的子节点（XMind 中直接可见）
    --keep-notes             → 正文作为备注（需点图标才能看到）

用法:
    python md_to_xmind.py input.md output.xmind
    python md_to_xmind.py input.md output.xmind --template base.xmind
    python md_to_xmind.py input.md output.xmind --keep-notes  # 正文→备注
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


def parse_markdown(text: str, keep_notes: bool = False) -> list[dict]:
    """
    解析 Markdown 文本为 sheet 列表。

    参数:
        text: Markdown 字符串
        keep_notes: False（默认）= 正文行转为子主题（XMind 中直接可见）
                    True = 正文行保留为备注（需点击图标查看）

    返回:
        list[dict]: sheet 列表
    """
    sheets = []
    current_sheet = None
    topic_stack = []          # [(heading_level, topic_dict)]
    pending_lines = []        # 收集当前主题下的正文行
    heading_level_for_lines = 0  # 正文行应作为哪个层级的子主题

    def flush_pending():
        """将收集的正文行写入栈顶主题。"""
        nonlocal pending_lines
        if pending_lines and topic_stack:
            text = '\n'.join(pending_lines).strip()
            if text:
                parent = topic_stack[-1][1]
                if keep_notes:
                    # 正文 → 备注（需点图标）
                    parent['note'] = text
                else:
                    # 正文 → 子主题（直接可见），每行一个子主题
                    if 'topics' not in parent:
                        parent['topics'] = []
                    for line_text in pending_lines:
                        line_text = line_text.strip()
                        if not line_text:
                            continue
                        # 去掉列表前缀: - item, * item, 1. item
                        clean = line_text
                        for prefix in ('- ', '* ', '+ '):
                            if clean.startswith(prefix):
                                clean = clean[len(prefix):]
                                break
                        else:
                            # 有序列表: 1. , 1)
                            import re
                            m = re.match(r'^\d+[.)]\s*', clean)
                            if m:
                                clean = clean[m.end():]
                        if clean:
                            parent['topics'].append({'title': clean, 'topics': []})
        pending_lines = []

    for raw_line in text.split('\n'):
        line = raw_line.rstrip()

        # 跳过空行和分隔符
        if not line or line.strip() == '---':
            continue

        # 标题行
        if line.startswith('#'):
            level = 0
            for ch in line:
                if ch == '#':
                    level += 1
                else:
                    break

            title = line[level:].strip()
            if not title:
                continue

            flush_pending()

            if level == 1:
                topic = {'title': title, 'topics': []}
                current_sheet = {'title': title, 'topic': topic}
                sheets.append(current_sheet)
                topic_stack = [(1, topic)]

            elif current_sheet is not None:
                while topic_stack and topic_stack[-1][0] >= level:
                    topic_stack.pop()

                if topic_stack:
                    parent = topic_stack[-1][1]
                    if 'topics' not in parent:
                        parent['topics'] = []
                    new_topic = {'title': title, 'topics': []}
                    parent['topics'].append(new_topic)
                    topic_stack.append((level, new_topic))
            else:
                topic = {'title': title, 'topics': []}
                current_sheet = {'title': title, 'topic': topic}
                sheets.append(current_sheet)
                topic_stack = [(2, topic)]

        else:
            # 非标题行 → 收集
            pending_lines.append(line)

    flush_pending()

    # 去除空的 topics 列表和空的 note
    def clean_topic(t):
        if 'topics' in t and not t['topics']:
            del t['topics']
        if 'note' in t and not t['note']:
            del t['note']
        if 'topics' in t:
            for child in t['topics']:
                clean_topic(child)

    for sheet in sheets:
        clean_topic(sheet['topic'])

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


def md_to_xmind(md_path: str, xmind_path: str, template: Optional[str] = None,
                keep_notes: bool = False):
    """
    将 Markdown 文件转换为 .xmind 思维导图文件。

    参数:
        md_path:    输入 .md 文件路径
        xmind_path: 输出 .xmind 文件路径
        template:   可选模板 .xmind 文件（继承其样式和元数据）
        keep_notes: False（默认）= 正文行转为子主题，XMind 中直接可见
                    True = 正文行保留为备注，需点击图标查看

    示例:
        >>> md_to_xmind('思维导图.md', '输出.xmind')
        >>> md_to_xmind('思维导图.md', '输出.xmind', template='模板.xmind')
        >>> md_to_xmind('思维导图.md', '输出.xmind', keep_notes=True)
    """
    # 读取并解析 Markdown
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    sheets = parse_markdown(md_text, keep_notes=keep_notes)

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
    parser.add_argument('--keep-notes', action='store_true',
                        help='正文行保留为备注（默认转为子主题）')

    args = parser.parse_args()

    try:
        md_to_xmind(args.input, args.output, args.template, args.keep_notes)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
