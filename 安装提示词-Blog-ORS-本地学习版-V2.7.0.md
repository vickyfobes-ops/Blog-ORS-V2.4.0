# Blog—ORS—本地学习版 V2.7.0 安装提示词

把下面整段发给运营电脑上的 Codex。它会独立安装新版并完成全部初始化；安装成功后运营只需输入选题：

```text
请安装并验证独立共存的 ORS Blog 本地学习版 V2.7.0，不要覆盖或删除任何旧版。

仓库：vickyfobes-ops/Blog-ORS-V2.4.0
分支：codex/origin-sculpture-blog-ops-v2-7-0
路径：skills/origin-sculpture-blog-ops-v2-7-0
安装名与调用名：origin-sculpture-blog-ops-v2-7-0

请使用内置 Skill Installer 完成安装，然后：
1. 确认 SKILL.md 的 name 是 origin-sculpture-blog-ops-v2-7-0，版本是 2.7.0，并运行 quick_validate。
2. 调用本机 workspace dependencies，用文档 Python 和 render_docx.py 运行 scripts/self_test.py。Windows 应定位本机 LibreOffice/soffice.exe 并使用实际路径，不能套用 Mac 路径；依赖确实缺失时只报告阻塞，不得跳过自检。
3. 运行 scripts/local_memory.py context --handle installation-probe。让新版自动发现本机工作区、Documents、Desktop、Downloads、OneDrive 中已有的 origin-blog-runs；不要要求我提供路径或手动运行 bootstrap。
4. 运行 scripts/local_memory.py status --verbose，确认本地记忆位于 skill 目录之外，且自动发现状态已经生成；升级或重装不得清空。
5. 确认此版 description 被识别为 ORS Blog 最新默认工作流。以后运营只输入普通选题就自动使用本版，不要求她输入调用名或做初始化；需要排查时才显式调用 $origin-sculpture-blog-ops-v2-7-0。

本次只授权安装、自动读取本地历史和离线验证；不要访问、修改或发布任何 Shopify 内容，也不要删除旧版或旧运行记录。
```
