# Oliixwxiilo 越狱软件源

个人自用 APT 软件源，提供 Rootless 与 RootHide 软件包。

**软件源地址：** https://oliixwxiilo.github.io/

## 兼容性

可在 Sileo、Zebra、Installer 及其他兼容 APT 的软件包管理器中添加。软件包是否适用取决于其自身的架构、越狱类型、iOS 版本和依赖，请以每个软件包的元数据为准。

## 仓库维护

- `*.deb`：当前阶段保留在仓库根目录，避免改变既有下载路径。
- `Packages` / `Packages.gz`：由 `scripts/build-repo.sh` 生成。
- `Release`：包含索引文件校验和及 arm64、arm64e 架构声明。
- `scripts/validate-repo.sh`：检查索引压缩一致性、必需字段和 DEB 文件是否存在。
- `.github/workflows/build-repo.yml`：在软件包或索引构建脚本变更时自动构建、验证并提交索引。

## 本地构建

在安装了 `dpkg-dev` 的 Linux 环境运行：

```sh
bash scripts/build-repo.sh
bash scripts/validate-repo.sh
```

## 安全与发布原则

重构先在 `refactor/modern-apt` 分支验证，不直接修改 `main`。现有 DEB 文件名和 URL 暂时保持不变；任何软件包迁移、删除或元数据变更都应先检查兼容性并单独审阅。
