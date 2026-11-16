# M6-2：量化与误差归因

```bash
.venv-model/bin/python M6/M6-2/quantize/ptq.py --model M6/M6-1/models/best_fp32.onnx --calib hardware/k230/usb_ros_20261116_2135 --out M6/M6-2/models --functional-indoor
.venv-model/bin/python M6/M6-2/tools/layer_analysis.py --fp32 M6/M6-1/models/best_fp32.onnx --int8 M6/M6-2/models/static_qdq.onnx --data hardware/k230/smartcar_usb_20261116_200340 --out M6/M6-2/results
```

实际跑通动态U8权重量化（64个ConvInteger）、静态QDQ（123Q/250DQ）和静态QOperator（64个QLinearConv），全部经过ORT推理和有限值检查，模型约3.4MB，对比FP32约12.7MB。不是仅转换成功或只量化一个无关MatMul。

校准用120张哈希各异的真实USB室内相邻帧。它们不是训练集，但场景/光照多样性不足、也不是赛道分布，因此只用于功能验证。用户已确认暂无数据；**100～500张独立赛道校准图、独立标注测试集和逐类mAP仍待补**。不得把室内帧数量达到120解释成赛道校准合格。

逐层CSV覆盖共同Conv输出，3张实拍逐层CosSim、KL、最大误差和激活范围，热力图及最差层JSON已生成。最差数值层为/model.22/cv3.2/cv3.2.1/conv/Conv_output_0，CosSim约0.952。此为数值定位证据，不把输出差异直接当mAP下降。mixed_precision.py保留实测最差3层为FP32并重新量化，结果单独记录；没有标签不能声称QAT/mAP补救已达标。

所有性能行均跑60秒：VM CPU动态约23.52FPS、QDQ约34.95FPS、QOperator约24.24FPS，FP32参考约24.15FPS。QDQ约1.45倍，**未达到2倍阈值**。不同日期共享VM负载也会影响尾延迟，不将该结果外推为板端速度。

另实际转换并部署到MNN3.2.0 CPU运行时，60秒1549帧、约25.81FPS，和ORT输出CosSim>.99。此为专用运行时功能验证，不冒充Orin TensorRT/DLA。官方转换命令和Python接口见THIRD_PARTY.md。TensorRT等板端后端仍待Orin。

eval_map.py接受images/与YOLO格式labels/，按类别、IoU0.50:0.95、101点插值计算AP。缺标注立即拒绝评估，不输出0或伪造mAP。NMS和框反归一化保持浮点，不强行INT8化。
