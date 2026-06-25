#!/bin/bash
# ──────────────────────────────────────────────
# Skill 打包脚本 - 一键打包 + 自动日期存档
# ──────────────────────────────────────────────
# 用法:
#   bash packages/build.sh             打包所有 skill
#   bash packages/build.sh ops-data-query   只打包指定 skill
#   bash packages/build.sh log-analyzer-skill
# ──────────────────────────────────────────────

set -e
cd "$(dirname "$0")/.."  # 回到 .trae/skills/

DATE_TAG=$(date +%Y-%m-%d)
PACKAGES_DIR="packages"
TARGET="$1"

# 需要打包的 skill 列表
ALL_SKILLS=(
  "log-analyzer-skill"
  "ops-data-query"
)

if [ -n "$TARGET" ]; then
  SKILLS_TO_BUILD=("$TARGET")
else
  SKILLS_TO_BUILD=("${ALL_SKILLS[@]}")
fi

echo "=========================================="
echo " Skill 打包脚本"
echo " 日期: $DATE_TAG"
echo "=========================================="

for skill in "${SKILLS_TO_BUILD[@]}"; do
  echo ""
  echo "▶ 打包: $skill ..."

  if [ ! -d "$skill" ]; then
    echo "  ⚠ 跳过: 目录不存在 ($skill)"
    continue
  fi

  SKILL_DIR="$PACKAGES_DIR/$skill"
  ZIP_NAME="${skill}.zip"
  ZIP_PATH="${SKILL_DIR}/${ZIP_NAME}"

  # 确保目录存在
  mkdir -p "$SKILL_DIR"

  # 如果已有旧包，按日期归档
  if [ -f "$ZIP_PATH" ]; then
    ARCHIVE_NAME="${skill}.${DATE_TAG}.zip"
    mv "$ZIP_PATH" "${SKILL_DIR}/${ARCHIVE_NAME}"
    echo "  📦 旧包已存档: ${ARCHIVE_NAME}"
  fi

  # 打新包
  zip -r "$ZIP_PATH" "$skill/" \
    -x "*/__pycache__/*" "*.pyc" > /dev/null

  SIZE=$(du -h "$ZIP_PATH" | cut -f1)
  echo "  ✅ 新包已生成: ${ZIP_NAME} (${SIZE})"
done

echo ""
echo "=========================================="
echo " 完成! 共打包 ${#SKILLS_TO_BUILD[@]} 个 skill"
echo " 目录: $(cd $PACKAGES_DIR && pwd)"
echo "=========================================="
ls -lhR "$PACKAGES_DIR" 2>/dev/null | head -30
