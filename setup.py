# setup.py
from setuptools import setup, find_packages

setup(
    name="restaurant_analytics",
    version="2.0.0",
    description="Enterprise Restaurant Video Analytics and Tracking System",
    author="Antigravity Team",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.20.0",
        "opencv-python-headless>=4.5.0",
        "ultralytics>=8.0.0",
        "pyyaml>=5.0.0",
        "psutil>=5.8.0",
    ],
    python_requires=">=3.8",
)
