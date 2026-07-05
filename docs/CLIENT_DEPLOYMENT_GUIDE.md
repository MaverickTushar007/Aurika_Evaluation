# Aurika Client Deployment Guide
**Enterprise Operations & Scaling Manual**

## 1. Introduction
This guide provides the necessary architectural overview and configuration instructions to deploy Aurika in a live commercial restaurant environment. 

---

## 2. Infrastructure Requirements
The standard Aurika edge stack runs on a single localized GPU-accelerated node:

### 2.1 Hardware Requirements
- **CPU:** Intel Xeon or AMD EPYC (8+ cores, 3.2 GHz minimum)
- **RAM:** 32 GB DDR4/DDR5
- **GPU:** NVIDIA RTX 4080 / 4090 or NVIDIA A10G (24 GB VRAM minimum for 6x 1080p camera streams)
- **Storage:** 1 TB Enterprise SSD (NVMe)
- **Network:** GigE local switch; isolated VLAN for camera RTSP feeds.

### 2.2 Software Stack
- **OS:** Ubuntu Server 22.04 LTS (HWE kernel)
- **Containerization:** Docker Engine 24.0.x + Docker Compose v2.20.x
- **GPU Drivers:** NVIDIA CUDA Driver 12.1+ + NVIDIA Container Toolkit

---

## 3. Configuration & Provisioning
Customer configurations are handled via JSON or environment vars. See `configs/` for standard structures.
- **Restaurant Name:** Custom name string (e.g. `Bistro-54`).
- **Camera Count & RTSP URLs:** Configured in `configs/cameras.json` to ingest video feeds.
- **Zone/Table mappings:** Floorplan homography coordinates mapped in `coordinate_mapper.py` relative to pixel locations.
