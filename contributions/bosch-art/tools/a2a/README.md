# 本机 A2A 配置

适配用户提供的 `server.mjs`、`send.mjs`。当前使用 A2A 0.3 / JSON-RPC，工作目录为 `C:/Users/zoezi/Desktop/hack/immersetheBay`。本机服务为 Codex，队友端为 LivingRoom 的 Claude Code。

## 已配置

- 本机入口：`http://win-tqcecsev19k.tail5a410a.ts.net:41241/`
- 队友入口：`http://qinchuans-macbook-pro.tail5a410a.ts.net:41241/`
- 本机监听：`127.0.0.1:41241`；通过 Tailscale Serve 的私网 TCP 转发访问。
- 配置：项目根目录 `.env`；本机已生成独立 A2A 令牌，没有使用 Reactor 或 World Labs 密钥充当 A2A 令牌。
- 日志与验证：根目录 `.a2a/`，已加入 `.gitignore`。

本地健康检查、Agent Card、无令牌／错误令牌拒绝、有效鉴权、实际 Codex 执行与同一 contextId 续接均已通过。已从用户补充的队友配置中，将对方的 `A2A_TOKEN` 导入本机 `A2A_PEER_TOKEN`，并用对方的 `A2A_PUBLIC_URL` 设置本机对端地址。本机自己的令牌保持不变，其他 API 密钥没有导入。

跨机 Agent Card、健康检查、错误令牌拒绝与正确令牌接受均已通过。此前的纯鉴权验证只使用 `tasks/get` 查询随机不存在的任务，记录在 `.a2a/peer-verification.json`。

## 双向消息检查（2026-11-14）

用户另行授权双向消息测试后，已完成实际握手：本机发送随机口令，队友返回正确的 `A2A_FORWARD_OK`；队友再向本机发起真实回调，本机返回相同口令的 `A2A_CALLBACK_OK`。回调任务 ID、状态和文本均已与本机日志及 `tasks/get` 的实际结果交叉核对。记录在 `.a2a/bidirectional-verification.json`。

本次检查同时发现两项限制，尚未作为“自动互调完全正常”验收：

- 队友客户端进程继承的空 `A2A_PEER_TOKEN` 会遮蔽 `.env` 中非空的真实值。首次回调因此失败；仅在一次测试子进程中移除这个空变量后，回调成功。没有持久修改队友环境或文件；默认启动环境仍需整理。
- 本机后台 Codex 可以回复文本，但执行 `node --version` 的只读探测失败，错误为 `registered Core launch requires an installed app`。这与网络鉴权不同，属于本机命令运行时问题；此前一次接收端主动调用 `send.mjs` 的尝试也受此错误阻止。

因此已验证的是双向文本消息传输。接收端执行项目命令和自主回拨仍需修复并重新测试。测试没有修改业务文件、共享新凭据、重启服务或放宽权限。

## 交换连接信息

`.a2a/share-with-teammate.env` 是给队友使用的私密配置，含本机入口及本机令牌。它只写在被忽略的本地文件内，没有打印到聊天。请私下交给队友，让他加入他自己的 `.env`。

本机的队友令牌已经填好。以后对方更换令牌时，可运行下面的命令，以隐藏输入方式更新：

```powershell
.\tools\a2a\set-peer-token.ps1
```

## 使用

```powershell
node tools/a2a/send.mjs --self --health
node tools/a2a/send.mjs --self --card
node tools/a2a/send.mjs --card
```

需要向队友发起沟通时：

```powershell
node tools/a2a/send.mjs "给队友代理的具体请求"
node tools/a2a/send.mjs --context <contextId> "继续上一条会话"
```

## 启停

本机服务已在后台启动，不会随开机自动重启。停止后重新启动：

```powershell
.\tools\a2a\start.ps1
& 'C:\Program Files\Tailscale\tailscale.exe' serve --bg --tcp 41241 tcp://127.0.0.1:41241
```

停止私网转发与本项目服务：

```powershell
& 'C:\Program Files\Tailscale\tailscale.exe' serve --tcp=41241 off
.\tools\a2a\stop.ps1
```

## 本机执行策略

附件原版会关闭全部权限检查。这里改为原生 `codex.exe`、`shell:false`、stdin 传入消息，并明确使用 `--sandbox workspace-write --ask-for-approval never`。后一个选项不会授予额外权限；需要提权的操作直接失败，远程调用不能替你批准提权。没有使用 sandbox bypass、hook trust bypass 或自动审批标志。

项目沙箱限制写入范围，不应把它理解为完整的只读文件隔离。服务访问依赖 Tailscale 网络权限和独立 Bearer 令牌；只把私密连接文件交给协作对象。已知环境令牌会从返回文本和日志中打码。

所有任务串行执行；当前每次任务上限 30 分钟。取消任务时终止该任务的 Windows 子进程树。contextId 到 Codex session 的映射保存在内存，服务重启后重新建会话。

协议测试脚本：`smoke-test.mjs`。它只向本机发送两条固定的最小测试消息，不给队友发消息；结果在 `.a2a/verification.json`。Tailscale 命令参考：[官方 Serve 文档](https://tailscale.com/docs/reference/tailscale-cli/serve)。
