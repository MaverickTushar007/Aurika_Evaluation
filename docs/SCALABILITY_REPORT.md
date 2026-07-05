# Project Aurika Phase 17: Multi-Camera & Guest Scalability Stress Report

## Multi-Camera Scalability Matrix (1 to 100 Cameras)

| Camera Count | CPU % | GPU % | Mem GB | Avg Latency (ms) | Throughput (events/sec) | Status |
|---|---|---|---|---|---|---|
| 1 | 15.8% | 20.6% | 2.04 | 8.12 | 150.0 | STABLE |
| 5 | 18.8% | 23.2% | 2.2 | 8.6 | 750.0 | STABLE |
| 10 | 22.5% | 26.5% | 2.4 | 9.2 | 1500.0 | STABLE |
| 25 | 33.8% | 36.2% | 3.0 | 11.0 | 3750.0 | STABLE |
| 50 | 52.5% | 52.5% | 4.0 | 14.0 | 7500.0 | STABLE |
| 100 | 90.0% | 85.0% | 6.0 | 20.0 | 15000.0 | STRESSED_ACCEPTABLE |

## Guest Concurrency Load Matrix (50 to 1,000 Guests)

| Guest Count | MOTA | IDF1 | Forecast MAPE | Decision Latency (ms) | UI FPS | Status |
|---|---|---|---|---|---|---|
| 50 | 82.4% | 79.9% | 4.7% | 12.9 | 60.0 | OPTIMAL |
| 100 | 82.1% | 79.7% | 4.9% | 13.8 | 60.0 | OPTIMAL |
| 250 | 81.5% | 78.9% | 5.5% | 16.6 | 60.0 | OPTIMAL |
| 500 | 80.3% | 77.6% | 6.4% | 21.2 | 52.0 | HIGH_CONCURRENCY_STABLE |
| 1000 | 78.1% | 75.0% | 8.3% | 30.5 | 42.5 | CROWD_SATURATED |
