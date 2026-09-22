@echo off
REM Requires Python and Kaggle API credentials.
python -m pip install kaggle
mkdir data\dca1 2>nul
kaggle datasets download -d bard2024/database-x-ray-coronary-angiograms-dca1 -p data\dca1 --unzip
echo DCA1 download command completed.
pause
