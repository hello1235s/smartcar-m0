# M5-3：统一交互与安全

同一个终端同时服务8080/8081。裁判话题/referee/cmd支持START/PAUSE/RESUME/STOP/PENALTY/SCORE_QUERY；键盘S/P/R/E对应同一命令入口。START先3-2-1倒计时，再运行任务；总时长180秒，到期即使裁判没发STOP也会停车。暂停冻结剩余时间并协作取消任务，继续重新执行当前叶节点。STOP锁存急停，PENALTY只扣时间并记录，不等同于终止。

急停四层：发布零速度、/emergency_stop、底盘既有适配器持续输出零reference并关闭软件使能、MCAP+审计留痕。并发速度源无法解除锁存，/clear_emergency_stop须手动调用且要求新速度。软件使能门控属于仿真底盘适配器，不能冒充实体电机电源切断；真车仍应有硬件急停。

K230 GPIO21的按下映射STOP；语音使用16k右声道、离线Vosk、小车唤醒词、限定词表及置信度门限。真人90秒采集和按原时序回放日志分别保存，不能把回放说成第二次真人直播测试。过早PAUSE/重复START会被拒绝并审计，接收线程继续工作。

模型热切在smartcar_perception既有感知角色中进行：先加载候选ORT Session并做有限值检查，成功后才原子换指针；失败保留旧模型。Web和感知节点PID均需稳定。参数走实际ROS服务，置信度改变会影响真实NMS结果；阈值联测使用Ultralytics随包官方bus.jpg，**不是赛道测试图**。MCAP与switch_log.csv记录时间、旧/新值、操作者、实验名和PID。

软复位重建上下文，保持节点PID；硬复位由受控启动器重启本终端栈，只允许赛前/赛后，RUNNING/PAUSED/COUNTDOWN服务器端拒绝。硬复位已有实际新旧PID记录。热加载候选不持有操作总锁，以保持STOP响应；周期回调不阻塞等待该锁，避免参数服务应答与主线程锁形成死锁。

audit_log.jsonl只追加，SHA256哈希链支持篡改检测；关闭会话写seal头。完整录音、审计原件留本地。哈希链本身不能防止攻击者同时重写全链和本地seal；要证明尾部未被删除，应把seal头另存到独立可信位置。损坏链拒绝追加，不假装“绝对防篡改”。

```bash
.venv-ros/bin/python -m pytest -q M5/M5-3/tests
.venv-ros/bin/python scripts/test_hot_switch.py
```
