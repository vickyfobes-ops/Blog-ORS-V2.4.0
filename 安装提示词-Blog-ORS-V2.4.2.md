# Blog—ORS—V2.4.2 安装／更新提示词

把下面整段发给另一台电脑上的 Codex：

```text
请使用 Codex 内置的 skill-installer，从 GitHub 安装 Blog—ORS—V2.4.2：

- 仓库：vickyfobes-ops/Blog-ORS-V2.4.0
- 分支：codex/origin-sculpture-blog-v2.4.2
- Skill 路径：skills/origin-sculpture-blog
- 安装名：origin-sculpture-blog

安装前先检查 ~/.codex/skills/origin-sculpture-blog：
1. 如果不存在，直接用 skill-installer 安装指定分支和路径。
2. 如果已存在旧版，不要覆盖或删除；先将旧目录移动为带时间戳的同级备份，再用 skill-installer 安装 2.4.2。
3. 安装后完整运行 Skill Creator 的 quick_validate，并确认 SKILL.md 的 metadata.version 为 2.4.2、agents/openai.yaml 显示 Blog—ORS—V2.4.2、scripts/verify_publish_docx.py、Libre Baskerville/Poppins 四个字体文件和 assets/format-reference/latest-format-page-1.png 都存在。
4. 扫描安装目录，确认没有 .env、Shopify Token、Client Secret、日志、数据库或店铺凭证。
5. 不要配置或调用 Shopify 发布；只完成安装和只读验证。告诉我安装结果，并提醒我在下一轮对话调用 $origin-sculpture-blog。
```

新安装也可以直接执行：

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo vickyfobes-ops/Blog-ORS-V2.4.0 \
  --path skills/origin-sculpture-blog \
  --ref codex/origin-sculpture-blog-v2.4.2
```

已安装的 Skill 不会自动从 GitHub 更新；旧版电脑需要按上面的更新流程重新安装。
