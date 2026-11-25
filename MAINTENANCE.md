# oliixwxiilo Repo 维护说明

## 网站内容
- 首页：`index.html`，只维护外部商店入口和页面文字，不放第三方插件下载按钮。
- 头像与网页图标：`assets/repo-avatar.jpg`。
- 修改以上文件并推送到 `main` 后，GitHub Actions 会自动部署 GitHub Pages。

## APT 软件包
本源使用 Rootless iOS 架构 `iphoneos-arm64`，发行版 `stable`，组件 `main`。

1. 将已确认可用于 Rootless 的 `.deb` 文件放入 `pool/main/`。
2. 在 Debian/Ubuntu 或 Theos 构建环境中安装 `dpkg-dev`、`gzip`、`xz-utils`。
3. 在仓库根目录运行：`bash scripts/rebuild-apt-index.sh`。
4. 检查生成的 `dists/stable/main/binary-iphoneos-arm64/Packages`、压缩索引和 `dists/stable/Release`。
5. 将 `.deb`、索引和 Release 一并提交到 `main`。Actions 成功后，等待 Pages 更新。
6. 在 Sileo/Zebra 刷新软件源，检查包名、版本、依赖和安装结果。

不要手工填写 Packages 的校验和。脚本会从实际文件重新生成 MD5、SHA1、SHA256、SHA512 和文件大小，避免 Release 与索引不匹配。

## 当前已发布
- `com.oliixwxiilo.fqmusic`（番茄音乐）1.0，Rootless 架构 `iphoneos-arm64`。
- 安装依赖：`mobilesubstrate`。
- 本包由仓库维护者提供；上传前已核对 deb 控制信息与文件清单。仍需在目标设备上验证安装、注入和运行效果。
- 目前没有发布签名密钥；若未来需要提高 APT 信任保障，可再规划 Release 签名（InRelease/Release.gpg）。

## 日常维护
- 只改网站：修改 `index.html`，提交到 `main` 即可。
- 更换头像：替换 `assets/repo-avatar.jpg`，保持首页引用路径不变。
- 发布/更新插件：放入 `pool/main/`，运行索引脚本，再提交包与索引。
- 每次提交后检查 GitHub Actions 的 `Deploy GitHub Pages` 工作流为绿色成功状态。
