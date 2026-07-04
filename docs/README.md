# Aurika: AI Restaurant Operations Intelligence Platform

Welcome to **Aurika**, the premier platform that converts raw CCTV footage into actionable operational intelligence. Aurika is not just a computer vision tool; it is a full-stack, event-driven business intelligence engine designed to act as the canonical operational heartbeat of your restaurant.

## Overview
Aurika observes physical spaces, derives business events (like a guest entering a waiting area), builds an immutable state engine of all active operations, derives real-time metrics, and ultimately generates prioritized, fully-explainable operational recommendations for restaurant managers.

## Features
- **Zero-Hallucination AI Copilot**: Ask natural language questions about your restaurant's health, and receive deterministic answers grounded in live operational data.
- **Executive Dashboard**: A rich, real-time terminal dashboard offering instant operational visibility (Wait Times, Queue Lengths, Staff Utilization).
- **Declarative Rule Engine**: Operational intelligence powered by a customizable JSON configuration—no Python changes required.
- **Automated HTML Reporting**: Generates a pristine end-of-day executive report for operational review.

## Quick Start
```bash
# 1. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
pip install ultralytics opencv-python rich jinja2 numpy

# 3. Launch the Executive Demo (Runs the video pipeline and live dashboard)
python pipeline_position.py
```

## Deployment Guide
1. Ensure your camera RTSP streams are configured and accessible.
2. Update the `VIDEOS` constant in `pipeline_position.py` (or transition it to an `.env` driven config) to point to your RTSP streams.
3. Use the `ZoneMapper` tools to define your restaurant's physical polygon zones in `configs/zones.json`.
4. Define your SLA thresholds in `configs/rules.json`.
5. Run the pipeline on a dedicated GPU edge device or cloud instance.
