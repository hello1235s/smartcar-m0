# Run review
/home/ubuntu2204/smartcar-advanced/M5/runs/20261117_000310_669548765

Result: **SUCCESS**; elapsed: 6.053448668000783 s

| Step | Status | Seconds | Retries | Degraded |
|---|---|---:|---:|---|
|wait_start|SUCCESS|0.011|0|False|
|navigate_to_scan|SUCCESS|4.011|1|False|
|detect_qr|SUCCESS|0.010|0|False|
|grasp|SUCCESS|2.006|0|False|
|battery_check|SUCCESS|0.007|0|False|
|lidar_check|SUCCESS|0.007|0|False|
|parallel_checks|SUCCESS|0.013|0|False|

## Key metrics
|Metric|Mean|Peak|
|---|---:|---:|
|perception_hz|4.712|10.009|
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

Parse time: 0.009 s; 131 key messages. Missing metrics remain unavailable.
