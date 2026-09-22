# Synthetic Coronary Angiography Dataset

This dataset was generated specifically for the take-home coronary artery image-processing assignment.

## Why this dataset exists
The assignment explicitly allows legally usable / synthetic datasets. These files contain **no patient information** and can be used immediately to develop and benchmark the 16-bit processing pipeline.

## Contents
- `case_01_clean`: stable anatomy, moderate vessel contrast
- `case_02_low_contrast`: lower vessel contrast
- `case_03_noisy_motion`: higher noise + mild motion/artifact
- Every case contains:
  - `frames_png16/` — 24 grayscale 16-bit PNG frames
  - `vessel_masks/` — ground-truth synthetic vessel masks
  - `*_cine.npz` — complete cine sequence + masks in one compressed NumPy file
  - `sample_frame_16bit.tiff` — example 16-bit TIFF
  - `preview.png` — display-only preview
  - `metadata.json`

## NPZ keys
```python
data = np.load("case_01_clean_cine.npz")
frames = data["frames"]          # uint16, shape: (N, 512, 512)
masks = data["vessel_masks"]     # uint8, shape: (N, 512, 512)
```

## Important
This synthetic dataset is useful for development, unit testing, 16-bit support, latency benchmarking, and demonstrating the complete application flow.

For final clinical-looking visual validation, also test the pipeline on a public real coronary angiography dataset listed in `../real_dataset_sources/README.md`.
