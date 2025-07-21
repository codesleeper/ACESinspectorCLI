#!/usr/bin/env python3
"""
Setup script for ACES Inspector CLI Python port
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="aces-inspector-cli",
    version="1.0.0.21",
    author="Luke Smith (Original C#), Python Port",
    author_email="",
    description="A Python port of the ACES Inspector CLI tool for analyzing Automotive Catalog Exchange Standard (ACES) XML files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Markup :: XML",
        "Topic :: Database",
        "License :: OSI Approved :: MIT License",  # Adjust as needed
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "aces-inspector=aces_inspector:main",
        ],
    },
    py_modules=["aces_inspector", "autocare"],
    include_package_data=True,
    zip_safe=False,
)