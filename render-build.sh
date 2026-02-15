#!/bin/bash
# Install system dependencies for Pillow
apt-get update
apt-get install -y python3-dev libjpeg-dev zlib1g-dev
# Install Python requirements
pip install -r requirements.txt
