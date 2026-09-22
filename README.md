# Coronary Angiography Image Enhancement — Real-Time Baseline

A research/assignment baseline for enhancing **contrast-filled coronary arteries in X-ray/cine angiography** while suppressing slowly varying anatomical background and persistent structures.

The pipeline supports **16-bit grayscale image processing**, optional temporal subtraction and translation registration, and detailed per-frame latency benchmarking.

> ⚠️ **Important:** This is research/educational software, not a certified medical device and not intended for diagnosis or clinical decision-making.

---

## 📌 Project Overview

Coronary angiography images contain thin, branching coronary vessels superimposed on anatomical structures such as:

* Ribs
* Spine
* Lung fields
* Soft-tissue background
* Sensor noise

The goal of this project is to suppress the slowly varying and persistent background while enhancing vessel-like structures under a strict real-time processing requirement.

### Target Requirement

```text
Maximum processing latency ≤ 36 ms/frame
```

The latency measurement covers the processing pipeline from the moment a frame enters the enhancement pipeline until the final enhanced frame is produced.

Disk I/O and file-writing operations are excluded from this measurement.

---

# 🎯 Objectives

* Process 16-bit grayscale coronary angiography images.
* Suppress slowly varying anatomical background.
* Enhance dark, thin coronary vessels.
* Support single frames and cine sequences.
* Support temporal/reference-frame subtraction.
* Handle small translational motion.
* Preserve meaningful intensity relationships across cine frames.
* Provide raw, processed, and enhanced outputs.
* Generate visual comparison images/videos.
* Benchmark processing latency and FPS.
* Maintain a maximum processing latency of ≤36 ms/frame when measured on the target hardware.

---

# 🔬 What the Pipeline Does

The complete processing pipeline is:

```text
Input Image / Cine
        │
        ▼
16-bit Conversion / Preservation
        │
        ▼
Intensity Normalization
        │
        ▼
Gaussian Denoising
        │
        ▼
Background Suppression
   ┌────┴─────────────┐
   │                  │
Box Filter       Black-Hat
   │                  │
   └────────┬─────────┘
            ▼
   Optional Temporal
   Reference Subtraction
            │
            ▼
 Optional Translation
     Registration
            │
            ▼
   Vessel Response Boost
            │
            ▼
          CLAHE
            │
            ▼
 Enhanced Coronary Image
```

The individual stages are designed to remain computationally lightweight and suitable for CPU-based real-time processing.

---

# 🧠 Processing Pipeline

## 1. 16-bit Image Preservation

Input images are converted or preserved as:

```text
uint16
Range: 0–65535
```

Supported sources are normalized into a common 16-bit grayscale representation.

For cine sequences, frames use a common intensity scale rather than independently rescaling every frame. This is important because independent frame normalization could destroy the intensity relationship needed for temporal subtraction.

---

## 2. Intensity Normalization

The default implementation performs fast min-max normalization.

An optional percentile-based normalization can be used when extreme pixels affect the image range.

```text
Default:
Min-Max Normalization

Optional:
1st–99.5th Percentile Normalization
```

The percentile option is more robust to extreme outliers but may increase processing time.

---

## 3. Gaussian Denoising

A small Gaussian blur is applied before morphological processing.

Default:

```text
gaussian_ksize = 3
```

The purpose is to reduce high-frequency sensor noise while keeping computational cost low.

---

# 4. Background Suppression

Background suppression is the core component of the pipeline.

Two complementary approaches are used.

### Box-Filter Background Estimation

A wide box filter estimates the slowly varying anatomical background.

Default:

```text
background_kernel = 31
```

Conceptually:

```text
Background ≈ BoxFilter(Image)

Vessel Response ≈ Background - Denoised Image
```

The box filter is selected because it is computationally inexpensive for the required kernel size.

---

### Black-Hat Morphology

OpenCV's black-hat morphological operation is used to emphasize dark, thin structures.

```python
cv2.MORPH_BLACKHAT
```

Default:

```text
blackhat_kernel = 11
```

This is useful because contrast-filled coronary vessels can appear as dark, thin structures relative to surrounding anatomy.

The default implementation uses a single kernel scale to maintain low latency.

The two suppression responses are combined using:

```python
cv2.max()
```

so that the stronger response is retained at each pixel.

---

# 5. Temporal / Reference-Frame Subtraction

For cine sequences, a pre-contrast or low-contrast reference frame can be used.

Example:

```bash
python main.py \
    --input path/to/data \
    --output outputs \
    --reference-frame 0
```

Conceptually:

```text
Reference Frame
      -
Current Frame
      ↓
Temporal Vessel Response
```

Persistent structures such as ribs, spine, and other anatomical background remain relatively stable, while contrast-filled vessels change between frames.

This provides a classical approach related to **digital subtraction angiography**.

### Disable Temporal Subtraction

If a suitable reference frame is unavailable:

```bash
python main.py \
    --input path/to/data \
    --output outputs \
    --no-temporal
```

For cine sequences, the reference frame should ideally be a frame before strong coronary contrast appears.

---

# 6. Optional Translation Registration

Small patient/table translations can be corrected using phase correlation.

```python
cv2.phaseCorrelate()
```

Enable it with:

```bash
python main.py \
    --input path/to/data \
    --output outputs \
    --reference-frame 0 \
    --register
```

Registration estimates small X/Y translations between the reference and current frame.

### Handles

* Small X translation
* Small Y translation

### Does Not Handle

* Cardiac deformation
* Non-rigid motion
* Full rotation

Registration adds processing overhead, so latency should be benchmarked with and without this option.

---

# 7. Vessel Response Boost

After background suppression, a mild vessel-response enhancement is applied.

Default:

```text
vessel_gain = 1.15
```

The implementation uses an unsharp-mask-style enhancement with:

```python
cv2.addWeighted()
```

The enhancement is intentionally conservative to reduce the risk of amplifying residual noise.

---

# 8. CLAHE Enhancement

The final stage uses:

**CLAHE — Contrast Limited Adaptive Histogram Equalization**

Default configuration:

```text
clip_limit = 2.0
tile_grid = 8 × 8
```

CLAHE improves local contrast and helps make faint vessel segments more visible.

### Fast Real-Time Mode

The default path uses:

```text
uint16
   ↓
uint8
   ↓
CLAHE
   ↓
uint16
```

Only the final contrast-enhancement stage uses the temporary 8-bit representation.

The earlier stages remain 16-bit.

### Full 16-bit CLAHE

For maximum bit-depth preservation:

```bash
python main.py \
    --input path/to/data \
    --output outputs \
    --full-16bit-clahe
```

This may increase latency, so the benchmark should be rerun before reporting compliance with the 36 ms requirement.

---

# 📥 Supported Input

The pipeline supports:

| Input         | Format                | Notes                                    |
| ------------- | --------------------- | ---------------------------------------- |
| 16-bit images | TIFF / PNG / PGM      | Preserves high-bit-depth input           |
| DICOM cine    | `.dcm`                | Multi-frame medical imaging              |
| NumPy cine    | `.npz`                | Suitable for public angiography datasets |
| Video         | MP4 / AVI / MOV / MKV | Usually decoded as 8-bit                 |
| Image folder  | Multiple image files  | Frame-by-frame cine processing           |
| Single image  | Common image formats  | Single-frame processing                  |

> For demonstrating **true 16-bit processing**, DICOM, TIFF, or NPZ input is preferred over ordinary video.

---

# 📂 Project Structure

```text
Coronary-Angiography-Enhancement/
│
├── main.py
├── demo_synthetic.py
├── README.md
├── requirements.txt
│
├── src/
│   ├── io_utils.py
│   ├── pipeline.py
│   └── benchmark.py
│
├── data/
│   └── ...
│
└── outputs/
    ├── raw_frame_0000_16bit.tiff
    ├── processed_frame_0000_16bit.tiff
    ├── enhanced_frame_0000_16bit.tiff
    ├── comparison_frame_0000.png
    ├── comparison.mp4
    └── benchmark_results.json
```

### File Responsibilities

| File                | Responsibility                            |
| ------------------- | ----------------------------------------- |
| `main.py`           | CLI entry point and pipeline execution    |
| `src/io_utils.py`   | Input loading and common frame conversion |
| `src/pipeline.py`   | Core coronary enhancement algorithm       |
| `src/benchmark.py`  | Latency and performance measurement       |
| `demo_synthetic.py` | Synthetic 16-bit cine generation          |
| `requirements.txt`  | Python dependencies                       |
| `README.md`         | Project documentation                     |

---

# ⚙️ Installation

## 1. Clone Repository

```bash
git clone https://github.com/<your-username>/<your-repository>.git

cd Coronary-Angiography-Enhancement
```

## 2. Create Virtual Environment

### Windows

```powershell
python -m venv .venv

.venv\Scripts\activate
```

### macOS / Linux

```bash
python -m venv .venv

source .venv/bin/activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🧪 Quick Installation Test

Generate synthetic 16-bit cine data:

```bash
python demo_synthetic.py
```

Run the pipeline:

```bash
python main.py \
    --input synthetic_cine \
    --output outputs \
    --reference-frame 0 \
    --save-video
```

The synthetic data is intended only for software validation and latency testing.

It must **not** be used to claim medical or clinical accuracy.

---

# 🏥 Run on DICOM Cine

```bash
python main.py \
    --input path/to/coronary_cine.dcm \
    --output outputs \
    --reference-frame 0 \
    --save-video
```

---

# 🧬 Run on NPZ Cine Dataset

```bash
python main.py \
    --input path/to/study/view.npz \
    --output outputs \
    --reference-frame 0 \
    --max-frames 300 \
    --save-video
```

---

# 🖼️ Run on 16-bit Image Folder

```bash
python main.py \
    --input path/to/frames \
    --output outputs \
    --reference-frame 0 \
    --save-video
```

---

# 📊 Output Files

The pipeline generates:

```text
outputs/
│
├── raw_frame_0000_16bit.tiff
├── processed_frame_0000_16bit.tiff
├── enhanced_frame_0000_16bit.tiff
├── comparison_frame_0000.png
├── comparison.mp4
└── benchmark_results.json
```

### Output Definitions

**Raw**

Original input image.

**Processed**

Background-suppressed vessel-response image before final CLAHE.

**Enhanced**

Final CLAHE-enhanced coronary image.

**Comparison**

```text
RAW
   │
   ▼
BACKGROUND SUPPRESSED
   │
   ▼
CORONARY ENHANCED
```

The project provides raw/processed/enhanced comparison specifically for visual evaluation.

---

# ⚡ 36 ms Performance Requirement

The mandatory project requirement is:

```text
Maximum Processing Latency ≤ 36 ms/frame
```

The benchmark measures:

```text
Frame enters pipeline
        ↓
Processing
        ↓
Enhanced frame produced
```

It excludes:

```text
Disk loading
File writing
Video encoding/output I/O
```

---

# 📈 Benchmark Metrics

`outputs/benchmark_results.json` reports:

* Average latency
* Minimum latency
* Maximum latency
* P50 latency
* P95 latency
* P99 latency
* FPS from mean latency
* Overall throughput
* Image size
* Image dtype
* CPU information
* RAM information
* OpenCV configuration
* Per-stage timing
* Whether maximum latency is ≤36 ms

The benchmark is designed to time the processing function after a warm-up pass.

---

# ⚠️ Performance Reporting

**Do not claim the 36 ms requirement has been achieved unless it has been measured on the exact submission hardware and dataset.**

Performance can vary depending on:

* CPU
* Image resolution
* OpenCV build
* Number of frames
* Reference-frame subtraction
* Translation registration
* CLAHE mode
* Kernel sizes
* Operating system

Example measurements from the project's test environment were approximately 4–6 ms average for synthetic 512×512 sequences, but these values are machine-dependent and should not be treated as guaranteed results.

---

# 📚 Dataset Recommendations

For cine/sequence behaviour, the project can be evaluated using public coronary angiography video datasets such as:

* **CoronaryDominance**
* **CADICA**

For expert-labeled vessel validation:

* **ARCADE**
* **DCA1**

Always follow the individual dataset's:

* License
* Terms of use
* Citation requirements
* Redistribution restrictions

Do not upload restricted or identifiable medical data to this repository.

---

# 🧪 Validation Strategy

A practical validation setup can include:

```text
                    Dataset
                       │
          ┌────────────┴────────────┐
          │                         │
       Cine Data              Labeled Data
          │                         │
          ▼                         ▼
 Temporal Behaviour          Vessel Validation
          │                         │
          ▼                         ▼
 Motion / Contrast            Visual / Quantitative
       Testing                    Analysis
```

The synthetic dataset can be used for software and latency testing, while real angiography datasets should be used for meaningful visual/qualitative evaluation.

---

# 🩺 Interpreting the Method Honestly

This project performs:

```text
Image Suppression
        +
Vessel Enhancement
```

It does **not** perform full anatomical semantic segmentation.

The algorithm does not explicitly classify every pixel as:

```text
Rib
Spine
Lung
Vessel
Background
```

Instead:

* Box filtering suppresses slowly varying background.
* Black-hat morphology emphasizes dark thin structures.
* Temporal subtraction suppresses persistent anatomy.
* Vessel-response enhancement strengthens vessel-like structures.
* CLAHE improves local contrast.

If explicit pixel-wise anatomical removal is required, a trained segmentation model would be a separate extension and would still need to satisfy the 36 ms/frame requirement.

---

# ⚠️ Known Limitations

1. This is enhancement/suppression rather than semantic segmentation.
2. It does not explicitly identify every anatomical structure.
3. Translation registration does not correct cardiac deformation.
4. Rotation is not explicitly corrected.
5. The method assumes vessels appear darker than surrounding anatomy.
6. Multi-scale vessel enhancement is not enabled in the real-time default.
7. Synthetic data is not clinically or anatomically accurate.
8. Real datasets are required for meaningful visual validation.
9. Full 16-bit CLAHE may increase processing latency.
10. Registration increases computational cost.

---

# 🔧 Main Configuration Parameters

| Parameter           | Default | Purpose                         |
| ------------------- | ------: | ------------------------------- |
| `gaussian_ksize`    |     `3` | Noise reduction                 |
| `background_kernel` |    `31` | Background estimation           |
| `blackhat_kernel`   |    `11` | Thin dark-structure enhancement |
| `vessel_gain`       |  `1.15` | Vessel-response boost           |
| `clip_limit`        |   `2.0` | CLAHE contrast limit            |
| CLAHE tile grid     | `8 × 8` | Local contrast processing       |
| `fast_clahe_8bit`   |  `True` | Faster final CLAHE              |

---

# 🛠️ Technologies

* **Python**
* **OpenCV**
* **NumPy**
* **DICOM**
* **Classical Computer Vision**
* **Morphological Image Processing**
* **CLAHE**
* **Phase Correlation**
* **Temporal Image Subtraction**
* **16-bit Image Processing**
* **Performance Benchmarking**

---

# 🚀 Future Improvements

Possible future extensions include:

* Multi-scale vessel enhancement
* Deep-learning vessel segmentation
* GPU acceleration
* Non-rigid image registration
* Cardiac-motion compensation
* Advanced temporal filtering
* Vessel centerline extraction
* Vessel diameter estimation
* Stenosis analysis
* Quantitative coronary vessel analysis
* Larger real-world dataset validation
* Optimized GPU/CPU hybrid processing

---

# 📌 Research / Educational Disclaimer

This repository is intended for **research, educational, and assignment purposes**.

It is not:

* A certified medical device
* A diagnostic system
* A treatment-planning system
* A substitute for clinical interpretation

Enhanced images should not be used independently for clinical decision-making.

---

# 👨‍💻 Author

**Hrushikesh Kate**

B.Tech Computer Engineering — AI & ML

### Areas of Interest

* Computer Vision
* Artificial Intelligence
* Machine Learning
* Deep Learning
* Medical Image Processing
* Generative AI
* AI Automation

---

# ⭐ Key Features

```text
✓ 16-bit Coronary Angiography Processing
✓ DICOM / NPZ / TIFF / Image Folder Support
✓ Background Suppression
✓ Black-Hat Vessel Enhancement
✓ Temporal Reference Subtraction
✓ Optional Translation Registration
✓ Vessel Response Boost
✓ CLAHE Enhancement
✓ Synthetic 16-bit Cine Generation
✓ Real-Time CPU Processing
✓ ≤36 ms Performance Target
✓ Detailed Latency Benchmarking
✓ RAW / PROCESSED / ENHANCED Comparison
✓ Benchmark JSON Output
✓ Research-Friendly Architecture
```

---

## 📖 Reproducibility

To reproduce an experiment:

```bash
python demo_synthetic.py

python main.py \
    --input synthetic_cine \
    --output outputs \
    --reference-frame 0 \
    --save-video
```

Then inspect:

```text
outputs/benchmark_results.json
outputs/comparison_frame_0000.png
outputs/comparison.mp4
```

For the first frame, remember that frame `0` may be the reference frame itself. A middle frame is generally more informative for visually inspecting contrast-filled coronary vessels.
