# Blog—ORS—本地学习版 V2.7.0 安装提示词

把下面整段发给运营电脑上的 Codex。它会独立安装新版、扫描这台电脑已有的 ORS 运行记录，并保留旧版：

```text
请安装并验证独立共存的 ORS Blog 本地学习版 V2.7.0，不要覆盖或删除任何旧版。

仓库：vickyfobes-ops/Blog-ORS-V2.4.0
分支：codex/origin-sculpture-blog-ops-v2-7-0
路径：skills/origin-sculpture-blog-ops-v2-7-0
安装名与调用名：origin-sculpture-blog-ops-v2-7-0

请使用内置 Skill Installer 完成安装，然后：
1. 确认 SKILL.md 的 name 是 origin-sculpture-blog-ops-v2-7-0，版本是 2.7.0，并运行 quick_validate。
2. 调用本机 workspace dependencies，用文档 Python 和 render_docx.py 运行 scripts/self_test.py。Windows 应定位本机 LibreOffice/soffice.exe 并使用实际路径，不能套用 Mac 路径；依赖确实缺失时只报告阻塞，不得跳过自检。
3. 在本机查找既有 origin-blog-runs 目录；对每个真实历史根目录运行 scripts/local_memory.py bootstrap --runs-root <绝对路径>。如果没有历史目录，就初始化空账本并明确说明“只能保护从现在开始的记录”。
4. 运行 scripts/local_memory.py status --verbose，确认本地记忆保存在 skill 目录之外；升级或重装不得清空。
5. 只有 quick_validate、自检和本地记忆初始化均成功后，才报告可用调用：$origin-sculpture-blog-ops-v2-7-0。

本次只授权安装、读取本地历史和离线验证；不要访问、修改或发布任何 Shopify 内容，也不要删除旧版或旧运行记录。
```
