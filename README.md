# Blog—ORS—运营修订版 V2.6.1

Origin Sculpture 专用 Codex Blog 自动化 Skill。这个版本与旧版并存，专门加入“运营修订审计”：先对比生成稿、运营改稿和 Shopify 状态，再把有证据的模式写成带适用边界的规则。

它通过固定三步完成 Shopify 博客工作流：

1. 输入一个英文选题；
2. 生成 SEO/GEO 文章、真实经验内容、自然内链、图片和最终上传版 Word，等待人工审核；
3. 只有收到当前审核版本的精确哈希确认短语后，才允许保存草稿、发布新文章或更新原文章。

## 安装

让 Codex 使用内置 Skill Installer 安装独立 skill：

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo vickyfobes-ops/Blog-ORS-V2.4.0 \
  --path skills/origin-sculpture-blog-ops-v2-6-1 \
  --ref codex/origin-sculpture-blog-ops-v2-6-1
```

安装完成后，Skill 会在下一轮对话中可用，调用名为：

```text
$origin-sculpture-blog-ops-v2-6-1
```

旧版 `$origin-sculpture-blog` 和运营 V2.6.0 都不会被覆盖；三个调用名可并存。它们使用同一份受保护的 Shopify 配置，但安装包本身不含凭证。

## 本次结构规则

Shopify 正文是 body-only HTML，不含 H1，以直接回答问题的段落开头，随后用 H2/H3 组织子问题。公用标题存于 `meta.json.title`，作为主题预期渲染的唯一 H1；Word 审核稿可显示标题，但不得复制 WordPress 外层容器或正文 H1 到 Shopify。上线前须只读核实同一文章模板在公开页面输出的唯一 H1；如无法确认，可保存已授权草稿，但不要建议人工直接发布。

## 运营修订审计

当运营修改过文章时，本版会先生成 `<run-dir>/operator-revision-record.md`，把实际差异、可有限复用的模式、只适用于当前文章的改动、禁止推导事项和待确认问题分开记录。只有用户明确要求，或多个已批准修订重复证明同一模式时，才更新长期规则。

## Shopify 配置

仓库不包含任何店铺凭证。每个使用者必须在自己的设备上单独配置：

```text
~/.config/origin-sculpture-blog/shopify.env
```

只申请以下权限：

- `read_content`
- `write_content`
- `read_files`
- `write_files`

安装后先运行只读店铺验证，不要直接发布测试文章。完整配置要求见 `skills/origin-sculpture-blog-ops-v2-6-1/references/shopify-setup.md`。

## 安装后强制自检

V2.6.1 把“能安装”和“能稳定生成正确成品”分开验证。全新安装或更新后，必须先运行：

```bash
python3 skills/origin-sculpture-blog-ops-v2-6-1/scripts/self_test.py
```

自检只在本机创建隔离测试包，不读取店铺凭证、不访问 Shopify、不上传或发布内容。只有输出 `"status": "PASS"` 后，才允许处理正式文章。它会验证固定字体、文章规则、AI 场景图比例、每篇 2–3 张 Origin 站内图片、1600×900 PNG/WebP 格式、人工视觉确认字段、Word 生成与结构、页面渲染对比，并确认错误字体、不合格图片、不合格文章和明显版式漂移能够被拦截。V2.6.1 还会拒绝重复正文 H1、外层 WordPress 容器和 H2 之前的 H3；跨平台容差视觉几何校验保持不变。

## 主要安全控制

- 精确哈希确认，不接受普通“好”“确认”作为发布授权；
- Shopify API 限流自动退避；
- 默认每天最多发布三篇新文章；
- `articleCreate` 和 `articleUpdate` 不盲目自动重试；
- 更新旧文章前校验 Article ID、Handle、Blog 和远程内容指纹；
- 凭证不进入 Skill、GitHub、聊天或文章运行目录；
- 至少五个自然站内链接，其中至少三个相关产品链接，并检查链接分布和有效性。
- 以当前线上 `sculpture-finish-guide` 的 Origin 文章结构和商家最终确认的 Word 成品为唯一版式真源；全黑文字、Libre Baskerville 标题、Poppins 正文、图片尺寸与分页均由生成器和校验器锁定；两套字体的常规/粗体都嵌入 DOCX，避免 Windows 与 Mac 字体回退；
- 禁止使用 Word 默认蓝色标题、衬线正文、通用报告模板或临时脚本降级生成；依赖缺失时直接停止 Word 交付；
- Pillar Blog 固定 1,800–2,500 词，Supporting Blog 固定 1,000–1,600 词；主题相关 Origin 真实经验占正文 10–20%，不得虚构项目、数据或客户偏好；
- 每篇使用 6–8 张图片，其中 2–3 张必须来自当前 Origin 产品或项目页面，并保留来源页和原始媒体地址；所有图片统一为 1600×900 PNG（Word）与 WebP（Shopify）；
- AI 写实场景图占图片清单至少 60%，封面默认为 AI 环境场景；网页、电脑/手机屏幕、商城 UI、文字、Logo 和水印不得作为主画面；Origin 产品/项目图只作为相关证据；
- 每张图片必须经过实际视觉检查并记录四项布尔确认：已查看、无屏幕/UI/文字/Logo、材质与尺度可信、与所在章节相关；缺一项或任一项为否即停止交付；
- 定制流程、下单、服务、公司类文章使用 `site-led`：围绕普通客户问题和 Origin 站内内容写，技术流程约占 20–30%；材料、finish、趋势、灵感、维护、安装和场地规划使用 `expert-led`，可用专业术语但必须首次解释并落到客户决策。

这个版本固定面向 `originsculpture.com`。其他站点必须先复制并重新配置品牌、域名、分类、模板、链接库存和 Shopify 应用，不能直接发布。
