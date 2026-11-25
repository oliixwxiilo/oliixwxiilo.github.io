# 丑象派维护说明

## 平时只需要上传什么

每个插件按需放入以下目录，然后提交到 GitHub 的 main 分支：

- 当前版本安装包：`pool/main/`
- 插件图标：`assets/icons/`
- 插件截图：`assets/screenshots/插件名称/`
- 可选中文资料：`metadata/packages/`
- 历史版本安装包：`pool/old/插件名称/`

**基础发布只需要 .deb。** 图标和截图不需要在 JSON 里逐条登记，构建脚本会自动匹配。

## 图标自动匹配规则

把图标放入 `assets/icons/`，文件名可以使用：

1. 完整软件包标识，例如 `com.example.plugin.png`。
2. 软件包标识最后一段，例如 `plugin.png`。
3. 插件显示名称，例如 `我的插件.png`。

支持 PNG、JPG、JPEG、WEBP。JSON 中如果填写了有效的“插件图标”路径，则优先使用该路径；路径失效时会继续自动匹配。

## 截图自动匹配规则

把截图直接放进对应插件目录，例如：

`assets/screenshots/番茄音乐/`

目录名称可以是插件显示名称、完整软件包标识，或软件包标识最后一段。构建时会自动收集该目录及其子目录中的图片，不需要逐张填写 JSON。

也支持把截图直接放在 `assets/screenshots/` 根目录，并使用插件名称或软件包标识作为文件名前缀。支持 PNG、JPG、JPEG、WEBP。

如果 JSON 中填写了有效的“插件截图”路径，会先显示这些图片，再补充自动发现的截图；重复图片只显示一次。无效路径会跳过并继续自动查找。

## 可选中文资料

`metadata/packages/插件资料.json` 用于补充自动无法可靠推断的内容：

- 插件介绍
- 更新日志
- 支持的系统
- 上传日期
- 历史版本下载信息
- 特殊图标或截图路径

没有 JSON 时，系统仍会从 .deb 读取软件包标识、版本、架构、依赖等信息，生成基础详情。不会自动编造介绍、更新日志或系统兼容性。

## 自动发布流程

提交到 main 分支后，GitHub Actions 会自动：

1. 扫描 `pool/main/` 和 `pool/old/` 中的 .deb。
2. 读取安装包真实的 Package、Version、Architecture 和依赖信息。
3. 自动匹配图标和截图，读取可选中文资料。
4. 生成 Sileo 原生详情 JSON 和网页详情页。
5. 生成 Packages、Packages.gz、Packages.xz。
6. 重新计算 Release 文件中的 MD5、SHA1、SHA256、SHA512 校验值。
7. 部署到 GitHub Pages。

不要手工修改自动生成的 Packages、Release 和详情文件。只有 GitHub Actions 显示部署成功后，才代表新内容已发布。

## 其他规则

- 当前版本 .deb 放在 `pool/main/`。
- 历史版本 .deb 放在 `pool/old/插件名称/`。
- 同一个软件包标识、版本号、架构不能重复。
- 未上传的图标或截图会被跳过，不会用软件源头像冒充。
- “支持的系统”未确认时显示“暂未确认”，不会猜测。
- Release 当前未配置 GPG 签名密钥，因此不是已签名软件源。
