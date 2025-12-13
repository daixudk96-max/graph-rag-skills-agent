# Deployment Tasks

## Prerequisites (User Decision Required)

1. [ ] **API 配置方式确认**
   - 选择 API 提供方式：One-API / 第三方代理 / 直接 OpenAI
   - 提供有效的 API Key
   - 确认 LLM 模型选择（建议 GPT-4o 或 DeepSeek 20241226）

2. [ ] **知识库文件准备**
   - 准备要导入的原始文档（支持 TXT/PDF/MD/DOCX/DOC/CSV/JSON/YAML）
   - 确定知识图谱主题和实体/关系类型

---

## Phase 1: Infrastructure Setup

1. [x] 启动 One-API（如选择此方式）
   ```bash
   docker run --name one-api -d --restart always -p 13000:3000 -e TZ=Asia/Shanghai -v "C:\data\one-api:/data" justsong/one-api
   ```
   验证：访问 http://localhost:13000

2. [ ] 启动 Neo4j 数据库
   ```bash
   cd c:\github\graph-rag-agent && docker compose up -d
   ```
   验证：访问 http://localhost:7474（用户名 neo4j，密码 12345678）

---

## Phase 2: Python Environment

3. [ ] 创建 Python 虚拟环境
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

4. [ ] 安装依赖
   ```bash
   pip install -r requirements.txt
   pip install pywin32>=302  # Windows only
   ```
   验证：`pip check`

5. [ ] 初始化项目
   ```bash
   pip install -e .
   ```

---

## Phase 3: Configuration

6. [ ] 创建并配置 `.env` 文件
   - 复制 `.env.example` 为 `.env`
   - 填写 API Key 和模型配置
   - 确认 Neo4j 连接信息

7. [ ] 配置知识图谱 schema（可选）
   - 编辑 `graphrag_agent/config/settings.py`
   - 设置 `theme`、`entity_types`、`relationship_types`

8. [ ] 放置知识库文件
   - 将原始文档放入 `files/` 目录

---

## Phase 4: Build & Launch

9. [ ] 构建知识图谱
   ```bash
   python graphrag_agent/integrations/build/main.py
   ```

10. [ ] 启动后端服务
    ```bash
    python server/main.py
    ```
    验证：访问 http://localhost:8000/docs

11. [ ] 启动前端服务
    ```bash
    streamlit run frontend/app.py
    ```
    验证：访问 http://localhost:8501

---

## Phase 5: Verification

12. [ ] 功能验证
    - 在前端执行示例查询
    - 验证知识图谱可视化
    - 测试不同 Agent 类型

---

## Dependencies

- Task 2 可与 Task 1 并行执行
- Task 3-5 依赖 Python 环境
- Task 6-8 可并行执行
- Task 9 依赖 Task 2、6、8 完成
- Task 10-11 依赖 Task 9 完成
