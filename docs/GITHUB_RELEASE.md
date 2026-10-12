# 准备 GitHub 首次发布

软件版本：0.1.0。仓库尚未创建，本轮只准备本地交付，不会自动公开你的文件。

## 推荐仓库信息

- 名称：`PyNi`
- 描述：`面向 Python 初学者的桌面学习 Agent：基础课、代码练习与理解小测。`
- 标签：`python`、`pyside6`、`desktop`、`learning`、`ai-agent`
- README 首页介绍、使用说明、测试工作流、问题模板已准备好。

创建前需要由作者确定账号、公开或私有，以及项目源码的许可证。本项目尚未擅自添加 MIT 等开源授权。第三方组件许可证已另行收录。

## 要上传什么

`release/PyNi-0.1.0-source.zip` 是明确按源码目录生成的上传底稿；不含 `.venv`、学习数据库、密钥配置、构建缓存或个人备份。解压后查看文件，再把源码提交到仓库根目录。

不要把整个桌面文件夹直接拖入仓库。Windows 程序包 `release/PyNi-0.1.0-windows-x64.zip` 和 `SHA256SUMS.txt` 应上传到版本 Release 的附件，不提交到源码目录。

准备好空仓库和 Git 后，在源码目录执行（替换 YOUR_ACCOUNT）：

```powershell
git init -b main
git add .
git status --short
git commit -m "Release PyNi 0.1.0"
git remote add origin https://github.com/YOUR_ACCOUNT/PyNi.git
git push -u origin main
```

如果 Git 未设置用户名与邮箱，根据自己的 GitHub 身份配置；不要使用示例身份提交。GitHub 要求身份验证时使用官方登录流程，不把访问令牌写进代码或聊天。

## Release 正文草稿

**Py妮 0.1.0：从基础开始的 Python 学习伙伴。**

- 五节基础课，含分层提示、练习检查、理解小测和学习记录。
- 支持 DeepSeek、OpenAI 和 Chat Completions 自定义服务。
- 真实 Agent 工具：查询进度、静态检查、阅读用户授权的代码文件夹。
- 本机草稿自动保存，支持学习备份与恢复。
- Windows x64 便携版，解压后双击 `PyNi.exe`；保留 `_internal` 目录。

本版不执行用户代码，不改写项目文件。密钥仅在当前运行内存保留。实际模型可用性由账号权限、余额和接口决定。软件未签名；首次公开发布前建议在另一台 Windows 10/11 x64 电脑完成使用验证。

## 开发者复现

Python 3.13 + Windows x64：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts/build_release.py
```

构建脚本依次运行离线/本机模拟测试、生成 onedir 程序、自检启动、压缩 Windows 包和源码包并计算 SHA-256。不会调用付费 API。构建信息保存在程序目录 `BUILD-INFO.json`。源码中的 `licenses` 已包含随附许可，构建不需要临时下载许可证。
