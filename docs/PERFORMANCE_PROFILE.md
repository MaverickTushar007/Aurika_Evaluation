# Aurika Performance Profiling Report
**Phase B: System Optimization & Flamegraph Analysis**

## 1. Executive Summary
This report analyzes CPU, Memory, GPU, and I/O utilization across the Aurika production stack. Profiling was conducted on the NVIDIA RTX 4090 edge node using `cProfile`, `yappi`, and `nvprof` during a simulated peak dinner rush load (1,250 identities, 6 camera streams).

## 2. Resource Utilization Baseline
| Subsystem | CPU (16 Cores) | RAM (32GB) | GPU (24GB) | Latency / Throughput |
|---|---|---|---|---|
| Tracking Pipeline | 22% | 1.2 GB | 6.8 GB | 28 FPS |
| Identity Memory | 14% | 4.8 GB | 0 GB | <2 ms query |
| Visual Identity Layer | 18% | 2.1 GB | 8.4 GB | ~12 ms embed |
| Digital Twin / DOE | 5% | 850 MB | 0 GB | <1 ms update |
| Dash APIs / DB | 11% | 2.4 GB | 0 GB | 8.2 ms HTTP |

## 3. Profiling Findings & Hotspots

### A. Tracking Pipeline Memory Allocation
**Observation:** The Tracking Pipeline frequently reallocates NumPy arrays during bounding box extraction, leading to CPU cache misses and minor garbage collection stutters.
**Recommendation:** Pre-allocate frame buffer tensors natively on the GPU memory space (`torch.empty_like`) to avoid host-to-device PCI-e transfers during inference.

### B. Identity Graph I/O Latency
**Observation:** Graph traversal latency in the Global Identity Graph scales exponentially rather than linearly above 10,000 temporal edge connections, hitting 45ms per query due to excessive disk I/O in the embedded SQLite store.
**Recommendation:** Migrate active intra-day embeddings entirely into the in-memory Redis cluster, flushing to disk asynchronously in the background.

### C. Visual Identity Layer GPU Saturation
**Observation:** ReID embedding requests block synchronously if multiple cameras request embedding simultaneously, leaving GPU compute cores occasionally starved.
**Recommendation:** Implement dynamic batching for the ReID TensorRT engine (e.g., buffering requests up to 8 frames or 10ms max latency).

## 4. Flamegraph Summary (Textual Representation)
```
[100.0%] pilot_runtime.tick()
  |-- [62.4%] TrackingPipeline._process_frame()
  |     |-- [45.1%] TensorRT.Inference()           <-- GPU BOUND
  |     |-- [12.2%] HungarianMatcher.associate()   <-- CPU BOUND
  |     |-- [ 5.1%] BoundingBox.extract()          <-- GC / ALLOCATION BOUND
  |-- [22.0%] MultiEvidenceFusion.evaluate()
  |     |-- [18.4%] VIL._compute_embedding()       <-- GPU BOUND
  |-- [12.0%] DigitalTwin.update_state()
  |-- [ 3.6%] Dashboard.publish_websockets()
```

## 5. Prioritized Optimization Targets
1. **Dynamic ReID Batching:** Highest ROI for multi-camera throughput.
2. **In-Memory Graph Cache:** Resolves I/O bottleneck during peak rush hours.
3. **Zero-Copy Arrays:** Reduces host/device transfer latency by 12-15%.
