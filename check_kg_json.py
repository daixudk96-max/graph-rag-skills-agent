"""验证知识图谱 JSON 文件的完整性"""
import json
import glob
import os
import sys
from pathlib import Path

# 获取最新的 json 文件
output_dir = Path("output/kg_build")
if not output_dir.exists():
    print("Output directory not found")
    sys.exit(1)
    
json_files = list(output_dir.glob("*.json"))
if not json_files:
    print("No JSON files found")
    sys.exit(1)
    
latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
print(f"Checking file: {latest_file.name}")

with open(latest_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# 1. 验证实体 ID 唯一性
print("\nVerifying Entities...")
entities = data.get("entities", [])
entity_ids = set()
duplicates = 0
for e in entities:
    if e["id"] in entity_ids:
        duplicates += 1
    entity_ids.add(e["id"])

print(f"Total Entities: {len(entities)}")
print(f"Unique IDs: {len(entity_ids)}")
if duplicates > 0:
    print(f"⚠️ Found {duplicates} duplicate entity IDs!")

# 2. 验证关系引用有效性
print("\nVerifying Relations...")
relations = data.get("relations", [])
print(f"Total Relations: {len(relations)}")

missing_sources = 0
missing_targets = 0
valid_relations = 0

for r in relations:
    is_valid = True
    if r["source"] not in entity_ids:
        missing_sources += 1
        is_valid = False
        # print(f"  Missing source: {r['source']}")
        
    if r["target"] not in entity_ids:
        missing_targets += 1
        is_valid = False
        # print(f"  Missing target: {r['target']}")
        
    if is_valid:
        valid_relations += 1

print(f"Valid Relations: {valid_relations}")
if missing_sources > 0:
    print(f"⚠️ Relations with missing source ID: {missing_sources}")
if missing_targets > 0:
    print(f"⚠️ Relations with missing target ID: {missing_targets}")

if valid_relations == len(relations):
    print("\n✅ Verification PASSED: All relations reference valid entity IDs.")
else:
    print("\n❌ Verification FAILED: Some relations reference missing entity IDs.")

