# Project Aurika
**Enterprise Restaurant Operations AI Platform**

![Aurika CI/CD](https://img.shields.io/badge/build-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen)
![License](https://img.shields.io/badge/license-Proprietary-red)

Aurika is a world-class production computer vision and artificial intelligence system built to optimize live restaurant operations. Moving far beyond simple object detection, Aurika maintains a persistent **Restaurant Digital Twin** and uses a multi-modal **Decision & Optimization Engine** to recommend real-time actions to managers, reducing wait times and increasing table turnover.

## Key Features
- **Multi-Camera Tracking Pipeline:** Seamlessly tracks guests across dining zones using ReID spatial trajectories.
- **Truth-Mode Business Intelligence:** Real-time metrics fully verified and traceable frame-by-frame to video, SQLite database logs, and evidence crop images.
- **Dynamic Polygon scaling:** OpenCV `cv2.pointPolygonTest` bounding box mappings dynamically scaled to fit any video resolution.
- **Automatic Lifecycle Validator:** Rigorous verification checks for timing monotonicity, unique track mappings, and physical transitions.

## Quickstart

See [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for full local setup and architectural documentation.

```bash
# 1. Start the main pipeline to process videos and generate demo packages
python pipeline_position.py

# 2. Run the automated database integrity checker
python scratch/journey_integrity_checker.py
```

## Final Demo Location
Presentation-ready reports, chronological timelines, annotated video outputs, and evidence crop directories are stored under:
`runs/<video_name>/demo_final/`

## Documentation
All critical technical documentation is located in the `docs/` folder:
- [Developer Guide](docs/DEVELOPER_GUIDE.md)

## Contributing
We enforce rigorous engineering standards. No new AI modules or architectures are permitted without formal RFCs. See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for pull request guidelines, linting requirements, and branching strategies.
