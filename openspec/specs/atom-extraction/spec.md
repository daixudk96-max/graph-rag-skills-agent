# atom-extraction Specification

## Purpose
TBD - created by archiving change integrate-atom-temporal-kg. Update Purpose after archive.
## Requirements
### Requirement: ATOM 时序知识图谱提取

系统应支持使用 ATOM 的三模块并行管道从非结构化文本中提取时序知识图谱。

#### Scenario: 从文档提取时序知识图谱

**Given** 用户提供了一个文档文件（如 PDF、TXT、DOCX）
**And** ATOM 提取模式已启用（`ATOM_ENABLED=true`）
**When** 系统处理该文档
**Then** 文档被分块处理（每块 ≤400 tokens）
**And** 每个块被分解为原子事实
**And** 从原子事实并行提取 5-元组 `(subject, predicate, object, t_start, t_end)`
**And** 原子知识图谱被并行合并
**And** 结果包含时序属性（观察时间、有效期）

#### Scenario: 增量更新现有知识图谱

**Given** 系统中已存在一个知识图谱
**And** 用户提供了新的文档
**When** 系统执行增量更新
**Then** 新文档被提取为原子知识图谱
**And** 新图谱与现有图谱使用余弦相似度进行实体/关系解析
**And** 时序属性被合并（扩展有效期历史）
**And** 重复实体/关系被合并而非重复创建

#### Scenario: 时序属性存储

**Given** ATOM 提取完成，生成了时序知识图谱
**When** 知识图谱被写入 Neo4j
**Then** 关系节点包含 `atom_t_obs` 属性（观察时间列表）
**And** 关系节点包含 `atom_t_start` 属性（有效期开始时间列表）
**And** 关系节点包含 `atom_t_end` 属性（有效期结束时间列表）
**And** 关系节点包含 `atom_atomic_facts` 属性（源原子事实列表）

#### Scenario: 配置阈值参数

**Given** 用户设置了 ATOM 配置参数
**When** 执行实体/关系解析
**Then** 实体相似度使用 `ATOM_ENTITY_THRESHOLD`（默认 0.8）
**And** 关系相似度使用 `ATOM_RELATION_THRESHOLD`（默认 0.7）
**And** 并行工作线程数使用 `ATOM_MAX_WORKERS`（默认 8）

### Requirement: 保持向后兼容

系统应在启用 ATOM 的同时保留现有的实体关系提取能力。

#### Scenario: Fallback 到传统提取器

**Given** `ATOM_ENABLED=false` 或未设置
**When** 系统处理文档
**Then** 使用现有的 `EntityRelationExtractor` 进行提取
**And** 行为与 ATOM 集成前完全一致

#### Scenario: 混合模式运行

**Given** 系统中同时存在 ATOM 提取的数据和传统提取的数据
**When** 查询知识图谱
**Then** 两种来源的数据都可以被检索
**And** 时序属性在存在时被返回，不存在时返回空

