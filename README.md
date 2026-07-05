# Project Aurika
**Enterprise Restaurant Operations AI Platform**

![Aurika CI/CD](https://img.shields.io/badge/build-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen)
![License](https://img.shields.io/badge/license-Proprietary-red)

Aurika is a world-class production computer vision and artificial intelligence system built to optimize live restaurant operations. Moving far beyond simple object detection, Aurika maintains a persistent **Restaurant Digital Twin** and uses a multi-modal **Decision & Optimization Engine** to recommend real-time actions to managers, reducing wait times and increasing table turnover.

## Key Features
- **Multi-Camera Tracking Pipeline:** Seamlessly tracks guests across dining zones using ReID facial embedding (TensorRT).
- **Restaurant Digital Twin (RDT):** Maintains the live 3D geometric state of all tables, queues, and staff.
- **Predictive Forecasting:** Anticipates wait times and queue depths up to 30 minutes into the future.
- **Enterprise Pilot Dashboard:** A React-based command center for restaurant operators to act upon AI recommendations.

## Quickstart

See [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for full local setup and architectural documentation.

```bash
# 1. Install all backend and frontend dependencies
make install

# 2. Start the local development stack
make run
```

## Documentation
All critical technical documentation is located in the `docs/` folder:
- [Engineering Audit](docs/ENGINEERING_AUDIT.md)
- [Performance Profiling](docs/PERFORMANCE_PROFILE.md)
- [Security Audit](docs/SECURITY_AUDIT.md)
- [Dependency Report](docs/DEPENDENCY_REPORT.md)
- [Developer Guide](docs/DEVELOPER_GUIDE.md)

## Contributing
We enforce rigorous engineering standards. No new AI modules or architectures are permitted without formal RFCs. See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for pull request guidelines, linting requirements, and branching strategies.
