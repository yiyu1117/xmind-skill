#!/usr/bin/env python3
"""
XMind Tools — 读取、写入和修改 XMind 文件 (.xmind)

使用 xmindparser 库进行读取，使用 zipfile + json 进行写入和修改。
支持 XMind Zen 格式 (content.json) 和旧版 XML 格式 (content.xml)。

依赖: xmindparser (pip install xmindparser)

用法示例:
    # 读取
    data = read_xmind('思维导图.xmind')

    # 列出所有主题
    topics = get_all_topics('思维导图.xmind')

    # 添加子主题
    add_topic('思维导图.xmind', parent_id='xxx', title='新主题')

    # 修改主题标题
    update_topic('思维导图.xmind', topic_id='xxx', new_title='新标题')

    # 删除主题
    delete_topic('思维导图.xmind', topic_id='xxx')

    # 写入新文件
    write_xmind('输出.xmind', data)

    # 导出 Markdown
    md = export_markdown('思维导图.xmind')
"""

import json
import os
import random
import string
import zipfile
from copy import deepcopy
from io import BytesIO
from typing import Optional

import xmindparser

# ============================================================================
# 内部工具函数
# ============================================================================


def _generate_id() -> str:
    """生成类似 XMind 风格的 26 位十六进制 ID。"""
    return ''.join(random.choices('0123456789abcdef', k=26))


def _load_content_json(zf: zipfile.ZipFile) -> list:
    """从已打开的 zip 中读取 content.json 并返回解析后的列表。"""
    with zf.open('content.json') as f:
        return json.loads(f.read().decode('utf-8'))


def _save_content_json(zf: zipfile.ZipFile, data: list):
    """将数据写回 zip 中的 content.json（需要以 'a' 模式打开的 zip）。"""
    # ZipFile 不支持直接更新，我们通过写入 BytesIO 再替换来实现
    pass


def _read_zip(path: str) -> tuple:
    """
    读取 xmind 文件的原始 zip 内容。
    返回 (original_data_dict, is_zen_format) 其中 data_dict 包含所有文件名到 bytes 的映射。
    """
    with zipfile.ZipFile(path, 'r') as zf:
        files = {}
        is_zen = 'content.json' in zf.namelist()
        for name in zf.namelist():
            try:
                files[name] = zf.read(name)
            except Exception:
                files[name] = b''
        return files, is_zen


def _write_zip(path: str, files: dict):
    """将文件字典写入新的 zip 文件。"""
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            if name.endswith('/'):
                continue  # 跳过目录项
            zf.writestr(name, data)


def _find_topic_in_sheet(sheet: dict, topic_id: str):
    """
    在单个 sheet 中递归查找 topic。
    返回 (topic_node, parent_children_list, index_in_parent) 或 (None, None, -1)。
    """
    def search(node, parent_list, idx):
        if node.get('id') == topic_id:
            return node, parent_list, idx
        for child_list_key in ('attached', 'callout', 'summary'):
            children = node.get('children', {}).get(child_list_key, None)
            if children:
                for i, child in enumerate(children):
                    result = search(child, children, i)
                    if result[0] is not None:
                        return result
        return None, None, -1

    root = sheet.get('rootTopic', {})
    return search(root, None, -1)


def _find_topic_in_data(data: list, topic_id: str):
    """
    在所有 sheet 中查找 topic。
    返回 (sheet, topic_node, parent_children_list, index_in_parent) 或 (None, None, None, -1)。
    """
    for sheet in data:
        node, parent_list, idx = _find_topic_in_sheet(sheet, topic_id)
        if node is not None:
            return sheet, node, parent_list, idx
    return None, None, None, -1


def _traverse_topics(node: dict, level: int = 0, sheet_title: str = ''):
    """
    递归遍历所有 topic，生成 (topic_dict, level, sheet_title) 元组。
    """
    yield node, level, sheet_title
    for key in ('attached', 'callout', 'summary'):
        children = node.get('children', {}).get(key, [])
        for child in children:
            yield from _traverse_topics(child, level + 1, sheet_title)


# ============================================================================
# 公共 API — 读取
# ============================================================================


def read_xmind(path: str) -> list:
    """
    读取 xmind 文件，返回结构化的 dict 列表。

    参数:
        path: .xmind 文件路径

    返回:
        list[dict]: 画布列表，每个画布包含 title, topic (递归结构), structure 等字段

    示例:
        >>> data = read_xmind('测试.xmind')
        >>> for sheet in data:
        ...     print(sheet['title'], sheet['topic']['title'])
    """
    return xmindparser.xmind_to_dict(path)


def get_all_topics(path: str) -> list[dict]:
    """
    获取 xmind 文件中所有主题的扁平列表。

    参数:
        path: .xmind 文件路径

    返回:
        list[dict]: 每个主题包含 id, title, level, sheet 字段

    示例:
        >>> topics = get_all_topics('测试.xmind')
        >>> for t in topics:
        ...     print(f"{'  ' * t['level']}{t['title']} (id={t['id']})")
    """
    _, raw_data = _read_raw_content(path)
    result = []
    for sheet in raw_data:
        sheet_title = sheet.get('title', '')
        root = sheet.get('rootTopic', {})
        for topic, level, _ in _traverse_topics(root, 0, sheet_title):
            result.append({
                'id': topic.get('id', ''),
                'title': topic.get('title', ''),
                'level': level,
                'sheet': sheet_title,
            })
    return result


def _read_raw_content(path: str) -> tuple:
    """
    读取 xmind 的原始 content.json 数据。

    返回 (is_zen, raw_data_list)
    """
    with zipfile.ZipFile(path, 'r') as zf:
        if 'content.json' in zf.namelist():
            data = json.loads(zf.read('content.json').decode('utf-8'))
            return True, data
        else:
            return False, []


# ============================================================================
# 公共 API — 修改
# ============================================================================


def add_topic(path: str, parent_id: str, title: str,
              output_path: Optional[str] = None) -> str:
    """
    在指定父主题下添加子主题。

    参数:
        path:       源 .xmind 文件路径
        parent_id:  父主题的 ID
        title:      新主题的标题
        output_path: 输出路径（默认为覆盖原文件）

    返回:
        str: 新创建主题的 ID

    示例:
        >>> new_id = add_topic('测试.xmind', '72982a532f2bd70d2b4c5baa5e', '新主题')
    """
    if output_path is None:
        output_path = path

    files, _ = _read_zip(path)

    # 解析 content.json
    if 'content.json' not in files:
        raise ValueError("不支持的文件格式：缺少 content.json")

    data = json.loads(files['content.json'].decode('utf-8'))

    # 查找父主题
    for sheet in data:
        node, _, _ = _find_topic_in_sheet(sheet, parent_id)
        if node is not None:
            # 确保有 children.attached 结构
            if 'children' not in node:
                node['children'] = {}
            if 'attached' not in node['children']:
                node['children']['attached'] = []

            new_id = _generate_id()
            new_topic = {
                'id': new_id,
                'class': 'topic',
                'title': title,
            }
            node['children']['attached'].append(new_topic)

            # 写回
            files['content.json'] = json.dumps(data, ensure_ascii=False).encode('utf-8')
            _write_zip(output_path, files)
            return new_id

    raise ValueError(f"未找到主题 ID: {parent_id}")


def update_topic(path: str, topic_id: str, new_title: str,
                 output_path: Optional[str] = None):
    """
    修改指定主题的标题。

    参数:
        path:       源 .xmind 文件路径
        topic_id:   要修改的主题 ID
        new_title:  新标题
        output_path: 输出路径（默认为覆盖原文件）

    示例:
        >>> update_topic('测试.xmind', 'a17b17c4d6c8e760647de8b1ab', '修改后的标题')
    """
    if output_path is None:
        output_path = path

    files, _ = _read_zip(path)

    if 'content.json' not in files:
        raise ValueError("不支持的文件格式：缺少 content.json")

    data = json.loads(files['content.json'].decode('utf-8'))

    sheet, node, _, _ = _find_topic_in_data(data, topic_id)
    if node is None:
        raise ValueError(f"未找到主题 ID: {topic_id}")

    node['title'] = new_title
    files['content.json'] = json.dumps(data, ensure_ascii=False).encode('utf-8')
    _write_zip(output_path, files)


def delete_topic(path: str, topic_id: str,
                 output_path: Optional[str] = None):
    """
    删除指定主题及其所有子主题。

    参数:
        path:       源 .xmind 文件路径
        topic_id:   要删除的主题 ID
        output_path: 输出路径（默认为覆盖原文件）

    注意: 不能删除根主题 (rootTopic)

    示例:
        >>> delete_topic('测试.xmind', 'a17b17c4d6c8e760647de8b1ab')
    """
    if output_path is None:
        output_path = path

    files, _ = _read_zip(path)

    if 'content.json' not in files:
        raise ValueError("不支持的文件格式：缺少 content.json")

    data = json.loads(files['content.json'].decode('utf-8'))

    sheet, node, parent_list, idx = _find_topic_in_data(data, topic_id)
    if node is None:
        raise ValueError(f"未找到主题 ID: {topic_id}")

    if parent_list is None:
        raise ValueError("不能删除根主题 (rootTopic)")

    parent_list.pop(idx)
    files['content.json'] = json.dumps(data, ensure_ascii=False).encode('utf-8')
    _write_zip(output_path, files)


def move_topic(path: str, topic_id: str, new_parent_id: str,
               output_path: Optional[str] = None):
    """
    将主题移动到另一个父主题下。

    参数:
        path:          源 .xmind 文件路径
        topic_id:      要移动的主题 ID
        new_parent_id: 新父主题的 ID
        output_path:   输出路径（默认为覆盖原文件）

    示例:
        >>> move_topic('测试.xmind', 'a17b17c4d6c8e760647de8b1ab',
        ...            '74ca001bd8c834a97b15da39c5')
    """
    if output_path is None:
        output_path = path

    files, _ = _read_zip(path)

    if 'content.json' not in files:
        raise ValueError("不支持的文件格式：缺少 content.json")

    data = json.loads(files['content.json'].decode('utf-8'))

    # 找到要移动的主题和它的父级
    _, node, parent_list, idx = _find_topic_in_data(data, topic_id)
    if node is None:
        raise ValueError(f"未找到主题 ID: {topic_id}")
    if parent_list is None:
        raise ValueError("不能移动根主题 (rootTopic)")

    # 找到新父主题
    new_parent_node = None
    for sheet in data:
        new_parent_node, _, _ = _find_topic_in_sheet(sheet, new_parent_id)
        if new_parent_node is not None:
            break

    if new_parent_node is None:
        raise ValueError(f"未找到新父主题 ID: {new_parent_id}")

    # 从原位置移除
    topic_copy = parent_list.pop(idx)

    # 添加到新位置
    if 'children' not in new_parent_node:
        new_parent_node['children'] = {}
    if 'attached' not in new_parent_node['children']:
        new_parent_node['children']['attached'] = []

    new_parent_node['children']['attached'].append(topic_copy)

    files['content.json'] = json.dumps(data, ensure_ascii=False).encode('utf-8')
    _write_zip(output_path, files)


# ============================================================================
# 公共 API — 创建
# ============================================================================


def write_xmind(path: str, data: list, template: Optional[str] = None):
    """
    将结构化数据写入新的 .xmind 文件（Zen 格式）。

    参数:
        path:     输出文件路径
        data:     画布列表，格式与 read_xmind() 返回的一致
        template: 可选，用作模板的 .xmind 文件路径（继承其样式和元数据）

    data 格式示例:
        [{
            "title": "画布 1",
            "topic": {
                "title": "中心主题",
                "topics": [
                    {"title": "子主题 1"},
                    {"title": "子主题 2", "topics": [
                        {"title": "孙主题"}
                    ]}
                ]
            }
        }]

    示例:
        >>> data = [{
        ...     "title": "我的导图",
        ...     "topic": {
        ...         "title": "中心主题",
        ...         "topics": [{"title": "分支 1"}, {"title": "分支 2"}]
        ...     }
        ... }]
        >>> write_xmind('输出.xmind', data)
    """
    # 如果有模板，从模板复制样式
    if template:
        files, _ = _read_zip(template)
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
                    "name": "xmind-tools",
                    "version": "1.0",
                }
            }, ensure_ascii=False).encode('utf-8'),
        }

    # 将简化格式转换为 XMind 完整格式
    content_json = _dict_to_content_json(data)
    files['content.json'] = json.dumps(content_json, ensure_ascii=False).encode('utf-8')

    _write_zip(path, files)


def _dict_to_content_json(data: list) -> list:
    """
    将简化的 dict 格式（来自 read_xmind）转换为 XMind content.json 的完整格式。
    """
    sheets = []
    for sheet_data in data:
        sheet_title = sheet_data.get('title', 'Sheet 1')
        topic_data = sheet_data.get('topic', {})

        sheet = {
            'id': _generate_id(),
            'class': 'sheet',
            'title': sheet_title,
            'rootTopic': _build_topic(topic_data),
            'theme': {},
        }
        sheets.append(sheet)
    return sheets


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

    # 保留备注
    if 'note' in topic_data:
        topic['notes'] = {
            'plain': {
                'content': topic_data['note'],
            }
        }

    # 保留标签
    if 'labels' in topic_data and topic_data['labels']:
        topic['labels'] = topic_data['labels']

    return topic


def add_sheet(path: str, sheet_title: str, root_title: str = '中心主题',
              output_path: Optional[str] = None):
    """
    在已有 xmind 文件中添加新画布。

    参数:
        path:       源 .xmind 文件路径
        sheet_title: 画布标题
        root_title:  画布根主题标题
        output_path: 输出路径（默认为覆盖原文件）

    示例:
        >>> add_sheet('测试.xmind', '新画布', '新中心主题')
    """
    if output_path is None:
        output_path = path

    files, _ = _read_zip(path)

    if 'content.json' not in files:
        raise ValueError("不支持的文件格式：缺少 content.json")

    data = json.loads(files['content.json'].decode('utf-8'))

    new_sheet = {
        'id': _generate_id(),
        'class': 'sheet',
        'title': sheet_title,
        'rootTopic': {
            'id': _generate_id(),
            'class': 'topic',
            'title': root_title,
        },
        'theme': {},
    }
    data.append(new_sheet)

    files['content.json'] = json.dumps(data, ensure_ascii=False).encode('utf-8')
    _write_zip(output_path, files)


# ============================================================================
# 公共 API — 导出
# ============================================================================


def export_markdown(path: str) -> str:
    """
    将 xmind 文件导出为 Markdown 格式字符串。

    参数:
        path: .xmind 文件路径

    返回:
        str: Markdown 格式内容

    示例:
        >>> md = export_markdown('测试.xmind')
        >>> print(md)
        >>> with open('输出.md', 'w', encoding='utf-8') as f:
        ...     f.write(md)
    """
    return xmindparser.xmind_to_markdown(path)


def export_json(path: str, output_path: Optional[str] = None) -> str:
    """导出为 JSON 字符串。如果指定 output_path 则写入文件。"""
    json_str = xmindparser.xmind_to_json(path)
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_str)
    return json_str


def export_yaml(path: str) -> str:
    """导出为 YAML 字符串。"""
    return xmindparser.xmind_to_yaml(path)


def export_xml(path: str) -> str:
    """导出为 XML 字符串。"""
    return xmindparser.xmind_to_xml(path)


# ============================================================================
# CLI 入口
# ============================================================================


def _cli():
    """命令行接口。"""
    import argparse

    parser = argparse.ArgumentParser(
        description='XMind Tools — 读取、写入和修改 XMind 文件 (.xmind)',
    )
    parser.add_argument('path', help='.xmind 文件路径')
    parser.add_argument('--output', '-o', help='输出文件路径（默认覆盖原文件）')

    subparsers = parser.add_subparsers(dest='action', help='操作')

    # read
    subparsers.add_parser('read', help='读取并打印 xmind 结构')

    # list
    subparsers.add_parser('list', help='列出所有主题')

    # add
    add_parser = subparsers.add_parser('add', help='添加子主题')
    add_parser.add_argument('title', help='新主题标题')
    add_parser.add_argument('--parent', '-p', required=True, help='父主题 ID')

    # update
    update_parser = subparsers.add_parser('update', help='修改主题标题')
    update_parser.add_argument('topic_id', help='要修改的主题 ID')
    update_parser.add_argument('title', help='新标题')

    # delete
    delete_parser = subparsers.add_parser('delete', help='删除主题')
    delete_parser.add_argument('topic_id', help='要删除的主题 ID')

    # move
    move_parser = subparsers.add_parser('move', help='移动主题')
    move_parser.add_argument('topic_id', help='要移动的主题 ID')
    move_parser.add_argument('new_parent', help='新父主题 ID')

    # add-sheet
    add_sheet_parser = subparsers.add_parser('add-sheet', help='添加画布')
    add_sheet_parser.add_argument('title', help='画布标题')
    add_sheet_parser.add_argument('--root', default='中心主题', help='根主题标题')

    # export
    export_parser = subparsers.add_parser('export', help='导出为 Markdown')
    export_parser.add_argument('--format', '-f', default='md',
                               choices=['md', 'json', 'yaml', 'xml'])

    # create
    create_parser = subparsers.add_parser('create', help='从 JSON 数据创建 xmind')
    create_parser.add_argument('json_file', help='包含画布数据的 JSON 文件')
    create_parser.add_argument('--template', '-t', help='模板 .xmind 文件')

    args = parser.parse_args()

    try:
        if args.action == 'read':
            data = read_xmind(args.path)
            print(json.dumps(data, indent=2, ensure_ascii=False))

        elif args.action == 'list':
            topics = get_all_topics(args.path)
            for t in topics:
                prefix = '  ' * t['level'] + ('├─ ' if t['level'] > 0 else '')
                print(f"{prefix}{t['title']}  [id={t['id']}]")

        elif args.action == 'add':
            new_id = add_topic(args.path, args.parent, args.title, args.output)
            print(f"已添加主题，ID: {new_id}")

        elif args.action == 'update':
            update_topic(args.path, args.topic_id, args.title, args.output)
            print(f"已更新主题 {args.topic_id}")

        elif args.action == 'delete':
            delete_topic(args.path, args.topic_id, args.output)
            print(f"已删除主题 {args.topic_id}")

        elif args.action == 'move':
            move_topic(args.path, args.topic_id, args.new_parent, args.output)
            print(f"已将主题 {args.topic_id} 移动到 {args.new_parent} 下")

        elif args.action == 'add-sheet':
            add_sheet(args.path, args.title, args.root, args.output)
            print(f"已添加画布: {args.title}")

        elif args.action == 'export':
            if args.format == 'md':
                print(export_markdown(args.path))
            elif args.format == 'json':
                print(export_json(args.path, args.output))
            elif args.format == 'yaml':
                print(export_yaml(args.path))
            elif args.format == 'xml':
                print(export_xml(args.path))

        elif args.action == 'create':
            with open(args.json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            output = args.output or args.path
            write_xmind(output, data, args.template)
            print(f"已创建: {output}")

        else:
            parser.print_help()

    except Exception as e:
        print(f"错误: {e}", file=__import__('sys').stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    _cli()
