# Blog—ORS—V2.4.0

Origin Sculpture 专用 Codex Blog 自动化 Skill。

它通过固定三步完成 Shopify 博客工作流：

1. 输入一个英文选题；
2. 生成 SEO/GEO 文章、真实经验内容、自然内链、图片和最终上传版 Word，等待人工审核；
3. 只有收到当前审核版本的精确哈希确认短语后，才允许保存草稿、发布新文章或更新原文章。

## 安装

让 Codex 使用内置 Skill Installer 安装：

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo vickyfobes-ops/Blog-ORS-V2.4.0 \
  --path skills/origin-sculpture-blog
```

安装完成后，Skill 会在下一轮对话中可用，调用名为：

```text
$origin-sculpture-blog
```

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

安装后先运行只读店铺验证，不要直接发布测试文章。完整配置要求见 `skills/origin-sculpture-blog/references/shopify-setup.md`。

## 主要安全控制

- 精确哈希确认，不接受普通“好”“确认”作为发布授权；
- Shopify API 限流自动退避；
- 默认每天最多发布三篇新文章；
- `articleCreate` 和 `articleUpdate` 不盲目自动重试；
- 更新旧文章前校验 Article ID、Handle、Blog 和远程内容指纹；
- 凭证不进入 Skill、GitHub、聊天或文章运行目录；
- 至少五个自然站内链接，其中至少三个相关产品链接，并检查链接分布和有效性。

这个版本固定面向 `originsculpture.com`。其他站点必须先复制并重新配置品牌、域名、分类、模板、链接库存和 Shopify 应用，不能直接发布。
