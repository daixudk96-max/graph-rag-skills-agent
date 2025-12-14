# Capability: kg-write-consistency

知识图谱写入一致性保障

## ADDED Requirements

### Requirement: ATOM 时序属性输出

知识图谱构建脚本应输出 ATOM 时序属性以区分传统图谱。

#### Scenario: 使用 ATOM 适配器构建图谱

- **Given**: 用户运行 `build_kg_atom.py` 脚本
- **When**: 脚本使用 `AtomExtractionAdapter` 提取知识图谱
- **Then**: 输出的 JSON 文件包含以下时序字段：
  - `entities[].t_obs`: 观察时间列表
  - `entities[].t_start`: 有效期开始时间
  - `entities[].t_end`: 有效期结束时间（可为空）
  - `relationships[].t_obs`: 关系观察时间
  - `relationships[].t_start`: 关系有效期开始
  - `relationships[].t_end`: 关系有效期结束

---

### Requirement: 实体-关系一致性校验

系统应在写入前校验实体与关系的一致性，过滤悬空引用。

#### Scenario: 检测并过滤悬空关系

- **Given**: 知识图谱包含关系 `(e_1) --[r]--> (e_99)`
- **And**: 实体列表仅包含 `e_1`，不包含 `e_99`
- **When**: 系统执行一致性校验
- **Then**: 该关系被标记为无效并过滤
- **And**: 系统记录警告日志包含 `"Missing target: e_99"`

#### Scenario: 写入前校验通过

- **Given**: 所有关系的 source 和 target 都存在于实体列表
- **When**: 系统执行一致性校验
- **Then**: 所有关系通过校验
- **And**: 不记录警告日志

---

### Requirement: Neo4j 写入错误记录

系统应记录 Neo4j 写入失败的详细信息，而非静默跳过。

#### Scenario: 记录关系写入失败

- **Given**: 尝试写入关系 `(e_1) --[r]--> (e_2)`
- **When**: Neo4j 中不存在节点 `e_2`
- **Then**: 系统记录错误日志 `"Failed to write relation: target e_2 not found in Neo4j"`
- **And**: 写入统计显示失败数 +1

---

### Requirement: 写入数量一致性

命令输出的统计数应与 Neo4j 实际写入数一致。

#### Scenario: 节点数量一致

- **Given**: 构建脚本输出 `写入 N 个节点`
- **When**: 用户在 Neo4j Browser 执行 `MATCH (n:KGEntity) RETURN count(n)`
- **Then**: 返回结果等于 N

#### Scenario: 关系数量一致

- **Given**: 构建脚本输出 `写入 M 个关系`
- **When**: 用户在 Neo4j Browser 执行 `MATCH ()-[r:RELATES]->() RETURN count(r)`
- **Then**: 返回结果等于 M
- **Or**: 如有被过滤的无效关系，脚本输出明确说明 `已过滤 K 个无效关系`

---

## MODIFIED Requirements

### Requirement: 关系去重键策略（修改自现有实现）

关系去重应使用唯一标识符而非仅靠类型，避免有效关系被不当合并。

#### Scenario: 同类型不同来源的关系保留

- **Given**: 实体 A 与实体 B 之间存在两条 "属于" 关系
- **And**: 第一条来自 `chunk_1`，第二条来自 `chunk_5`
- **When**: 系统写入关系
- **Then**: 两条关系均被保留
- **And**: 通过 `rel_id` 或 `chunk_id` 可区分

---

### Requirement: 可选实体质量后处理

系统应支持可选的实体质量后处理，默认关闭，由配置项控制。

#### Scenario: 后处理默认关闭

- **Given**: 环境变量 `ENABLE_ENTITY_QUALITY_POSTPROCESS` 未设置或为 `false`
- **When**: 用户运行 `build_kg_atom.py`
- **Then**: 图谱构建完成后不调用 `EntityQualityProcessor`
- **And**: 日志不包含 "Starting entity quality postprocess"

#### Scenario: 启用后处理

- **Given**: 环境变量 `ENABLE_ENTITY_QUALITY_POSTPROCESS=true`
- **When**: 用户运行 `build_kg_atom.py`
- **Then**: 图谱写入 Neo4j 后自动调用 `EntityQualityProcessor`
- **And**: 日志包含 "Starting entity quality postprocess"
- **And**: 执行实体消歧和对齐

## Cross-References

- 依赖: `graphrag_agent/graph/extraction/atom_adapter.py`
- 依赖: `graphrag_agent/graph/extraction/temporal_writer.py`
- 依赖: `graphrag_agent/graph/structure/temporal_kg.py`
- 依赖: `graphrag_agent/graph/processing/entity_quality.py` (可选后处理)
- 相关: `openspec/specs/atom-extraction/spec.md`

