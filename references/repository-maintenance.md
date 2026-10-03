# Skill 发布仓库维护

## 已授权的同步范围

用户要求将可直接使用的 `xiaoshuo` 发布到 `git@github.com:zhouyanyu/xiaoshuo-skill.git`，README 详细说明用法，且以后更新此 skill 时再同步更新仓库。该约定只涵盖 skill 本身、模板、维护说明与 README，不涵盖小说原文、个人笔记、阅读进度或整个用户目录。

仓库地址：

- SSH：`git@github.com:zhouyanyu/xiaoshuo-skill.git`
- HTTPS：`https://github.com/zhouyanyu/xiaoshuo-skill.git`

SSH 不可用时，可使用现有 HTTPS 凭据访问同一仓库。不获取、打印或提交凭据。

### Windows SSH 代理兼容

本机曾出现 Windows SSH 代理已有密钥，但 Git 默认 SSH 报 `Permission denied (publickey)` 的情况。先用 Windows 自带的 `ssh-add -l` 检查已加载的公开指纹；若存在密钥，可用 `git -c core.sshCommand=C:/Windows/System32/OpenSSH/ssh.exe ls-remote <SSH仓库地址>` 测试。成功后在本 checkout 配置 `core.sshCommand`，或每次 Git 调用传入该选项。不要改全局配置，不读取私钥内容，不把这类客户端差异误报成用户没上传密钥。

## 更新流程

1. 检查本地安装的 skill 与仓库现有内容。优先复用可用 checkout；否则在当前任务工作目录克隆。不要依赖过去聊天的临时目录一定存在。
2. 获取远端最新状态，确认默认分支。已有本地变更先检查归属；不覆盖、不丢弃他人的变更，不强制推送。远端已经演进时正常合并，内容冲突不能可靠解决时说明具体阻碍。
3. 按本次请求更新安装文件，并同步到仓库根目录的 `SKILL.md`、`agents/` 和 `references/` 等相关文件。仓库目录名可以是 `xiaoshuo-skill`，但安装目录及 frontmatter 名称保持 `xiaoshuo`。
4. 用法、默认行为、文件结构或依赖变化时同步修改 `README.md`。用户特定的 GitHub 地址与维护约定保持准确，不编造不支持的功能。
5. 执行可用的 skill 结构校验，检查引用文件与 README 命令，审查 diff。只暂存此次明确涉及的发布文件，不使用无范围的提交以免混入个人资料。
6. 创建简洁的提交，正常推送到已确认的默认分支。原始请求和本约定授权此范围内的发布；无需每次重复确认，但工具权限仍需按环境处理。
7. 核对远端提交与本地提交一致，报告仓库链接和同步结果。认证或权限失败时保留准备好的改动，明确说尚未推送，不声称完成远端更新。

如果使用者 fork 到自己的仓库，只有用户明确要求才更改发布地址与同步约定。不要自动给原作者仓库推送其他使用者的定制。
