# 丑象派维护说明

## 平时你只需要做什么

以后每个插件按需放入以下目录，然后把文件提交到 GitHub 的 main 分支即可：

- 插件图标：\`assets/icons/插件名称.png\`
- 插件截图：\`assets/screenshots/插件名称/\`
- 中文资料：\`metadata/packages/插件名称.json\`
- 当前版本安装包：\`pool/main/插件标识_版本_iphoneos-arm64.deb\`
- 历史版本安装包：\`pool/old/插件名称/\`

每个插件的 JSON 资料使用中文字段。请保持“软件包标识”与 .deb 内的 Package 字段一致；“当前版本”与当前安装包版本一致。截图、图标文件名和 JSON 中填写的路径必须一致。

## 自动发布流程

每次向 main 分支提交后，GitHub Actions 会自动：

1. 安装 APT 索引构建工具。
2. 扫描 \`pool/main/\` 和 \`pool/old/\` 中的所有 .deb。
3. 读取安装包真实的 Package、Version、Architecture、依赖等信息。
4. 结合中文 JSON 生成 Sileo 原生详情 JSON 和网页详情页。
5. 自动关联插件图标、截图、介绍、版本资料、历史版本和更新日志。
6. 生成标准 APT 的 Packages、Packages.gz、Packages.xz。
7. 同步根目录兼容用的 Packages、Packages.gz、Packages.xz。
8. 重新计算标准 Release 和根目录 Release 的 MD5、SHA1、SHA256、SHA512。
9. 部署整个软件源到 GitHub Pages。

你不需要手工修改 Packages、Release，也不需要计算哈希。自动生成的索引和详情文件会随 GitHub Pages 发布；它们是在 Actions 构建时生成，不要求你手工维护这些生成文件。

## 重要规则

- 当前版本 .deb 放在 \`pool/main/\`。
- 旧版本 .deb 放在 \`pool/old/插件名称/\`。旧版本仍会被加入 APT 多版本索引。
- 不要把不同插件的 .deb 混放到同一个旧版本目录以外的路径。
- 同一个软件包标识、版本号、架构不能重复出现。
- 图标和截图如果尚未上传，自动构建会先跳过对应图片，不会拿软件源头像冒充插件图标。
- “支持的系统”未确认时显示“暂未确认”，不要猜测。
- 只有 GitHub Actions 显示部署成功后，才代表新版本已发布到网站。
- Release 当前未配置 GPG 签名密钥，不能称为已签名软件源。

## 番茄音乐示例

- 插件名称：番茄音乐
- 软件包标识：\`com.oliixwxiilo.fqmusic\`
- 当前版本：\`1.0\`
- 当前安装包：\`pool/main/com.oliixwxiilo.fqmusic_1.0_iphoneos-arm64.deb\`
- 中文资料：\`metadata/packages/番茄音乐.json\`
- 图标路径：\`assets/icons/番茄音乐.png\`
- 截图目录：\`assets/screenshots/番茄音乐/\`

番茄音乐目前还没有实际上传插件图标和截图，所以这两项暂时不会显示；把图片放入上述位置并提交后，自动构建就会加入详情页。
