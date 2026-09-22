#!/usr/bin/env bash
set -e
python -m pip install kaggle
mkdir -p data/dca1
kaggle datasets download -d bard2024/database-x-ray-coronary-angiograms-dca1 -p data/dca1 --unzip
