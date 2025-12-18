# fix-apply-spec-output-dir

## Summary

修复 `apply-spec` 命令的 `--output-dir` 参数被忽略的 bug。

## Problem Statement

当用户运行 `skill-seekers apply-spec spec.yaml --output-dir output/my-custom-path` 时，
`--output-dir` 参数被完全忽略。输出目录始终由 `spec.yaml` 中的 `name` 字段硬编码决定为 `output/{spec.name}`。

### Root Cause

1. `main.py:_handle_apply_spec()` 没有读取或传递 `args.output_dir` 给 `UnifiedSkillBuilder`
2. `UnifiedSkillBuilder.__init__()` 硬编码 `self.skill_dir = f"output/{self.name}"`
3. `UnifiedSkillBuilder.build_from_spec()` 再次硬编码覆盖 `self.skill_dir = f"output/{self.skill_spec.name}"`

## Proposed Solution

1. 在 `UnifiedSkillBuilder.__init__()` 中添加可选参数 `output_dir: Optional[str] = None`
2. 如果提供了 `output_dir`，使用它；否则默认为 `output/{skill_name}`
3. 修改 `build_from_spec()` 仅在未设置 `output_dir` 时使用默认值
4. 修改 `_handle_apply_spec()` 读取并传递 `args.output_dir`

## Scope

- **Affects**: `spec-first-skill-workflow` capability
- **Priority**: High (CLI flag is non-functional)
- **Backward Compatible**: Yes (default behavior unchanged when flag omitted)

## Files Changed

| File | Change Type |
|------|-------------|
| `src/skill_seekers/cli/main.py` | Modify `_handle_apply_spec()` |
| `src/skill_seekers/cli/unified_skill_builder.py` | Modify `__init__()` and `build_from_spec()` |
| `tests/test_unified.py` | Add tests for output_dir parameter |
