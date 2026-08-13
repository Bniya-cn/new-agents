#!/usr/bin/env bash
# 一次性读取 secrets/gitee.token.in → 写入钥匙串 + AES 密文 → 安全擦除明文
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IN_FILE="${ROOT}/secrets/gitee.token.in"
ENC_FILE="${ROOT}/secrets/gitee.token.enc"
KEYCHAIN_SERVICE="healing-agents-gitee-token"
PASSPHRASE_SERVICE="healing-agents-gitee-token-passphrase"
ACCOUNT="${USER}"

if [[ ! -f "$IN_FILE" ]]; then
  echo "[ERROR] 缺少输入文件: secrets/gitee.token.in"
  echo "先执行: cp secrets/gitee.token.in.example secrets/gitee.token.in"
  echo "再把 token 粘贴进去，然后重新运行本脚本。"
  exit 1
fi

# 取第一行非注释、非空内容
TOKEN="$(
  grep -vE '^\s*#' "$IN_FILE" | sed '/^\s*$/d' | head -n 1 | tr -d '\r\n' | xargs
)"

if [[ -z "$TOKEN" || "$TOKEN" == "REPLACE_WITH_YOUR_GITEE_TOKEN" ]]; then
  echo "[ERROR] secrets/gitee.token.in 里还没有有效 token。"
  exit 1
fi

if [[ ${#TOKEN} -lt 16 ]]; then
  echo "[ERROR] token 过短，请确认粘贴完整。"
  exit 1
fi

mkdir -p "${ROOT}/secrets"

# 1) 写入 macOS Keychain（若已存在则更新）
if security find-generic-password -a "$ACCOUNT" -s "$KEYCHAIN_SERVICE" >/dev/null 2>&1; then
  security delete-generic-password -a "$ACCOUNT" -s "$KEYCHAIN_SERVICE" >/dev/null 2>&1 || true
fi
security add-generic-password -a "$ACCOUNT" -s "$KEYCHAIN_SERVICE" -w "$TOKEN" -U
echo "[OK] 已写入 macOS 钥匙串: service=$KEYCHAIN_SERVICE"

# 2) 生成/复用加密口令，并写入钥匙串；再用它对 token 做文件级加密备份
if ! PASS="$(security find-generic-password -a "$ACCOUNT" -s "$PASSPHRASE_SERVICE" -w 2>/dev/null)"; then
  PASS="$(openssl rand -base64 32)"
  if security find-generic-password -a "$ACCOUNT" -s "$PASSPHRASE_SERVICE" >/dev/null 2>&1; then
    security delete-generic-password -a "$ACCOUNT" -s "$PASSPHRASE_SERVICE" >/dev/null 2>&1 || true
  fi
  security add-generic-password -a "$ACCOUNT" -s "$PASSPHRASE_SERVICE" -w "$PASS" -U
  echo "[OK] 已生成加密口令并写入钥匙串: service=$PASSPHRASE_SERVICE"
else
  echo "[OK] 复用已有加密口令（钥匙串）"
fi

# openssl 加密：密文落盘，口令不落盘
umask 077
printf '%s' "$TOKEN" | openssl enc -aes-256-cbc -pbkdf2 -salt \
  -pass "pass:${PASS}" \
  -out "$ENC_FILE"
chmod 600 "$ENC_FILE"
echo "[OK] 已写入密文文件: secrets/gitee.token.enc"

# 3) 擦除明文输入
# 先覆写再删除，降低残留
if command -v shred >/dev/null 2>&1; then
  shred -u "$IN_FILE" 2>/dev/null || true
fi
if [[ -f "$IN_FILE" ]]; then
  dd if=/dev/urandom of="$IN_FILE" bs=1024 count=4 status=none 2>/dev/null || true
  rm -f "$IN_FILE"
fi
echo "[OK] 已擦除明文输入文件 secrets/gitee.token.in"

# 清理当前 shell 中的敏感变量
unset TOKEN PASS

echo
echo "完成。之后推送请用:"
echo "  ./scripts/push_remotes.sh"
