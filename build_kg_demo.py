"""
GraphRAG 知识图谱构建脚本 - 使用 AI 助手模拟 LLM API

本脚本演示如何使用 AI 编程助手（Codex）来模拟 LLM API，
从华东理工大学规章制度文档中提取实体和关系，构建知识图谱。

运行步骤：
1. 读取文档
2. 文本分块
3. 实体关系提取（使用 Codex AI 模拟）
4. 写入 Neo4j 知识图谱
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

# ============================================================
# 配置
# ============================================================
FILES_DIR = project_root / "files" / "txt文件"
OUTPUT_DIR = project_root / "output" / "kg_build"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 实体类型和关系类型定义
ENTITY_TYPES = [
    "奖学金类型",      # 各类奖学金
    "学生类型",        # 学生类别（本科生、研究生等）
    "评选条件",        # 评选资格和条件
    "组织机构",        # 学校、学院、委员会等
    "金额等级",        # 奖学金金额和等级
    "政策法规",        # 规章制度
    "时间期限",        # 评选时间、申请期限等
]

RELATIONSHIP_TYPES = [
    "属于",           # 归属关系
    "要求",           # 条件要求
    "评定",           # 评定关系
    "发放",           # 奖金发放
    "申请",           # 申请关系
    "审核",           # 审核关系
    "包含",           # 包含关系
    "排斥",           # 互斥关系
]

# ============================================================
# 模拟 LLM 响应（使用预定义的提取结果）
# 在实际使用中，可以调用 Codex MCP 工具来生成响应
# ============================================================

def mock_llm_extract_entities_relations(text: str, chunk_id: int) -> Dict[str, Any]:
    """
    模拟 LLM 提取实体和关系
    
    在实际生产环境中，这里应该调用真实的 LLM API 或 Codex MCP 工具。
    本函数返回基于文本关键词的预定义提取结果。
    """
    entities = []
    relations = []
    
    # 根据文本内容提取实体
    if "国家奖学金" in text:
        entities.append({
            "id": f"e_{chunk_id}_1",
            "name": "国家奖学金",
            "type": "奖学金类型",
            "properties": {"级别": "国家级", "金额": "8000元/人/年"}
        })
    
    if "国家励志奖学金" in text:
        entities.append({
            "id": f"e_{chunk_id}_2",
            "name": "国家励志奖学金",
            "type": "奖学金类型",
            "properties": {"级别": "国家级", "金额": "5000元/人/年"}
        })
    
    if "上海市奖学金" in text:
        entities.append({
            "id": f"e_{chunk_id}_3",
            "name": "上海市奖学金",
            "type": "奖学金类型",
            "properties": {"级别": "市级"}
        })
    
    if "优秀奖学金" in text or "特等" in text:
        entities.append({
            "id": f"e_{chunk_id}_4",
            "name": "优秀奖学金",
            "type": "奖学金类型",
            "properties": {"级别": "校级"}
        })
        if "特等" in text:
            entities.append({
                "id": f"e_{chunk_id}_5",
                "name": "特等奖学金",
                "type": "金额等级",
                "properties": {"金额": "5000元/人/学年", "比例": "2%"}
            })
        if "一等" in text:
            entities.append({
                "id": f"e_{chunk_id}_6",
                "name": "一等奖学金",
                "type": "金额等级",
                "properties": {"金额": "3000元/人/学年", "比例": "3%"}
            })
    
    if "本科生" in text or "本科学生" in text:
        entities.append({
            "id": f"e_{chunk_id}_7",
            "name": "本科生",
            "type": "学生类型",
            "properties": {"学历层次": "本科"}
        })
    
    if "华东理工大学" in text:
        entities.append({
            "id": f"e_{chunk_id}_8",
            "name": "华东理工大学",
            "type": "组织机构",
            "properties": {"类型": "高校"}
        })
    
    if "本科生奖惩评审委员会" in text:
        entities.append({
            "id": f"e_{chunk_id}_9",
            "name": "本科生奖惩评审委员会",
            "type": "组织机构",
            "properties": {"职能": "评审奖学金"}
        })
    
    if "综合成绩" in text or "德育" in text:
        entities.append({
            "id": f"e_{chunk_id}_10",
            "name": "综合成绩要求",
            "type": "评选条件",
            "properties": {"计算公式": "必修课程平均成绩×85%+德育考核成绩×15%"}
        })
    
    # 生成关系
    entity_ids = [e["id"] for e in entities]
    if len(entities) >= 2:
        # 创建一些基本关系
        for i in range(len(entities) - 1):
            relations.append({
                "source": entities[i]["id"],
                "target": entities[i + 1]["id"],
                "type": "属于" if "奖学金" in entities[i]["name"] else "要求",
                "properties": {"来源": f"chunk_{chunk_id}"}
            })
    
    return {
        "entities": entities,
        "relations": relations,
        "chunk_id": chunk_id,
        "text_preview": text[:100] + "..." if len(text) > 100 else text
    }


# ============================================================
# 文档处理
# ============================================================

def read_documents(files_dir: Path) -> List[Tuple[str, str]]:
    """读取所有文档"""
    documents = []
    for file_path in files_dir.glob("*.txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            documents.append((file_path.name, content))
    return documents


def simple_chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """简单的文本分块（按字符数）"""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start = end - overlap
        if start + overlap >= len(text):
            break
    return chunks


# ============================================================
# 知识图谱构建主流程
# ============================================================

def build_knowledge_graph():
    """构建知识图谱的主函数"""
    
    console.print(Panel.fit(
        "[bold cyan]GraphRAG 知识图谱构建[/bold cyan]\n"
        "[dim]使用 AI 助手模拟 LLM API[/dim]",
        border_style="cyan"
    ))
    
    # Step 1: 读取文档
    console.print("\n[bold yellow]Step 1: 读取文档[/bold yellow]")
    documents = read_documents(FILES_DIR)
    console.print(f"  读取了 [green]{len(documents)}[/green] 个文档")
    
    # 显示文档列表
    table = Table(title="文档列表")
    table.add_column("序号", style="cyan")
    table.add_column("文件名", style="green")
    table.add_column("大小", style="yellow")
    
    for i, (name, content) in enumerate(documents, 1):
        table.add_row(str(i), name, f"{len(content)} 字符")
    
    console.print(table)
    
    # Step 2: 文本分块
    console.print("\n[bold yellow]Step 2: 文本分块[/bold yellow]")
    all_chunks = []
    for doc_name, content in documents:
        chunks = simple_chunk_text(content)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "doc_name": doc_name,
                "chunk_id": f"{doc_name}_{i}",
                "content": chunk
            })
    console.print(f"  共生成 [green]{len(all_chunks)}[/green] 个文本块")
    
    # Step 3: 实体关系提取
    console.print("\n[bold yellow]Step 3: 实体关系提取[/bold yellow]")
    all_entities = []
    all_relations = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("提取实体和关系...", total=len(all_chunks))
        
        for i, chunk_info in enumerate(all_chunks):
            result = mock_llm_extract_entities_relations(
                chunk_info["content"],
                i
            )
            all_entities.extend(result["entities"])
            all_relations.extend(result["relations"])
            progress.update(task, advance=1)
    
    # 去重并建立 ID 映射
    unique_entities = {}
    id_mapping = {}  # old_id -> new_id (retained entity's id)
    
    for e in all_entities:
        key = (e["name"], e["type"])
        if key not in unique_entities:
            unique_entities[key] = e
        
        # 将当前实体 ID 映射到保留的实体 ID
        # 如果是第一次遇到，它映射到自己
        # 如果是重复的，它映射到之前保留的那个实体 ID
        id_mapping[e["id"]] = unique_entities[key]["id"]
    
    # 更新关系中的 ID 并去重
    unique_relations_map = {}
    updated_count = 0
    for r in all_relations:
        # 更新源和目标 ID
        if r["source"] in id_mapping:
            if r["source"] != id_mapping[r["source"]]:
                updated_count += 1
                # console.print(f"[dim]Rel update: {r['source']} -> {id_mapping[r['source']]}[/dim]")
            r["source"] = id_mapping[r["source"]]
            
        if r["target"] in id_mapping:
            if r["target"] != id_mapping[r["target"]]:
                updated_count += 1
            r["target"] = id_mapping[r["target"]]
            
        # 避免自环（可选，视需求而定）
        if r["source"] == r["target"]:
            continue
            
        key = (r["source"], r["target"], r["type"])
        unique_relations_map[key] = r
    
    console.print(f"  已更新 [yellow]{updated_count}[/yellow] 个关系引用")
    
    unique_relations = list(unique_relations_map.values())
    
    console.print(f"  提取到 [green]{len(unique_entities)}[/green] 个唯一实体")
    console.print(f"  提取到 [green]{len(unique_relations)}[/green] 个唯一关系")
    
    # 显示提取的实体
    entity_table = Table(title="提取的实体")
    entity_table.add_column("名称", style="cyan")
    entity_table.add_column("类型", style="green")
    entity_table.add_column("属性", style="yellow")
    
    for (name, etype), entity in list(unique_entities.items())[:15]:
        props = json.dumps(entity.get("properties", {}), ensure_ascii=False)
        entity_table.add_row(name, etype, props[:50])
    
    console.print(entity_table)
    
    # Step 4: 保存结果
    console.print("\n[bold yellow]Step 4: 保存结果[/bold yellow]")
    
    output_data = {
        "build_time": datetime.now().isoformat(),
        "statistics": {
            "documents": len(documents),
            "chunks": len(all_chunks),
            "entities": len(unique_entities),
            "relations": len(unique_relations)
        },
        "entities": list(unique_entities.values()),
        "relations": unique_relations
    }
    
    output_file = OUTPUT_DIR / f"kg_build_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    console.print(f"  结果保存至: [green]{output_file}[/green]")
    
    # Step 5: 输出到 Neo4j（模拟）
    console.print("\n[bold yellow]Step 5: 写入 Neo4j（模拟）[/bold yellow]")
    console.print("  [dim]注意：实际写入需要 Neo4j 连接[/dim]")
    console.print("  [dim]这里仅展示 Cypher 语句示例[/dim]")
    
    # 生成示例 Cypher 语句
    console.print("\n  [cyan]示例 Cypher 语句:[/cyan]")
    for i, entity in enumerate(list(unique_entities.values())[:3]):
        cypher = f"CREATE (n:{entity['type'].replace(' ', '_')} {{name: '{entity['name']}', ...}})"
        console.print(f"    {cypher}")
    
    # 完成
    console.print(Panel.fit(
        "[bold green]✓ 知识图谱构建完成！[/bold green]\n\n"
        f"文档数: {len(documents)}\n"
        f"文本块: {len(all_chunks)}\n"
        f"实体数: {len(unique_entities)}\n"
        f"关系数: {len(unique_relations)}",
        border_style="green"
    ))
    
    return output_data


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    try:
        result = build_knowledge_graph()
    except Exception as e:
        console.print(f"[red]构建过程出错: {e}[/red]")
        import traceback
        traceback.print_exc()
