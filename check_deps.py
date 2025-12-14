# -*- coding: utf-8 -*-
"""依赖检查脚本"""
import sys

deps = [
    'shutup',
    'langgraph', 
    'langchain',
    'langchain_openai',
    'langchain_community',
    'langchain_neo4j',
    'graphdatascience',
    'neo4j',
    'hanlp',
    'rich',
]

print('GraphRAG 依赖检查结果:')
print('=' * 40)

missing = []
for dep in deps:
    try:
        __import__(dep.replace('-', '_'))
        print(f'{dep:25} ✓ 已安装')
    except ImportError:
        print(f'{dep:25} ✗ 未安装')
        missing.append(dep)

print('=' * 40)
if missing:
    print(f'缺少 {len(missing)} 个依赖: {", ".join(missing)}')
    print('\n安装命令:')
    print(f'  pip install {" ".join(missing)}')
else:
    print('所有依赖已安装!')
