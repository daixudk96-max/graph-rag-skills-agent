# Fix PyTorch DLL Conflict on Windows

## Summary

本提案旨在修复 Windows 系统上 PyTorch DLL 加载失败的问题（WinError 1114），该问题阻止了 GraphRAG 项目的正常运行。

## Problem Statement

在 Windows 系统上运行项目时，遇到以下错误：

```
OSError: [WinError 1114] 动态链接库(DLL)初始化例程失败。
Error loading "C:\Python311\Lib\site-packages\torch\lib\c10.dll" or one of its dependencies.
```

### 错误链路

```
langgraph → langchain_core → transformers → torch → c10.dll 加载失败
```

### 根本原因

1. **版本不匹配**：安装了与本机不匹配的 PyTorch 构建
2. **依赖缺失**：缺少 VC++ 运行库或 CUDA 库
3. **间接安装**：`sentence_transformers` 自动安装的 torch 版本可能不兼容
4. **已知问题**：torch 2.9.0 在 Windows 上有此问题，需安装已验证版本

### 用户环境

- **GPU**: NVIDIA GeForce RTX 4090 (24GB VRAM)
- **驱动版本**: 581.xx
- **推荐**: 使用 CUDA 版本以充分利用 GPU 性能

## Proposed Solution

### 1. 安装 CUDA 版 PyTorch

由于用户有 RTX 4090 GPU，推荐安装 CUDA 12.4 版本：

```bash
# 卸载现有版本
pip uninstall -y torch torchvision torchaudio

# 安装 CUDA 12.4 版本 (适用于驱动 >= 525.60.13)
pip install torch==2.5.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

> **备选方案 (CPU 版本)**：如果 CUDA 版本仍有问题，可使用 CPU 版本：
> ```bash
> pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
> ```

### 2. 更新安装文档

在 `assets/start.md` 和 `README.md` 中添加 PyTorch 安装指南：

- GPU 用户：使用 CUDA 版本
- 无 GPU 用户：使用 CPU 版本

### 3. 创建环境检查脚本

创建 `scripts/check_pytorch.py` 用于验证 PyTorch 安装和 GPU 状态。

## Files to Modify

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `requirements.txt` | MODIFY | 添加 PyTorch 版本说明注释 |
| `assets/start.md` | MODIFY | 添加 PyTorch 安装说明（GPU/CPU） |
| `README.md` | MODIFY | 添加 PyTorch 问题排查指南 |
| `scripts/check_pytorch.py` | NEW | PyTorch 环境检查脚本 |

## Risks and Mitigations

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| CUDA 版本不兼容 | 中 | 提供 CPU 备选方案 |
| 驱动版本过旧 | 低 | RTX 4090 驱动通常较新 |
| 安装时间较长 | 低 | CUDA 包较大，需耐心等待 |

## Timeline

- Phase 1 (立即): 重新安装 PyTorch CUDA 版
- Phase 2: 更新 requirements.txt 注释
- Phase 3: 更新安装文档

