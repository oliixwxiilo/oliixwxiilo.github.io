# 丑象派维护说明

## 网站内容
- 首页：`index.html`，维护商店入口和中文页面文字。
- 软件源头像与网页图标：`assets/repo-avatar.jpg`。
- GitHub 的 `main` 分支更新后，会自动触发网页部署。

## 插件资料目录
- 插件图标：`assets/icons/`，建议使用正方形 PNG 图片。
- 插件截图：`assets/screenshots/插件名称/`，可放多张 PNG、JPG 或 WebP 图片。
- 插件介绍、版本资料、更新日志：`metadata/packages/插件名称.json`。
- 当前版本安装包：`pool/main/`。
- 历史版本安装包：`pool/old/插件名称/`。

每个插件的资料模板使用中文字段，包含插件名称、版本号、图标、截图、介绍、更新日志、旧版本、支持的系统、安装包大小和上传日期。暂时不确定的资料留空，不要猜测。

## APT 软件包
本源使用 Rootless iOS 架构 `iphoneos-arm64`，发行版 `stable`，组件 `main`。

1. 将当前版本的 `.deb` 放入 `pool/main/`。
2. 将旧版本的 `.deb` 放入 `pool/old/插件名称/`，不要放进当前版本索引目录。
3. 更新对应的 `metadata/packages/插件名称.json`。
4. 在仓库根目录运行：`bash scripts/rebuild-apt-index.sh`。
5. 检查生成的索引和 Release 文件，提交所有变更。
6. 等待 GitHub Pages 部署成功，再在 Sileo/Zebra 刷新软件源。

不要手工填写索引校验值。索引脚本会根据实际安装包重新生成校验信息。

## 当前已发布
- 番茄音乐 1.0，软件包标识：`com.oliixwxiilo.fqmusic`。
- 安装依赖：`mobilesubstrate`。
- 安装包大小：6164 字节。
- 支持的系统版本尚未确认，因此资料模板中暂时留空。
- 尚未配置 Release 签名密钥。
