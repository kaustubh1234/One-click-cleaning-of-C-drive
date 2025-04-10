#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="c-drive-cleaner",
    version="1.0.0",
    description="一个安全高效的C盘文件清理软件",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/c-drive-cleaner",
    packages=find_packages(),
    install_requires=[
        "PyQt5>=5.15.0",
        "psutil>=5.9.0",
        "send2trash>=1.8.0",
    ],
    entry_points={
        "console_scripts": [
            "c-drive-cleaner=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Win32 (MS Windows)",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    python_requires=">=3.6",
)
