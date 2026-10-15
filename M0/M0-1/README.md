# M0-1：开发环境与真实踩坑记录

作者：张驰。检查日期：2026-10-15。开发环境为 Windows 主机中的 VMware Ubuntu 虚拟机。
以下安装、版本、报错和运行结果均来自本次实际检查；原有系统安装过程没有重新执行，不能编造安装经历。

| 组件 | 实测结果 |
| --- | --- |
| 系统 | Ubuntu 22.04.5 LTS，x86_64，内核 6.8.0-138-generic |
| ROS 2 | Humble，`/opt/ros/humble`；`ros2 --help` 可用，启动脚本已加入 .bashrc |
| Python | 3.10.12，项目虚拟环境为 `~/smartcar-m0/.venv` |
| 环境管理 | uv 0.13.1，安装于 `~/.local/bin` |
| 编译工具 | gcc/g++ 11.4.0、make、cmake 3.22.1 |
| Git | 2.34.1；署名张驰，邮箱 3544516607@qq.com |
| 编辑器 | VS Code 1.142.0，安装于 `~/.local/opt/vscode`，CLI 可用 |
| 插件 | Python、C/C++、Remote SSH、Remote WSL 均已实际安装 |
| 远程工具 | ssh、scp、ssh-keygen、rsync 可用 |
| 云端仓库 | https://github.com/hello1235s/smartcar-m0 ，开发分支 codex/m0-training |

**使用与复现**

```bash
cd ~/smartcar-m0
export PATH="$HOME/.local/bin:$PATH"
source .venv/bin/activate
bash M0/M0-1/check_env.sh
```

最终环境检查结果为 **PASS=32、FAIL=0、WARN=0**，完整输出保存在 `evidence/environment_check.log`。
脚本中显示 `ros2: unknown` 是因为原题脚本调用了不受此 ros2 CLI 支持的 `--version`；
已额外通过 `ros2 --help` 验证命令可运行，没有为了显示版本号修改验收脚本逻辑。
本次只把检查脚本的 Windows CRLF 换行转为 LF，其余检查逻辑保持原题内容。

新终端会读取 .bashrc 中的用户工具路径与 ROS 配置；虚拟环境按需手动激活。
VS Code 可从应用菜单或 `code ~/smartcar-m0` 打开。本次已验证 CLI 与插件，桌面交互仍需本人实际熟悉。

**实际问题记录**

| 问题 | 现象与定位 | 处理与验证 |
| --- | --- | --- |
| VMware 主机虚拟网卡不可用 | SSH 超时；Windows 的 VMnet8 显示 Not Present，访问虚拟机走 WLAN；管理员启用设备返回“设备没有连接” | 用户在 VMware 网络编辑器取消再勾选“将主机虚拟适配器连接到此网络”；VMnet8 变为 Up，端口 22 检测成功 |
| SSH 认证未配置 | 端口连通后返回 `Permission denied (publickey,password)` | Windows 生成专用登录公钥，用户在 Ubuntu 添加到 authorized_keys 并设置目录/文件权限；随后成功登录并传输作业 |
| Python 环境管理工具缺失 | 已有系统 Python/pip，但没有 uv 或 conda | 用 Astral 官方安装器在用户目录安装 uv，建立并激活 .venv，安装依赖后验收通过 |
| VS Code 仅残留包配置 | dpkg 状态为 rc，`code` 命令和程序文件都不存在 | 在用户目录安装微软官方 Linux 发行包和开发插件；下载首次中断，断点续传后安装成功，code --version 与插件列表可用 |
| GitHub 域名指向本机 | github.com 被 /etc/hosts 映射到 127.0.0.1；SSH 服务端版本显示 Ubuntu，本地拒绝 git 用户认证 | 使用官方 ssh.github.com:443 入口，固定官方 Ed25519 主机公钥，通过仓库专用 Deploy key 推送；未改动系统 hosts |
| Bash 脚本换行错误 | `check_env.sh: $'\\r': 未找到命令`，随后出现 Bash 语法错误 | CRLF 转 LF，并加入 .gitattributes；重跑全部验收后检查脚本 32 项通过 |

**远程操作与目前边界**

实际完成：Windows → Ubuntu 的密钥 SSH 登录、SCP 文件传输；Ubuntu → GitHub 的 SSH 仓库认证与推送。
Ubuntu 已生成自己的 SSH 密钥，私钥保存在用户的 .ssh 目录，不在作业仓库。
目前没有 Jetson，尚未演示“Ubuntu 登录独立开发板并运行 M0-2”；需在借到设备或正式现场提供设备后补验。
GitHub 的 Git SSH 服务不提供普通远程 shell，不能把 Git 推送当作开发板远程操作演示。

获取板子后可以采用如下步骤（占位符要替换为真实账号和地址）：

```bash
ssh-copy-id 用户名@开发板IP
ssh 用户名@开发板IP
scp M0/M0-2/corr_tool.py M0/M0-2/config.yaml M0/M0-2/sample_data.csv 用户名@开发板IP:~/m0-demo/
```

远端目标目录、Python 与 PyYAML 需要先准备；远程运行时说明输入文件路径、工作目录及输出结果。

**参考与 AI 使用**

- 原题：https://github.com/Blake-John/22SmartCar/tree/main/round1/M0/M0-1
- ROS 安装说明：https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html
- uv 官方说明：https://docs.astral.sh/uv/getting-started/installation/
- VS Code 官方 Linux 下载：https://update.code.visualstudio.com/latest/linux-x64/stable
- GitHub SSH 443：https://docs.github.com/en/authentication/troubleshooting-ssh/using-ssh-over-the-https-port
- GitHub 服务器指纹：https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints

Codex 执行远程检查、用户级软件安装、代码测试、Git 提交和文档整理。
VMware 界面调整、Ubuntu 登录公钥授权、GitHub 仓库创建与 Deploy key 授权由用户亲自操作。
本人是否已独立复现所有步骤、是否逐行理解代码，待张驰本人确认。
