# Run review
/home/ubuntu2204/smartcar-advanced/M5/runs/20261117_000752_782558517

Result: **SUCCESS**; elapsed: 6.897876192000695 s

| Step | Status | Seconds | Retries | Degraded |
|---|---|---:|---:|---|
|wait_start|SUCCESS|0.013|0|False|
|navigate_to_scan|SUCCESS|4.853|0|False|
|detect_qr|SUCCESS|0.011|0|False|
|grasp|SUCCESS|2.005|0|False|
|battery_check|SUCCESS|0.007|0|False|
|lidar_check|SUCCESS|0.008|0|False|
|parallel_checks|SUCCESS|0.014|0|False|

## Key metrics
|Metric|Mean|Peak|
|---|---:|---:|
|perception_hz|7.636|80.673|
|confidence|0.806|0.874|
|cpu_percent|15.000|15.000|
|network_rtt_ms|1.000|1.000|
|path_deviation_m|0.020|0.020|
|temperature_c|45.000|45.000|
|voltage_v|12.000|12.000|

## Evidence chain
LOST on /perception/detections (recorded telemetry) → pause task and request lidar-only fallback → handling delay 0.010s; extra navigation cost unmeasured; measured task pause 1.833s
DEGRADED on /perception/detections (recorded telemetry) → no causally linked corrective action recorded → cost unmeasured
ONLINE on /perception/detections (recorded telemetry) → no causally linked corrective action recorded → cost unmeasured

## Clock alignment
MCAP log_time and FSM ts_ns are wall nanoseconds. ros_ns is stored separately; never directly subtract simulation time from wall time.

## Previous run comparison
Previous: /home/ubuntu2204/smartcar-advanced/M5/runs/20261117_000751_866240637
perception_hz mean change: -0.9311
confidence mean change: -0.0437
cpu_percent mean change: +0.0000
network_rtt_ms mean change: +0.0000
path_deviation_m mean change: +0.0000
temperature_c mean change: +0.0000
voltage_v mean change: +0.0000
New faults: ['DEGRADED', 'LOST', 'ONLINE']
Disappeared faults: []
Current switches: [{"ts_ns": "1794845273057733136", "kind": "model", "old": "null", "new": "\"/home/ubuntu2204/smartcar-advanced/M6/M6-1/models/best_fp32.onnx\"", "user": "web", "experiment": "manual", "pid": "44755"}, {"ts_ns": "1794845273111450678", "kind": "parameters", "old": "{\"nav_speed\": 0.4, \"perception_hz\": 10.0, \"confidence\": 0.25, \"scene\": \"training_mock\"}", "new": "{\"nav_speed\": 0.4, \"perception_hz\": 10.0, \"confidence\": 0.25, \"scene\": \"training_mock\"}", "user": "web", "experiment": "manual", "pid": "44755"}]

Parse time: 0.011 s; 140 key messages. Missing metrics remain unavailable.
