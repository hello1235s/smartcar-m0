# Run review
/home/ubuntu2204/smartcar-advanced/M5/runs/20261116_214159

Result: **SUCCESS**; elapsed: 6.809905998001341 s

| Step | Status | Seconds | Retries | Degraded |
|---|---|---:|---:|---|
|wait_start|SUCCESS|0.016|0|False|
|navigate_to_scan|SUCCESS|4.767|0|False|
|detect_qr|SUCCESS|0.011|0|False|
|grasp|SUCCESS|2.003|0|False|
|battery_check|SUCCESS|0.009|0|False|
|lidar_check|SUCCESS|0.008|0|False|
|parallel_checks|SUCCESS|0.012|0|False|

## Key metrics
|Metric|Mean|Peak|
|---|---:|---:|

## Evidence chain
No recorded fault; no root cause inferred.

## Clock alignment
MCAP log_time and FSM ts_ns are wall nanoseconds. ros_ns is stored separately; never directly subtract simulation time from wall time.

Parse time: 0.027 s; 709 key messages. Missing metrics remain unavailable.
