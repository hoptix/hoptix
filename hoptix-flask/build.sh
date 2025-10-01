#!/bin/bash
# Build script for deployment platforms
# This ensures Cython is installed before youtokentome

echo "Installing Cython first..."
pip install Cython==3.1.4

echo "Installing remaining requirements..."
pip install -r requirements.txt

echo "Build completed successfully!"
