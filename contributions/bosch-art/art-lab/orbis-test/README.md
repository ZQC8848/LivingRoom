# 博斯全景：Orbis 实测

## 当前版本：按物体分层的混合制作（v6，2026-11-14）

打开 `../bosch-orbis-v6.html`。各“看……”按钮转向对应动作并放大检查，“回到全景视野”恢复广角；转头与手势揭示保持可用。最终每个状态仍是一条 2:1 全景视频，不使用六面墙分别播放。本轮没有新增模型调用，Orbis 原始试片入口仍保留历史生成结果，文字区分该素材是否用于新版。

v5 的矩形树冠光流导致树下建筑热浪形变，动物整块 RGB 出现区域曝光漂移，水面亮度残差不易察觉，火光亮度残差呈现抖动。v6 停用这些处理方式：

- 树：从原画分离四处树冠与枝干，补出静态背景，围绕各自枝干锚点摆动约 1.8–2.8 度。只变换物体抠图，建筑另有固定前景保护；不再使用模型光流。
- 水：整片河道按色彩和岸线建立蒙版，单独排除蓝色建筑、岛屿与动物。对原画水纹做连续周期位移及弱高光变化；岸线和建筑保持固定。这是可控二维动画，未伪称为模型生成。
- 鸟与白马：沿用 `run-dynamic-v2`；背景特征配准轨迹先做平滑，利用物体外的固定背景拟合曝光并修正缓慢空间偏色，再逐帧分离主体。只合成主体 alpha，固定底图不接受生成的矩形背景。鸟的原画腿脚保持固定；白马细腿另用原画保护。
- 火：沿用 `fire/run-stable-01`，稳像、曝光匹配、时间平滑后提取火焰的色彩和动态轮廓。静态暗色城墙在火焰前方遮挡；舍弃上一版整块亮度残差。

输出为 `delivery-v3/`。两个状态各为 2048×1024、30 fps、六秒的后期循环，包含往返重采样，非模型原生无缝循环。页面播放已有录像，不开实时模型会话。当前桌面仍解码两种状态合成手势蒙版，Quest 单路中继与头显质量尚未验收。

对话内视频也保留 2048×1024，采用较高压缩率；本地完整版码率更高。球面纹理水平方向使用周期采样 `REPEAT`，保持视频及静帧纹理为二次幂尺寸；WebGL 1 中不应将此设置直接用于 1536 等非二次幂纹理。修订后人工复查了对话内球面接缝与局部放大视图。

制作脚本 `../compose_bosch_v6.py`；页面模板／构建 `../bosch-orbis-v6.fragment.html`、`../build_bosch_orbis_v6.py`。物体缓存 `delivery-v3/*-object-cache.npz` 可加快后续合成；改变分割或曝光算法时需重建对应缓存。

验证记录：

- `delivery-v3/report.json`：编码前被保护建筑、城墙变化为 0，鸟的物体合成未改变蒙版支持区外的背景。
- `delivery-v3/regression-audit.json`、`../audit_bosch_v6.py`：每条编码后视频抽取 36 帧。鸟旁固定草地区域的平均亮度范围从 v5 的 21.73/255 降至 0.0203/255；树下建筑的平均逐像素时间标准差为 0.0073/255。前景水纹保持运动，中心蓝色建筑不动。数字是所选区域的检查，不代表所有感知质量已被证明。
- `delivery-v3/object-review.jpg`：四个时刻的鸟、树、水、火局部人工查看；另查看全景及放大后的浏览器截图。
- `../review/bosch-orbis-v6/verification.json`：浏览器播放、无自动转头、五处动作变化、手势揭示、2:1 排版、原始素材对照、暂停、窄屏布局通过。完整页面使用 2048×1024 视频；对话版是压缩预览。

## 历史版本：Dynamic 动作修订（v5，2026-11-14）

打开 `../bosch-orbis-v5.html`，使用“看白马／看鸟翼／看树叶”定位新动作；可暂停、转头、用手势蒙版揭示地狱，以及对照模型原始输出。本轮实际完成三个 Dynamic 六秒测试，均正常释放会话，未干预其他人的会话。首帧约 6.2–6.3 秒，分别记录 109／108／114 帧。之前五次容量失败属于历史测试，本轮没有发生。

- 白马：重新生成闭口低头动作，保留小型独角兽与长角；在最终循环的 16 个均匀抽样时刻中未再看到嘴部白沫。动物的生成纹理仍有轻微变化，不能将抽样审阅等同于模型身份稳定性的保证。
- 鸟：实际生成展翅与翼拍，双脚留在原处。扩大并羽化局部蒙版以容纳翼尖，使用稳像后的 RGB，旧版静态鸟已被替换。
- 树冠：提取 Dynamic 光流，将位移放大 4 倍，上限为源画 7 像素；用该位移驱动原画树叶，舍弃生成颜色变化，避免把颗粒闪烁当作运动。旧版上限为 1.1 像素。
- 水面和火光：沿用已审阅的 Stable 结果和处理方式，没有重新调用。

动物与树冠的六秒源片被压缩到约三秒，再正向／反向组成六秒循环；不是原生无缝生成。最终每种状态各是一条 2:1 全景视频。当前桌面页面解码两种状态用于手势合成；尚未验证 Quest 单路中继或头显性能。

新输出在 `delivery-v2/`，旧版 `delivery/` 保留。新动物／树冠运行分别位于 `horse/run-dynamic-v2/`、`bird/run-dynamic-v2/`、`leaves/run-dynamic-v2/`，内含真实提示词、逐帧输出与记录。处理脚本为 `../composite_orbis_painting_v2.py` 和 `../build_bosch_orbis_v5.py`。

浏览器检查记录为 `../review/bosch-orbis-v5/verification.json`：视频播放、五处局部变化、无自动转头、手势移动蒙版、2:1 排版、原始片段对照、暂停和窄屏检查均通过。另人工检查全景、翼尖和嘴部对照帧。编码前活动蒙版外变化像素数为 0；有损编码仍会产生误差。最终抽样图为 `delivery-v2/final-motion-contact.jpg` 与 `delivery-v2/horse-muzzle-review.jpg`。

## 以下为上一版 Stable 测试记录

本轮已经实际调用 Reactor 的 Orbis API，使用用户提供的本地 `.env` 中的 Reactor 密钥。没有调用 World Labs 生成新场景；继续使用已经批准的花园／地狱空间草稿。密钥没有写入浏览器、视频或测试记录。

## 查看

打开 `../bosch-orbis.html`，可转头、切换花园／地狱、移动手势蒙版、暂停六秒循环、定位水面／枝叶／火光，以及查看五类原始输出并与输入图对照。

对话内版使用压缩视频；完整本地版播放 2048×1024 的全景。两种状态各自为完整 2:1 画面，不使用六面墙视频。当前桌面原型解码两种状态并合成显示，尚未接入队友的 Quest 单路视频中继，也未进行头显性能验收。

## 实际执行与结论

- Orbis Dynamic 共五次创建会话尝试，均返回 HTTP 429：`no available capacity`。没有生成任何 Dynamic 画面，也没有终止团队其他人的会话。
- Orbis Stable 成功执行六个短测试：水面两种提示词各一次，白马、鸟、树叶、火光各一次。每次收到画面后记录约六秒，首帧等待约 3.94–4.25 秒；实际交付流 2560×1440。本地帧记录为 1024×576。
- 每个已创建会话均在 `finally` 中断开；服务端会话上限为 75 秒，正常测试在约 14 秒内结束。

| 对象 | 原始输出表现 | 当前全景如何使用 |
| --- | --- | --- |
| 水面 | 快速替换为另一片湖景，构图保持失败 | 仅提取局部水面的时间亮度变化，丢弃模型生成的场景与几何 |
| 树叶 | 部分建筑与树冠可对应，但有缩放、漂移和新鸟 | 用静止背景做特征配准；只把原位叶尖的光流转移到原画，位移限制为原生源图 1.1 像素 |
| 火光 | 原画结构较接近，但有镜头漂移与更大的烟 | 配准后仅提取远城活动蒙版内的亮度变化；原画建筑、烟气形状保持静止 |
| 白马 | 被放大、改形，丢失原形象细节，并出现走动 | 未通过；保持原画静止 |
| 鸟 | 鸟与背景均被放大或重构 | 未通过；保持原画静止 |

因此，当前通过的是“模型局部动势经过后期处理，再驱动固定的全景基底”这一原型路径。没有任何一段完整原始输出获准直接替换原画。动物动作尚未通过，也不能据此宣布后续所有场景均可直接批量复制。

## 画面和循环控制

所有相机、建筑、地形、天空与地面的像素来自固定基底。水与火的亮度变化被限幅，树叶只发生小幅位置变化。每个活动区外都锁定原画，编码前检测到的越界变化像素数为 0；视频压缩会引入编码误差，该数值不是对有损编码后每个像素的保证。

循环取每段中间约三秒，按正向／反向排列为六秒，避免硬切回开头。它是后期往返循环，不是 Orbis 原生首尾帧约束。水面亮度波动与火光适合这种处理；此结果不能证明持续单向水流或复杂人物动作的循环已经成立。

局部后期由本地 OpenCV 特征配准、光流、亮度提取和蒙版程序执行；没有运行 ComfyUI。该逻辑可以移植为 ComfyUI／合成软件工作流，但本轮没有验证对应节点图。

## 提示词

每个运行目录内的 `effective-prompt.txt` 与 `report.json` 保存实际发送的提示词。最初参考和计划提示词在每个对象目录内的 `reference.png`、`prompt.txt`。第二轮优先声明平面绘画、保留构图和笔触，然后只指定一个微小动作，以 `passthrough=true` 原样发送。固定机位的文字要求是软约束，实测并未严格遵从，因此不能仅凭提示词保证机位或身份。

主要可重复提示词结构：

> A flat early-Netherlandish oil painting holds the exact composition and fine painted brushwork of the reference image. [One small local action.] Every painted building, figure, animal, bank and branch holds its established shape and position; the painting stays flat, with the original mineral colors. Static camera, locked frame, identical framing throughout. A tiny local painted movement, with the rest of the painting still.

当前枝叶与火光对应运行：`leaves/run-stable-01/`、`fire/run-stable-01/`。水面对应第二轮：`water/run-stable-02/`。失败的动物动作也完整保存在 `horse/run-stable-01/`、`bird/run-stable-01/`，供下一轮对照。

## 文件与复现

- `jobs.json`：五个对象的参考范围、活动支持区、动作和模型名。
- `<对象>/run-*/raw-orbis.mp4`、`frames/`：未经合成的模型输出及逐帧记录。
- `<对象>/run-*/runtime-schema.json`：连接后读取的实际接口 schema。
- `<对象>/run-*/analysis.json`、`contact.jpg`：背景配准诊断与帧对照。
- `delivery/garden-equirect-2048.mp4`、`delivery/hell-equirect-2048.mp4`：完整 2:1 后期全景。
- `delivery/report.json`：使用的模型、原始失败情况、合成方式与像素支持区检查。
- `../review/bosch-orbis/verification.json`：浏览器视频播放、相机、手势、2:1、原始片段和窄屏检查。

处理脚本为 `../prepare_orbis_painting.py`、`../run_orbis_painting.py`、`../analyze_orbis_painting.py`、`../composite_orbis_painting.py`、`../build_bosch_orbis.py`。SDK 与视频工具安装在任务专用的 `../.venv-orbis/`，未修改队友仓库依赖。

## 已验证与待验证

已验证：真实 API 生成与逐帧接收、局部后期、与已批准静态球面排版的对照、标准 2:1 导出、浏览器录像播放、微动暂停、手势揭示、固定观察点、原始试片对照和 390px 窄屏。

待验证：可用容量下的 Dynamic 对照、原位动物动作、直接使用完整生成 RGB 的可靠性、头显观看质量／性能，以及现场实时模型流接入。目前浏览器播放已有录像，不会发起模型调用或持续消耗模型会话。

接口与提示词依据：[Reactor Python SDK](https://docs.reactor.inc/sdk-reference/python/reactor.md)、[Orbis 提示词指南](https://docs.reactor.inc/model-api-reference/visko-orbis-dynamic/prompt-guide)、[模型规格](https://docs.reactor.inc/model-api-reference/visko-orbis-stable/overview.md)。测试中的实际结论以本地原始帧和记录为准。
