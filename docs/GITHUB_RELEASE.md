# Windows 发行包

项目仓库为 [Xiao2255/Py-NI](https://github.com/Xiao2255/Py-NI)。发布 0.3.0 的 Windows 体验版时，使用同一提交构建的以下三个文件：

- `release/PyNi-0.3.0-windows-x64.zip`
- `release/PyNi-0.3.0-source.zip`
- `release/PyNi-0.3.0-SHA256SUMS.txt`

在 GitHub Releases 中选择与源码对应的标签 `v0.3.0`，附上以上文件，发布说明可引用 [更新记录](../CHANGELOG.md)。

## 复现构建

在 Windows 的 Python 3.13 虚拟环境中安装 `requirements-dev.txt`，运行：

```powershell
.\.venv\Scripts\python.exe scripts/build_release.py
```

脚本运行测试、打包、自检正式 EXE、解压并在无 Python PATH 的环境中自检，最后生成源码包及 SHA-256。GitHub 发布需自行操作，构建脚本不会上传文件。
