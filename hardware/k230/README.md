# K230 USB 传感器桥

本板为 01Studio CanMV K230 2G，固件自报 `v1.4-41-g273db2e`。使用 CanMV 调试 USB 协议在 RAM 中执行采集程序，不要求板端 Wi-Fi，也不把调试串口说成系统自带 UVC 摄像头或 UAC 声卡。原 SD 卡程序已另行备份，不刷固件、不覆盖 main.py。

链路：K230 USB → Windows COM3 → 127.0.0.1:8766 → SSH 反向转发 → Ubuntu ROS。Windows 必须保留 USB 所有权，不再同时将该设备直通虚拟机。

```powershell
ssh -N -R 127.0.0.1:8766:127.0.0.1:8766 -i C:\Users\ROG\.ssh\smartcar_m0_ed25519 ubuntu2204@192.168.19.131
python hardware/k230/usb_host.py --port COM3 --seconds 90 --out 一个不存在的新目录
```

Ubuntu 启动：

```bash
source scripts/env.sh
ROS_DOMAIN_ID=68 .venv-ros/bin/python hardware/k230/ros_usb_bridge.py --seconds 120 --out evidence/USB/latest.json
ROS_DOMAIN_ID=68 .venv-ros/bin/python hardware/k230/offline_voice.py --model hardware/voice/models/vosk-model-small-cn-0.22 --out evidence/USB/voice.json
```

输出 `/camera/image_raw`（320×240 BGR8）、`/audio/pcm_s16le_16k_mono`（UInt8MultiArray，signed16 little-endian）、`/k230/button`（Bool）和 `/hw/k230`（无媒体数据的元信息）。图像 ROS stamp 是接收时刻；板端 ticks 单独保存，未经标定不能宣称采集延迟已精确测出。

实测 65 秒：Windows 和 Ubuntu 均收到 406 帧、65.24 秒音频，约 6.25 FPS，未报告传输错误、队列丢弃。90 秒真人测试：562 帧、90.24 秒音频、2 个按键边沿，USB relay_drops=0。使用右声道；GPIO21 为低电平按下。物理 KEY 与 GUI 均通过同一个 STOP 命令入口，锁存解除必须手动操作。

最初开放词表将一处“停车”识别为“挺住”，低置信度被拒绝。随后限定“小车 开始/暂停/停车/求助 + [unk]”词表，按原时序回放完整真实录音验证。结果见 `evidence/USB/voice_replay.json`。这属于真实录音回放验证，不冒充第二次实时说话测试。非法 PAUSE/START 被安全拒绝并记录，不再终止 ROS 接收线程。

USB relay 每客户端队列上限128；过载时有显式丢弃计数。M6 内部推理管线另用阻塞背压，不混淆两者的丢帧口径。当前 USB 相机约6.25 FPS，不能用回放管线31 FPS代替物理相机30 FPS或Orin推理成绩。

官方接口：[录音](https://wiki.01studio.cc/docs/canmv_k230/basic_examples/record/)、[按键](https://wiki.01studio.cc/docs/canmv_k230/basic_examples/key/)。原始室内图像、完整录音和主程序备份只留本地，不加入 Git。
