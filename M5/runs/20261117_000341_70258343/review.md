# Run review
/home/ubuntu2204/smartcar-advanced/M5/runs/20261117_000341_70258343

Result: **SUCCESS**; elapsed: 6.864579719000176 s

| Step | Status | Seconds | Retries | Degraded |
|---|---|---:|---:|---|
|wait_start|SUCCESS|0.011|0|False|
|navigate_to_scan|SUCCESS|4.826|0|False|
|detect_qr|SUCCESS|0.009|0|False|
|grasp|SUCCESS|2.003|0|False|
|battery_check|SUCCESS|0.009|0|False|
|lidar_check|SUCCESS|0.007|0|False|
|parallel_checks|SUCCESS|0.014|0|False|

## Key metrics
|Metric|Mean|Peak|
|---|---:|---:|
|perception_hz|4.536|10.040|
|confidence|0.807|0.856|
|cpu_percent|15.000|15.000|
|network_rtt_ms|1.000|1.000|
|path_deviation_m|0.020|0.020|
|temperature_c|45.000|45.000|
|voltage_v|12.000|12.000|

## Evidence chain
LOST on /perception/detections (recorded telemetry) → manual resume after sensor fault → handling delay 1.809s; extra navigation cost unmeasured; measured task pause 1.805s
DEGRADED on /perception/detections (recorded telemetry) → no causally linked corrective action recorded → cost unmeasured
ONLINE on /perception/detections (recorded telemetry) → no causally linked corrective action recorded → cost unmeasured

## Clock alignment
MCAP log_time and FSM ts_ns are wall nanoseconds. ros_ns is stored separately; never directly subtract simulation time from wall time.

## Previous run comparison
Previous: /home/ubuntu2204/smartcar-advanced/M5/runs/20261117_000330_776612094
perception_hz mean change: +0.1481
confidence mean change: +0.0064
cpu_percent mean change: +0.0000
network_rtt_ms mean change: +0.0000
path_deviation_m mean change: +0.0000
temperature_c mean change: +0.0000
voltage_v mean change: +0.0000
New faults: ['DEGRADED', 'LOST', 'ONLINE']
Disappeared faults: []
Current switches: [{"ts_ns": "1794845021311877895", "kind": "model", "old": "\"/home/ubuntu2204/smartcar-advanced/M6/M6-2/models/static_qdq.onnx\"", "new": "\"/home/ubuntu2204/smartcar-advanced/M6/M6-1/models/best_fp32.onnx\"", "user": "web", "experiment": "manual", "pid": "44390"}, {"ts_ns": "1794845021361050138", "kind": "parameters", "old": "{\"nav_speed\": 0.4, \"perception_hz\": 10.0, \"confidence\": 0.25, \"scene\": \"training_mock\"}", "new": "{\"nav_speed\": 0.4, \"perception_hz\": 10.0, \"confidence\": 0.25, \"scene\": \"training_mock\"}", "user": "web", "experiment": "manual", "pid": "44390"}]

Parse time: 0.011 s; 142 key messages. Missing metrics remain unavailable.
