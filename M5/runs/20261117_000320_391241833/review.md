# Run review
/home/ubuntu2204/smartcar-advanced/M5/runs/20261117_000320_391241833

Result: **SUCCESS**; elapsed: 6.0424003769985575 s

| Step | Status | Seconds | Retries | Degraded |
|---|---|---:|---:|---|
|wait_start|SUCCESS|0.007|0|False|
|navigate_to_scan|SUCCESS|4.005|1|False|
|detect_qr|SUCCESS|0.008|0|False|
|grasp|SUCCESS|2.009|0|False|
|battery_check|SUCCESS|0.007|0|False|
|lidar_check|SUCCESS|0.007|0|False|
|parallel_checks|SUCCESS|0.012|0|False|

## Key metrics
|Metric|Mean|Peak|
|---|---:|---:|
|perception_hz|4.690|10.018|
|confidence|0.800|0.805|
|cpu_percent|15.000|15.000|
|network_rtt_ms|1.000|1.000|
|path_deviation_m|0.020|0.020|
|temperature_c|45.000|45.000|
|voltage_v|12.000|12.000|

## Evidence chain
No recorded fault; no root cause inferred.

## Clock alignment
MCAP log_time and FSM ts_ns are wall nanoseconds. ros_ns is stored separately; never directly subtract simulation time from wall time.

Parse time: 0.010 s; 127 key messages. Missing metrics remain unavailable.
