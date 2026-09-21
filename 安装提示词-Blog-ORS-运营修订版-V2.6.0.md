# Blog—ORS—运营修订版 V2.6.0 安装提示词

把下面整段发给运营电脑上的 Codex：

```text
请安装独立共存的 Origin Sculpture Blog 运营修订版，不要覆盖或删除旧版。

- GitHub 仓库：vickyfobes-ops/Blog-ORS-V2.4.0
- Git 分支：codex/origin-sculpture-blog-ops-v2-6-0
- Skill 路径：skills/origin-sculpture-blog-ops-v2-6-0
- 安装目录与调用名：origin-sculpture-blog-ops-v2-6-0
- 安装后调用：$origin-sculpture-blog-ops-v2-6-0

安装要求：
1. 使用 Codex 内置 Skill Installer 从上述仓库、分支和路径安装。
2. 不要覆盖、删除或重命名已有的 $origin-sculpture-blog；新版本必须与旧版并存。
3. 安装后检查 SKILL.md：name 必须是 origin-sculpture-blog-ops-v2-6-0，metadata.version 必须是 2.6.0。
4. 运行 Skill Creator 的 quick_validate。
5. 调用 workspace dependencies，使用当前电脑提供的文档 Python 和 render_docx.py 运行 scripts/self_test.py。Windows 不要使用 Mac 路径；如果自检报告缺少 LibreOffice/soffice.exe 或文档渲染器，报告准确缺失依赖后停止，不得绕过验证。
6. 只有 self_test 输出 status=PASS，才能处理正式文章或 Shopify。
7. 不要把 token、client secret、.env、Shopify 配置、文章运行记录或缓存写进 skill 或 GitHub。既有受保护的 Shopify 配置可继续使用，无需复制凭证。

本版本的额外能力是“运营修订审计”：运营修改文章后，先输出 operator-revision-record.md，分开记录实际差异、有限复用模式、局部修改、禁止推导事项和待确认问题。未获得明确确认或重复证据前，不得把单篇修改升级为全局规则。
```

如果需要命令行安装，使用当前电脑的 Codex Skill Installer，目标必须是上述 Git 分支和 `skills/origin-sculpture-blog-ops-v2-6-0` 路径。
