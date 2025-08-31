#!/usr/bin/env bash
set -o errexit  # exit on error

# Install system dependencies needed for pyscard
apt-get update
apt-get install -y libpcsclite-dev pcscd

# Now install Python deps
pip install -r requirements.txt
