"""Setup configuration for ATM Area Surveillance Edge AI."""

from setuptools import find_packages, setup

setup(
    name="atm-area-surveillance-edge-ai",
    version="1.0.0",
    description="Real-time ATM area surveillance using Edge AI on Raspberry Pi",
    author="LBJayasundara",
    packages=find_packages(exclude=["tests*", "training*", "data*"]),
    python_requires=">=3.9",
    install_requires=[
        "opencv-python>=4.8.0",
        "ultralytics>=8.1.0",
        "numpy>=1.24.0",
        "flask>=3.0.0",
        "flask-cors>=4.0.0",
        "pyyaml>=6.0",
        "scipy>=1.11.0",
    ],
    entry_points={
        "console_scripts": [
            "atm-surveillance=main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
)
