"""
ATOM 时序知识图谱构建脚本

使用 ATOM 适配器从文档中提取时序知识图谱，并写入 Neo4j 数据库。
支持完整的时序属性 (t_obs, t_start, t_end) 和原子事实追踪。

运行步骤：
1. 读取输入文件（txt 文档或 json 文本块）
2. 使用 AtomExtractionAdapter.extract_from_chunks_sync() 提取时序知识图谱
3. 使用 Neo4jTemporalWriter.write_temporal_kg() 写入 Neo4j
4. 输出包含时序属性的 JSON 文件

用法：
    python build_kg_atom.py                           # 使用默认输入目录
    python build_kg_atom.py --input ./files/txt文件   # 指定输入目录
    python build_kg_atom.py --input chunks.json       # 使用 JSON 文本块文件
    python build_kg_atom.py --skip-write              # 仅提取，不写入 Neo4j
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

console = Console()


# ============================================================
# 配置
# ============================================================
DEFAULT_INPUT_DIR = PROJECT_ROOT / "files" / "txt文件"
OUTPUT_DIR = PROJECT_ROOT / "output" / "kg_build"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 文本加载与分块
# ============================================================

def load_text_chunks(input_path: Path) -> List[str]:
    """
    加载文本块。
    
    支持两种输入格式：
    1. 目录：读取所有 .txt 文件并分块
    2. JSON 文件：直接读取预分块的文本
    
    Args:
        input_path: 输入文件或目录路径
        
    Returns:
        文本块列表
    """
    if input_path.is_file():
        return _load_chunks_from_json(input_path)
    elif input_path.is_dir():
        return _load_chunks_from_directory(input_path)
    else:
        raise FileNotFoundError(f"输入路径不存在: {input_path}")


def _load_chunks_from_json(json_path: Path) -> List[str]:
    """从 JSON 文件加载文本块"""
    console.print(f"[cyan]从 JSON 文件加载: {json_path.name}[/cyan]")
    
    data = json.loads(json_path.read_text(encoding="utf-8"))
    
    # 支持多种 JSON 格式
    if isinstance(data, list):
        # 直接是文本块列表
        if all(isinstance(item, str) for item in data):
            return data
        # 包含 chunk_doc 或 content 字段的对象列表
        chunks = []
        for item in data:
            if isinstance(item, dict):
                text = item.get("chunk_doc") or item.get("content") or item.get("text") or ""
                if text:
                    chunks.append(text)
        return chunks
    
    # 包含 chunks 字段的对象
    if "chunks" in data:
        return [c.get("content", c) if isinstance(c, dict) else c for c in data["chunks"]]
    
    raise ValueError(f"无法解析 JSON 格式: {json_path}")


def _load_chunks_from_directory(dir_path: Path) -> List[str]:
    """从目录中读取所有 txt 文件并分块"""
    console.print(f"[cyan]从目录加载文档: {dir_path}[/cyan]")
    
    all_chunks = []
    txt_files = list(dir_path.glob("*.txt"))
    
    if not txt_files:
        raise FileNotFoundError(f"目录中未找到 .txt 文件: {dir_path}")
    
    for file_path in txt_files:
        content = file_path.read_text(encoding="utf-8")
        chunks = _simple_chunk_text(content)
        all_chunks.extend(chunks)
        console.print(f"  [dim]{file_path.name}: {len(chunks)} 个文本块[/dim]")
    
    return all_chunks


def _simple_chunk_text(
    text: str, 
    chunk_size: int = 500, 
    overlap: int = 100
) -> List[str]:
    """简单的文本分块（按字符数，带重叠）"""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start + overlap >= len(text):
            break
    return chunks


# ============================================================
# ATOM 时序知识图谱构建
# ============================================================

def build_temporal_knowledge_graph(
    chunks: Sequence[str],
    observation_time: Optional[str] = None,
) -> "TemporalKnowledgeGraph":
    """
    使用 ATOM 适配器构建时序知识图谱。
    
    Args:
        chunks: 文本块列表
        observation_time: 观察时间戳 (ISO 格式)，默认当前时间
        
    Returns:
        TemporalKnowledgeGraph 实例
    """
    from graphrag_agent.graph.extraction.atom_adapter import AtomExtractionAdapter
    from graphrag_agent.models.get_models import get_llm_model, get_embeddings_model
    
    console.print("\n[bold yellow]初始化 ATOM 适配器...[/bold yellow]")
    
    # 初始化模型
    llm = get_llm_model()
    embeddings = get_embeddings_model()
    
    # 创建适配器
    adapter = AtomExtractionAdapter(
        llm_model=llm,
        embeddings_model=embeddings,
    )
    
    console.print(f"  [green]✓[/green] LLM: {llm.model_name}")
    console.print(f"  [green]✓[/green] Embeddings: 已初始化")
    
    # 使用观察时间
    obs_time = observation_time or datetime.now(timezone.utc).isoformat()
    console.print(f"  [green]✓[/green] 观察时间: {obs_time}")
    
    # 提取时序知识图谱
    console.print(f"\n[bold yellow]提取时序知识图谱 ({len(chunks)} 个文本块)...[/bold yellow]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("ATOM 提取中...", total=None)
        
        temporal_kg = adapter.extract_from_chunks_sync(
            chunks=chunks,
            observation_time=obs_time,
        )
        
        progress.update(task, completed=True)
    
    console.print(f"  [green]✓[/green] 实体数量: {len(temporal_kg.entities)}")
    console.print(f"  [green]✓[/green] 关系数量: {len(temporal_kg.relationships)}")
    
    return temporal_kg


def write_to_neo4j(
    temporal_kg: "TemporalKnowledgeGraph",
    merge_strategy: str = "replace",
) -> Dict[str, int]:
    """
    将时序知识图谱写入 Neo4j。
    
    Args:
        temporal_kg: 时序知识图谱
        merge_strategy: 合并策略 ('update' 或 'replace')
        
    Returns:
        写入统计 {"entities": n, "relationships": m}
    """
    from graphrag_agent.graph.extraction.temporal_writer import create_temporal_writer
    
    console.print("\n[bold yellow]写入 Neo4j...[/bold yellow]")
    
    # 创建写入器
    writer = create_temporal_writer()
    
    neo4j_uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
    console.print(f"  [cyan]连接: {neo4j_uri}[/cyan]")
    
    # 写入数据
    stats = writer.write_temporal_kg(temporal_kg, merge_strategy=merge_strategy)
    
    console.print(f"  [green]✓[/green] 写入实体: {stats.get('entities', 0)}")
    console.print(f"  [green]✓[/green] 写入关系: {stats.get('relationships', 0)}")
    
    return stats


def save_output(
    temporal_kg: "TemporalKnowledgeGraph",
    input_info: str,
    write_stats: Optional[Dict[str, int]] = None,
) -> Path:
    """
    保存输出 JSON 文件。
    
    Args:
        temporal_kg: 时序知识图谱
        input_info: 输入信息描述
        write_stats: Neo4j 写入统计（可选）
        
    Returns:
        输出文件路径
    """
    console.print("\n[bold yellow]保存输出...[/bold yellow]")
    
    # 序列化知识图谱
    output_data = temporal_kg.to_dict()
    
    # 添加元数据
    output_data["metadata"] = {
        "input": input_info,
        "neo4j_write": write_stats or {"skipped": True},
        "extractor": "ATOM",
    }
    
    # 生成输出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"kg_atom_{timestamp}.json"
    
    # 写入文件
    output_file.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    
    console.print(f"  [green]✓[/green] 输出文件: {output_file}")
    
    return output_file


# ============================================================
# 主流程
# ============================================================

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="ATOM 时序知识图谱构建脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="输入文件或目录路径（默认: files/txt文件）",
    )
    parser.add_argument(
        "--observation-time", "-t",
        type=str,
        default=None,
        help="观察时间戳（ISO 格式，默认当前时间）",
    )
    parser.add_argument(
        "--skip-write",
        action="store_true",
        help="跳过 Neo4j 写入，仅提取和保存 JSON",
    )
    parser.add_argument(
        "--merge-strategy",
        choices=["update", "replace"],
        default="replace",
        help="Neo4j 合并策略（默认: replace）",
    )
    
    args = parser.parse_args()
    
    # 显示标题
    console.print(Panel.fit(
        "[bold cyan]ATOM 时序知识图谱构建[/bold cyan]\n"
        "[dim]使用 ATOM 提取器和 Neo4j 时序写入器[/dim]",
        border_style="cyan",
    ))
    
    try:
        # Step 1: 加载文本块
        console.print("\n[bold yellow]Step 1: 加载文本块[/bold yellow]")
        chunks = load_text_chunks(args.input)
        console.print(f"  [green]✓[/green] 加载 {len(chunks)} 个文本块")
        
        # Step 2: 构建时序知识图谱
        console.print("\n[bold yellow]Step 2: 构建时序知识图谱[/bold yellow]")
        temporal_kg = build_temporal_knowledge_graph(
            chunks=chunks,
            observation_time=args.observation_time,
        )
        
        # 显示提取结果摘要
        _display_extraction_summary(temporal_kg)
        
        # Step 3: 写入 Neo4j（可选）
        write_stats = None
        if not args.skip_write:
            console.print("\n[bold yellow]Step 3: 写入 Neo4j[/bold yellow]")
            write_stats = write_to_neo4j(temporal_kg, args.merge_strategy)
        else:
            console.print("\n[bold yellow]Step 3: 跳过 Neo4j 写入[/bold yellow]")
        
        # Step 4: 保存输出
        console.print("\n[bold yellow]Step 4: 保存输出[/bold yellow]")
        output_file = save_output(
            temporal_kg=temporal_kg,
            input_info=str(args.input),
            write_stats=write_stats,
        )
        
        # 完成
        _display_completion_summary(temporal_kg, output_file, write_stats)
        
    except Exception as e:
        with open("error.log", "w", encoding="utf-8") as f:
            import traceback
            f.write(str(e) + "\n" + traceback.format_exc())
        console.print(f"\n[red]错误: {e}[/red]")
        logger.exception("构建过程出错")
        sys.exit(1)


def _display_extraction_summary(temporal_kg: "TemporalKnowledgeGraph") -> None:
    """显示提取结果摘要"""
    console.print("\n[bold]提取结果摘要:[/bold]")
    
    # 实体表格
    if temporal_kg.entities:
        entity_table = Table(title="实体 (前 10 个)")
        entity_table.add_column("名称", style="cyan", max_width=30)
        entity_table.add_column("类型", style="green")
        entity_table.add_column("嵌入", style="yellow")
        
        for entity in temporal_kg.entities[:10]:
            has_emb = "✓" if entity.embeddings else "-"
            entity_table.add_row(
                entity.name[:30],
                entity.label,
                has_emb,
            )
        
        console.print(entity_table)
    
    # 关系表格
    if temporal_kg.relationships:
        rel_table = Table(title="关系 (前 10 个)")
        rel_table.add_column("源", style="cyan", max_width=20)
        rel_table.add_column("关系", style="magenta")
        rel_table.add_column("目标", style="cyan", max_width=20)
        rel_table.add_column("时序", style="yellow")
        
        for rel in temporal_kg.relationships[:10]:
            has_temporal = "✓" if rel.t_obs or rel.t_start else "-"
            rel_table.add_row(
                rel.source_id[:20],
                rel.type[:15],
                rel.target_id[:20],
                has_temporal,
            )
        
        console.print(rel_table)


def _display_completion_summary(
    temporal_kg: "TemporalKnowledgeGraph",
    output_file: Path,
    write_stats: Optional[Dict[str, int]],
) -> None:
    """显示完成摘要"""
    summary_lines = [
        "[bold green]✓ 时序知识图谱构建完成！[/bold green]\n",
        f"实体数: {len(temporal_kg.entities)}",
        f"关系数: {len(temporal_kg.relationships)}",
    ]
    
    if write_stats:
        summary_lines.append(f"\n[cyan]Neo4j 写入:[/cyan]")
        summary_lines.append(f"  实体: {write_stats.get('entities', 0)}")
        summary_lines.append(f"  关系: {write_stats.get('relationships', 0)}")
    
    summary_lines.append(f"\n输出文件: {output_file.name}")
    
    console.print(Panel.fit(
        "\n".join(summary_lines),
        border_style="green",
    ))


if __name__ == "__main__":
    main()
