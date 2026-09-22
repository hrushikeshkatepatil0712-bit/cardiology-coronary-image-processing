# Real Coronary Angiography Dataset Sources

These datasets are NOT redistributed in this ZIP because of size, account/access conditions, or third-party hosting.
Use the official/public source listed below.

## 1) DCA1 — Database X-ray Coronary Angiograms
- 130 grayscale coronary angiograms
- 300 x 300 pixels
- expert cardiologist ground-truth vessel images
- License shown on Kaggle: MIT
- Best use: small real-image validation and vessel-preservation comparison

Official/public page:
https://www.kaggle.com/datasets/bard2024/database-x-ray-coronary-angiograms-dca1

Kaggle CLI:
```bash
pip install kaggle
kaggle datasets download -d bard2024/database-x-ray-coronary-angiograms-dca1 -p data/dca1 --unzip
```
Kaggle account/API credentials may be required.

## 2) ARCADE — Coronary artery segmentation / stenosis dataset
- 1500 labelled coronary-artery images + 1500 stenosis images across challenge tasks
- 512 x 512 coronary angiography frames
- Best use: labelled coronary segmentation validation
- Access is restricted by the challenge/data-use agreement.

Challenge:
https://arcade.grand-challenge.org/

Zenodo record:
https://zenodo.org/records/8248931

You must register/request access. Do not redistribute restricted files.

## 3) CoronaryDominance
- 1,574 invasive coronary angiography studies
- multi-view X-ray videos/cine data
- Hugging Face repository
- Repository currently reports ~88.6 GB
- License shown by Hugging Face: CC0-1.0
- Best use: real cine / latency / robustness testing

Dataset:
https://huggingface.co/datasets/BearSubj13/CoronaryDominance

Because the repository is very large, do NOT download all 88+ GB unless necessary. Start with one archive/study if possible and use it only for final cine validation.

## Recommended workflow
1. Develop and benchmark with the included synthetic 16-bit dataset.
2. Validate vessel visibility on DCA1.
3. If access is available, validate segmentation on ARCADE.
4. Use a small subset of CoronaryDominance for real cine/latency testing.
