# Blog—ORS—运营修订版 V2.6.1 安装提示词

把下面整段发给运营电脑上的 Codex：

```text
请安装并验证独立共存的 Origin Sculpture Blog 运营修订版 V2.6.1，不要覆盖或删除旧版。

- GitHub 仓库：vickyfobes-ops/Blog-ORS-V2.4.0
- Git 分支：codex/origin-sculpture-blog-ops-v2-6-1
- Skill 路径：skills/origin-sculpture-blog-ops-v2-6-1
- 安装目录与调用名：origin-sculpture-blog-ops-v2-6-1
- 安装后调用：$origin-sculpture-blog-ops-v2-6-1

安装要求：
1. 使用 Codex 内置 Skill Installer 从上述分支和路径安装，不覆盖 $origin-sculpture-blog 或 $origin-sculpture-blog-ops-v2-6-0。
2. 检查 SKILL.md 的 name 为 origin-sculpture-blog-ops-v2-6-1，metadata.version 为 2.6.1，运行 Skill Creator 的 quick_validate。
3. 在当前 Windows 电脑调用 workspace dependencies，使用所给文档 Python 和 render_docx.py 运行本 skill 的 scripts/self_test.py；不要套用 Mac 路径。缺少 LibreOffice/soffice.exe 或渲染器时准确报告缺失依赖并停止，不能跳过自检。
4. 只有 self_test 返回 status=PASS 才处理正式文章。不要把 token、.env 或运行记录放进 skill 或 GitHub；沿用电脑上现有的受保护 Shopify 配置。

本版正文结构：Shopify article.html 不写 H1，先写直接回答问题的段落，再写 H2/H3；Word 审核稿可以显示标题。不要复制 WordPress 外层容器、WordPress 页级内联样式或重复 H1。把 meta.json.title 当作期望由 Shopify 主题渲染的唯一 H1。建议人工发布或执行正式发布之前，只读检查同一文章模板的公开页面确实输出一个包含文章标题的 H1；不能确认时保留已授权草稿未发布并告知我，不要往正文硬塞 H1。

继续遵守原有证据、图片、内链、运营修订边界和哈希确认规则；不要因此修改任何现有 Shopify 文章或模板。
```
