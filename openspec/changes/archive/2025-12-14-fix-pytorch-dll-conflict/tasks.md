# Tasks - Fix PyTorch DLL Conflict

## Phase 1: 修复 PyTorch 安装 (立即执行)

- [x] 1.1 卸载现有 PyTorch
  ```bash
  pip uninstall -y torch torchvision torchaudio
  ```

- [x] 1.2 安装 CUDA 12.4 版 PyTorch 2.5.1
  ```bash
  pip install torch==2.5.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
  ```

- [x] 1.3 验证 PyTorch 安装
  - 输出: PyTorch 2.5.1+cu124, CUDA available: True, CUDA version: 12.4

- [x] 1.4 验证依赖链
  - transformers 和 langchain_core 导入成功，无 DLL 错误

---

## Phase 2: 验证结果

- [x] 运行端到端测试 `test_e2e_graphrag_mock.py`
  - 结果: 错误从 13 个减少到 4 个
  - **DLL 错误已完全消除**
  - 剩余 4 个错误是测试脚本导入路径问题（非 PyTorch 相关）

---

## Validation Checklist

- [x] `python -c "import torch; print(torch.__version__)"` 输出 `2.5.1+cu124`
- [x] `python -c "import torch; print(torch.cuda.is_available())"` 输出 `True`
- [x] `python -c "import transformers; print('OK')"` 成功
- [x] `python -c "import langchain_core; print('OK')"` 成功
- [x] `python test_e2e_graphrag_mock.py` 无 DLL 错误 ✅

---

## 结果摘要

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 总错误数 | 13 | 4 |
| DLL 相关错误 | 13 | 0 |
| PyTorch 版本 | 2.9.1 (有问题) | 2.5.1+cu124 |
| CUDA 可用 | 否 (DLL 失败) | 是 |

**结论**: PyTorch DLL 冲突问题已完全解决。
