#!/bin/bash
set -e

echo "Starting build process..."

# Upgrade pip first
python -m pip install --upgrade pip

# Install build dependencies explicitly
python -m pip install setuptools>=68.0.0 wheel>=0.41.0

# Install requirements
python -m pip install -r requirements.txt

echo "Build completed successfully!"