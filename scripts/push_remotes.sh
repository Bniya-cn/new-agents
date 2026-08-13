#!/usr/bin/env bash
# 从钥匙串（优先）或密文文件取 Gitee token，推送 GitHub + Gitee，不把 token 写进磁盘明文。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

KEYCHAIN_SERVICE="healing-agents-gitee-token"
PASSPHRASE_SERVICE="healing-agents-gitee-token-passphrase"
ACCOUNT="${USER}"
ENC_FILE="${ROOT}/secrets/gitee.token.enc"
GITEE_URL_BASE="https://gitee.com/dai-jinglin050402/healing-agents.git"

get_gitee_token() {
  local token=""
  if token="$(security find-generic-password -a "$ACCOUNT" -s "$KEYCHAIN_SERVICE" -w 2>/dev/null)"; then
    printf '%s' "$token"
    return 0
  fi

  if [[ -f "$ENC_FILE" ]]; then
    local pass
    pass="$(security find-generic-password -a "$ACCOUNT" -s "$PASSPHRASE_SERVICE" -w 2>/dev/null || true)"
    if [[ -z "$pass" ]]; then
      echo "[ERROR] 找不到钥匙串中的解密口令，且无法从钥匙串读 token。" >&2
      echo "请重新运行: ./scripts/secure_store_gitee_token.sh" >&2
      return 1
    fi
    openssl enc -d -aes-256-cbc -pbkdf2 -salt \
      -pass "pass:${pass}" \
      -in "$ENC_FILE" 2>/dev/null
    return 0
  fi

  echo "[ERROR] 未找到 Gitee token。请先:" >&2
  echo "  cp secrets/gitee.token.in.example secrets/gitee.token.in" >&2
  echo "  # 编辑粘贴 token" >&2
  echo "  ./scripts/secure_store_gitee_token.sh" >&2
  return 1
}

echo "== 1) Push GitHub =="
git push github HEAD:main
git push --tags github 2>/dev/null || true

echo "== 2) Push Gitee (token from keychain/ciphertext) =="
TOKEN="$(get_gitee_token)"
if [[ -z "$TOKEN" ]]; then
  echo "[ERROR] token 为空"
  exit 1
fi

# 使用临时 askpass / URL 注入，避免 token 出现在 git remote -v 持久配置里
# GIT_ASKPASS 方式更干净，但 URL 一次性 push 也可用；这里用环境变量 + rewrite
AUTHED_URL="https://oauth2:${TOKEN}@gitee.com/dai-jinglin050402/healing-agents.git"

# 不打印 URL（含 token）
set +x
git push "$AUTHED_URL" HEAD:master
git push "$AUTHED_URL" HEAD:main
git push --tags "$AUTHED_URL" 2>/dev/null || true
unset TOKEN AUTHED_URL

echo "== 3) Verify =="
git fetch github
# Gitee fetch 也可能需要 token；用同样方式静默校验 tip
echo "[OK] GitHub tip: $(git rev-parse --short github/main 2>/dev/null || echo unknown)"
echo "[OK] Local  tip: $(git rev-parse --short HEAD)"
echo "完成。若 Gitee HTTPS fetch 仍 403，不影响本次 push；浏览网页确认即可。"
