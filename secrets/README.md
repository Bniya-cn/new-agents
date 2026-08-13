# secrets/ — 凭证存放说明

这里只放**本地加密凭证**，不进 git。

## Gitee Token（推荐流程）

1. 复制示例文件：

```bash
cp secrets/gitee.token.in.example secrets/gitee.token.in
```

2. 用编辑器打开 `secrets/gitee.token.in`，把私人令牌粘贴进去（单行，不要引号）。

3. 立即加密入库并擦除明文：

```bash
./scripts/secure_store_gitee_token.sh
```

会生成：

- `secrets/gitee.token.enc` — AES-256-CBC 密文（本地文件，已 gitignore）
- macOS 钥匙串条目 `healing-agents-gitee-token` — 运行时优先从这里取（非明文文件）

4. 推送（自动取 token，不回显）：

```bash
./scripts/push_remotes.sh
```

## 安全约束

- `secrets/gitee.token.in` 只是一次性输入盒；加密成功后会被覆盖清空并删除。
- 仓库内**不允许**提交明文 token。
- 密文文件也已 gitignore；丢失可重新用新 token 走上述流程。
- 不要把 token 写进 `README`、聊天记录、commit message。
