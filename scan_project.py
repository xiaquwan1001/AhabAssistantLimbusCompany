#!/usr/bin/env python3
"""
智能工程文件夹扫描工具
- 自动从脚本所在目录开始扫描
- 支持JSON输出
- 支持自定义深度
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import argparse

class ProjectScanner:
    def __init__(self, root_path, max_depth=None):
        self.root_path = Path(root_path).resolve()
        self.max_depth = max_depth
        self.stats = {
            'project_root': str(self.root_path),
            'scan_time': datetime.now().isoformat(),
            'total_files': 0,
            'total_dirs': 0,
            'file_types': defaultdict(int),
            'total_size': 0,
            'tree': [],
            'files': []
        }
    
    def scan(self, path=None, relative_path="", current_depth=0):
        """扫描文件夹"""
        if path is None:
            path = self.root_path
        
        # 检查深度限制
        if self.max_depth is not None and current_depth > self.max_depth:
            return None
        
        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            # 过滤隐藏文件和常见不需要的目录
            items = [item for item in items if not item.name.startswith('.') 
                    and item.name not in ['node_modules', '__pycache__', '.git', 'venv', 'env', '.venv']]
        except PermissionError:
            return None
        
        tree_node = {
            'name': path.name if relative_path else self.root_path.name,
            'path': str(path),
            'type': 'directory',
            'children': [],
            'size': 0,
            'file_count': 0,
            'dir_count': 0
        }
        
        for item in items:
            if item.is_dir():
                self.stats['total_dirs'] += 1
                child = self.scan(item, 
                                  relative_path + item.name + "/", 
                                  current_depth + 1)
                if child:
                    tree_node['children'].append(child)
                    tree_node['dir_count'] += 1 + child.get('dir_count', 0)
                    tree_node['file_count'] += child.get('file_count', 0)
                    tree_node['size'] += child.get('size', 0)
            else:
                self.stats['total_files'] += 1
                size = item.stat().st_size
                self.stats['total_size'] += size
                
                ext = item.suffix.lower() or 'no_extension'
                self.stats['file_types'][ext] += 1
                
                file_info = {
                    'name': item.name,
                    'path': str(item.relative_to(self.root_path)),
                    'size': size,
                    'size_formatted': self.format_size(size),
                    'extension': ext,
                    'type': 'file'
                }
                self.stats['files'].append(file_info)
                
                tree_node['children'].append(file_info)
                tree_node['file_count'] += 1
                tree_node['size'] += size
        
        # 排序：目录在前，文件在后
        tree_node['children'].sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))
        
        return tree_node
    
    @staticmethod
    def format_size(bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.2f}{unit}"
            bytes /= 1024.0
        return f"{bytes:.2f}TB"
    
    def get_summary(self):
        """获取统计摘要"""
        return {
            'project_root': self.stats['project_root'],
            'scan_time': self.stats['scan_time'],
            'total_files': self.stats['total_files'],
            'total_dirs': self.stats['total_dirs'],
            'total_size': self.stats['total_size'],
            'total_size_formatted': self.format_size(self.stats['total_size']),
            'file_types': dict(self.stats['file_types'])
        }
    
    def find_large_files(self, min_size_mb=10):
        """查找大文件"""
        large = []
        for f in self.stats['files']:
            size_mb = f['size'] / (1024 * 1024)
            if size_mb >= min_size_mb:
                large.append(f)
        return sorted(large, key=lambda x: x['size'], reverse=True)
    
    def to_json(self, include_files=False, include_tree=True, indent=2):
        """导出为JSON格式"""
        result = {
            'summary': self.get_summary()
        }
        
        if include_tree:
            result['tree'] = self.stats['tree']
        
        if include_files:
            result['files'] = self.stats['files']
        
        return json.dumps(result, indent=indent, ensure_ascii=False)
    
    def scan_complete(self):
        """完成扫描，构建树"""
        self.stats['tree'] = [self.scan()]

def main():
    # 获取脚本所在目录（自动从根目录开始）
    script_dir = Path(__file__).parent.resolve()
    
    parser = argparse.ArgumentParser(description='智能工程文件夹扫描工具')
    parser.add_argument('-d', '--depth', type=int, default=None, 
                       help='扫描深度限制（默认：无限制）')
    parser.add_argument('-j', '--json', action='store_true',
                       help='输出JSON格式')
    parser.add_argument('-o', '--output', type=str,
                       help='输出到文件（默认：标准输出）')
    parser.add_argument('-l', '--large', type=int, default=0,
                       help='查找大于指定MB的文件')
    parser.add_argument('--no-tree', action='store_true',
                       help='不包含树形结构（仅JSON模式）')
    parser.add_argument('--no-files', action='store_true',
                       help='不包含文件列表（仅JSON模式）')
    parser.add_argument('path', nargs='?', default=None,
                       help='要扫描的路径（默认：脚本所在目录）')
    
    args = parser.parse_args()
    
    # 确定扫描路径
    if args.path:
        scan_path = Path(args.path).resolve()
    else:
        scan_path = script_dir  # 默认：脚本所在目录
    
    print(f"📁 脚本位置: {script_dir}")
    print(f"📂 扫描目录: {scan_path}")
    print("=" * 70)
    
    # 创建扫描器
    scanner = ProjectScanner(scan_path, max_depth=args.depth)
    
    # 执行扫描
    print("🔄 扫描中...")
    scanner.scan_complete()
    
    # 处理输出
    if args.json:
        # JSON输出模式
        json_data = scanner.to_json(
            include_files=not args.no_files,
            include_tree=not args.no_tree
        )
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_data)
            print(f"✅ JSON数据已保存到: {args.output}")
        else:
            print(json_data)
    else:
        # 文本输出模式
        summary = scanner.get_summary()
        print("\n📊 项目统计:")
        print(f"  总文件数: {summary['total_files']}")
        print(f"  总文件夹数: {summary['total_dirs']}")
        print(f"  总大小: {summary['total_size_formatted']}")
        
        # 显示文件类型TOP10
        print("\n📈 文件类型分布:")
        sorted_types = sorted(summary['file_types'].items(), 
                            key=lambda x: x[1], reverse=True)
        for ext, count in sorted_types[:10]:
            percentage = (count / summary['total_files']) * 100 if summary['total_files'] > 0 else 0
            print(f"  {ext}: {count} 个 ({percentage:.1f}%)")
        
        # 查找大文件
        if args.large > 0:
            large_files = scanner.find_large_files(args.large)
            if large_files:
                print(f"\n💾 大文件 (>{args.large}MB) TOP 10:")
                for f in large_files[:10]:
                    print(f"  📄 {f['path']} ({f['size_formatted']})")
            else:
                print(f"\n✅ 没有找到大于 {args.large}MB 的文件")
        
        # 显示目录树（简化版）
        print("\n🌳 目录结构 (前3层):")
        print_tree_simple(scan_path, max_depth=3)

def print_tree_simple(path, prefix="", max_depth=3, current_depth=0):
    """简单树形显示"""
    if current_depth > max_depth:
        print(f"{prefix}└── ... (更深层级)")
        return
    
    path = Path(path)
    if not path.exists():
        return
    
    try:
        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        items = [item for item in items if not item.name.startswith('.') 
                and item.name not in ['node_modules', '__pycache__', '.git']]
    except PermissionError:
        return
    
    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└── " if is_last else "├── "
        
        if item.is_dir():
            print(f"{prefix}{connector}📁 {item.name}/")
            extension = "    " if is_last else "│   "
            print_tree_simple(item, prefix + extension, max_depth, current_depth + 1)
        else:
            size = ProjectScanner.format_size(item.stat().st_size)
            print(f"{prefix}{connector}📄 {item.name} ({size})")

if __name__ == "__main__":
    main()