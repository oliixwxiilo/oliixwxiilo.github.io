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


## 软件包资料维护

- repo-config.json：人工维护插件展示名称、介绍、主页、iOS 范围、兼容性实测状态和更新日志。
- catalog.json：自动生成的主页目录。
- version-history.json：从当前 APT 索引归集各包已保留的版本、文件名和 SHA256。
- depictions/<包名>/<版本>/index.html：自动生成的插件详情页。

编辑 repo-config.json 时，使用 DEB 的准确 Package 字段作为键。兼容性状态建议使用 unknown、tested 或 not-tested 等明确值；没有设备实测记录时请保持 unknown。iOS 版本范围留空表示尚未确认。更新日志日期必须来自真实发布记录，不要推测。


## 发布安全与依赖审计

- `scripts/audit-debs.py`：逐个检查 DEB 控制字段、文件大小及 SHA256 与 APT 索引是否一致。
- `scripts/audit-dependencies.py`：区分仓库内可满足的依赖与需要由外部越狱基础源提供的依赖；外部依赖不自动视为错误。
- `dependency-audit.json`：自动生成的依赖审计结果。
- `scripts/check-release-safety.sh`：发布前对照 `main`，阻止删除或替换任何既有 DEB，并核对原软件源地址。
- `.github/workflows/release-safety.yml`：面向合并到 `main` 的 Pull Request 执行发布安全门禁；只有检查通过后才适合人工审阅合并。

当前阶段不自动合并到 `main`，也不自动覆盖生产软件源。依赖审计只检查本仓库是否提供依赖；标记为 `external-or-virtual` 的项目通常需要由用户已添加的越狱基础源提供，不能单凭该标签判断为安装失败。
