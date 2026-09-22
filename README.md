# 🫀 Coronary Angiography Image Enhancement — Real-Time Baseline

> 🩻 **A real-time computer vision pipeline for enhancing contrast-filled coronary arteries in X-ray/cine angiography while suppressing anatomical background structures.**

This project is a research/assignment baseline designed to enhance the visibility of coronary vessels in angiography images while maintaining a strict **≤ 36 ms/frame processing-latency target**.

The pipeline supports **16-bit grayscale processing**, cine sequences, DICOM images, NPZ datasets, image folders, and common video formats.

> ⚠️ **Important:** This is research/educational software. It is **not a certified medical device** and is **not intended for diagnosis or clinical decision-making**.

---

# 🎯 Project Objectives

The main objectives of this project are:

* 🫀 Enhance contrast-filled coronary arteries.
* 🧹 Suppress slowly varying anatomical background.
* 🩻 Reduce the visual influence of ribs, spine, and lung fields.
* 🔢 Preserve and process 16-bit grayscale information.
* 🎞️ Support single images and cine sequences.
* 🔄 Support temporal/reference-frame subtraction.
* 📐 Support optional small translation registration.
* ✨ Improve local vessel contrast using CLAHE.
* ⚡ Maintain a maximum processing latency target of **36 ms/frame**.
* 📊 Generate detailed benchmark statistics.
* 🖼️ Generate raw, processed, and enhanced image comparisons.
* 🎥 Generate comparison videos for cine sequences.

---

# 🔬 What the Pipeline Does

The complete image-processing workflow is:

```text
                         🩻 INPUT IMAGE / CINE
                                  │
                                  ▼
                         🔢 16-BIT CONVERSION
                                  │
                                  ▼
                       📊 INTENSITY NORMALIZATION
                                  │
                                  ▼
                         🌫️ GAUSSIAN DENOISING
                                  │
                                  ▼
                       🧹 BACKGROUND SUPPRESSION
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
              📦 BOX FILTER              ⚫ BLACK-HAT
            Background Estimate          Morphology
                    │                           │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    🎞️ TEMPORAL SUBTRACTION
                         (Optional)
                                  │
                                  ▼
                       📐 MOTION REGISTRATION
                         (Optional)
                                  │
                                  ▼
                       🎯 VESSEL RESPONSE BOOST
                                  │
                                  ▼
                         ✨ CLAHE ENHANCEMENT
                                  │
                                  ▼
                     🫀 ENHANCED CORONARY IMAGE
```

The processing stages are implemented inside `CoronaryEnhancementPipeline.process_frame()`, with per-stage timing available for performance analysis.

---

# 🫀 Before → After Concept

The pipeline generates three important representations:

```text
🩻 RAW IMAGE
     │
     ▼
🧹 BACKGROUND SUPPRESSED
     │
     ▼
✨ CORONARY ENHANCED
```

### Output Definitions

| Stage            | Description                                 |
| ---------------- | ------------------------------------------- |
| 🩻 **RAW**       | Original input angiography frame            |
| 🧹 **PROCESSED** | Background-suppressed vessel-response image |
| ✨ **ENHANCED**   | Final CLAHE-enhanced image                  |

The project also generates side-by-side comparison images showing:

```text
RAW  |  BACKGROUND SUPPRESSED  |  CORONARY ENHANCED
```

---

# 🧠 Core Computer Vision Pipeline

## 🔢 1. 16-bit Image Processing

All supported inputs are converted or preserved as:

```text
uint16
Range: 0 – 65535
```

For cine sequences, frames share a common intensity scale calculated across the sequence instead of independently scaling each frame.

This preserves frame-to-frame intensity relationships required for temporal subtraction.

---

## 📊 2. Intensity Normalization

The default normalization uses fast min-max normalization.

```text
Default:
Min-Max Normalization
```

An optional percentile normalization can use:

```text
1st percentile → 99.5th percentile
```

This can reduce the influence of extreme outlier pixels, although it requires additional computation.

---

## 🌫️ 3. Gaussian Denoising

A small Gaussian blur is applied before morphological processing.

Default:

```text
gaussian_ksize = 3
```

### Purpose

* 🧹 Reduce sensor noise
* 🔍 Stabilize morphological processing
* ⚡ Maintain low computational cost

---

# 🧹 4. Background Suppression

Background suppression is the main component of the enhancement pipeline.

Two complementary methods are used.

---

## 📦 Box-Filter Background Estimation

A wide box filter estimates slowly varying anatomical background.

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

## ⚫ Black-Hat Morphological Enhancement

The pipeline uses:

```python
cv2.MORPH_BLACKHAT
```

to emphasize dark, thin structures against a brighter background.

Default:

```text
blackhat_kernel = 11
```

This is useful for enhancing vessel-like structures in the input representation.

A single kernel scale is used in the real-time configuration to reduce processing cost.

---

## 🔗 Combining Suppression Responses

The box-filter response and black-hat response are combined using:

```python
cv2.max()
```

This retains the stronger response at each pixel.

---

# 🎞️ 5. Temporal / Reference-Frame Subtraction

For cine sequences, a pre-contrast or low-contrast reference frame can be selected.

Example:

```bash
python main.py \
    --input path/to/data \
    --output outputs \
    --reference-frame 0
```

Conceptually:

```text
       🩻 Reference Frame
              │
              │
              ▼
         ┌─────────┐
         │    −    │
         └─────────┘
              ▲
              │
              │
        🩻 Current Frame
              │
              ▼
      🫀 Vessel Response
```

Persistent structures such as ribs and spine are relatively stable across frames, while contrast-filled coronary vessels change over time.

Temporal subtraction therefore provides a classical approach related to **digital subtraction angiography**.

---

## 🚫 Disable Temporal Subtraction

If a suitable reference frame is unavailable:

```bash
python main.py \
    --input path/to/data \
    --output outputs \
    --no-temporal
```

For cine sequences, the reference frame should ideally be a frame before the contrast bolus strongly opacifies the coronary vessels.

---

# 📐 6. Optional Translation Registration

Small patient/table translations can be handled using phase correlation.

The pipeline uses:

```python
cv2.phaseCorrelate()
```

Enable registration:

```bash
python main.py \
    --input path/to/data \
    --output outputs \
    --reference-frame 0 \
    --register
```

### Handles

* ↔️ Small X translation
* ↕️ Small Y translation

### Does Not Handle

* ❤️ Cardiac deformation
* 🔄 Full rotation
* 🌀 Non-rigid motion

Registration adds processing latency, so it should be benchmarked separately.

---

# 🎯 7. Vessel Response Boost

A mild vessel-response enhancement is applied after background suppression.

Default:

```text
vessel_gain = 1.15
```

The implementation uses:

```python
cv2.addWeighted()
```

against a lightly blurred version of the vessel response.

The gain is intentionally conservative to avoid amplifying residual noise into false vessel-like artifacts.

---

# ✨ 8. CLAHE Enhancement

The final enhancement stage uses:

**CLAHE — Contrast Limited Adaptive Histogram Equalization**

Default:

```text
clip_limit = 2.0
tile_grid = 8 × 8
```

CLAHE improves local contrast and helps make faint vessel segments more visible.

---

## ⚡ Fast CLAHE Mode

The default real-time path performs:

```text
16-bit Vessel Response
        ↓
      8-bit
        ↓
      CLAHE
        ↓
      uint16
```

This reduces the computational cost of the final CLAHE operation.

The earlier stages remain in 16-bit processing.

---

## 🔬 Full 16-bit CLAHE

For maximum bit-depth preservation:

```bash
python main.py \
    --input path/to/data \
    --output outputs \
    --full-16bit-clahe
```

This can increase latency, so benchmark again before reporting compliance with the 36 ms requirement.

---

# 📥 Supported Input Data

| 📦 Input Type            | 📄 Format                      | 📝 Description               |
| ------------------------ | ------------------------------ | ---------------------------- |
| 🩻 Medical Image         | `.dcm`                         | Multi-frame DICOM cine       |
| 🖼️ High Bit-Depth Image | `.tiff`, `.png`, `.pgm`        | 16-bit grayscale images      |
| 🎞️ NumPy Cine           | `.npz`                         | Compressed cine sequences    |
| 🎥 Video                 | `.mp4`, `.avi`, `.mov`, `.mkv` | Usually decoded as 8-bit     |
| 📁 Image Folder          | Multiple images                | Frame sequence               |
| 🖼️ Single Image         | Common formats                 | Single-frame processing      |
| 🧪 Synthetic Cine        | Generated data                 | Development and benchmarking |

> 💡 To demonstrate **true 16-bit support**, DICOM, TIFF, or NPZ input is preferred.

---

# 📚 Dataset Sources

For cine/sequence behaviour, public coronary angiography video datasets can be used, including:

* 🎥 **CoronaryDominance**
* 🎥 **CADICA**

For expert-labeled vessel validation:

* 🧠 **ARCADE**
* 🧠 **DCA1**

### ⚠️ Dataset Usage

Always follow the dataset's:

* 📜 License
* 🔐 Usage restrictions
* 📚 Citation requirements
* 📤 Redistribution policy

Do not commit private, restricted, or identifiable patient data to GitHub.

---

# 🏗️ Project Architecture

```text
Coronary-Angiography-Enhancement/
│
├── 🐍 main.py
├── 🧪 demo_synthetic.py
├── 📖 README.md
├── 📦 requirements.txt
│
├── 📁 src/
│   ├── 📥 io_utils.py
│   ├── 🧠 pipeline.py
│   └── 📊 benchmark.py
│
├── 📁 data/
│   └── coronary_datasets/
│
└── 📁 outputs/
    ├── 🩻 raw_frame_0000_16bit.tiff
    ├── 🧹 processed_frame_0000_16bit.tiff
    ├── ✨ enhanced_frame_0000_16bit.tiff
    ├── 🖼️ comparison_frame_0000.png
    ├── 🎥 comparison.mp4
    └── 📊 benchmark_results.json
```

---

# 📂 File Responsibilities

| 📄 File             | 🔧 Responsibility                         |
| ------------------- | ----------------------------------------- |
| `main.py`           | 🚀 CLI entry point and pipeline execution |
| `src/io_utils.py`   | 📥 Input loading and frame normalization  |
| `src/pipeline.py`   | 🧠 Core enhancement algorithm             |
| `src/benchmark.py`  | 📊 Performance benchmarking               |
| `demo_synthetic.py` | 🧪 Synthetic 16-bit cine generation       |
| `requirements.txt`  | 📦 Python dependencies                    |
| `README.md`         | 📖 Project documentation                  |

The original project documentation defines `pipeline.py` as the core algorithm, `io_utils.py` as the common input loader, and `benchmark.py` as the performance-measurement component.

---

# ⚙️ Installation

## 1️⃣ Clone the Repository

```bash
git clone https://github.com/<your-username>/<your-repository>.git

cd Coronary-Angiography-Enhancement
```

## 2️⃣ Create Virtual Environment

### 🪟 Windows

```powershell
python -m venv .venv

.venv\Scripts\activate
```

### 🐧 Linux / 🍎 macOS

```bash
python -m venv .venv

source .venv/bin/activate
```

## 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🧪 Quick Installation Test

Generate synthetic 16-bit data:

```bash
python demo_synthetic.py
```

Run the enhancement pipeline:

```bash
python main.py \
    --input synthetic_cine \
    --output outputs \
    --reference-frame 0 \
    --save-video
```

The synthetic data is intended only for:

* 🧪 Code testing
* ⚡ Latency testing
* 🔧 Pipeline development

It should **not** be used to claim clinical or medical accuracy.

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

# 🖼️ Run on a Folder of 16-bit Frames

```bash
python main.py \
    --input path/to/frames \
    --output outputs \
    --reference-frame 0 \
    --save-video
```

---

# 🚫 Run Without Temporal Subtraction

```bash
python main.py \
    --input path/to/data \
    --output outputs \
    --no-temporal
```

---

# 📐 Run With Translation Registration

```bash
python main.py \
    --input path/to/data \
    --output outputs \
    --reference-frame 0 \
    --register
```

---

# 🔬 Run With Full 16-bit CLAHE

```bash
python main.py \
    --input path/to/data \
    --output outputs \
    --full-16bit-clahe
```

---

# 📤 Output Files

After processing, the output directory contains:

```text
outputs/
│
├── 🩻 raw_frame_0000_16bit.tiff
├── 🧹 processed_frame_0000_16bit.tiff
├── 🫀 enhanced_frame_0000_16bit.tiff
├── 🖼️ comparison_frame_0000.png
├── 🎥 comparison.mp4
└── 📊 benchmark_results.json
```

### 🩻 Raw Frame

Original input.

### 🧹 Processed Frame

Background-suppressed vessel response after the vessel-response boost.

### 🫀 Enhanced Frame

Final CLAHE-enhanced image.

### 🖼️ Comparison

Side-by-side:

```text
RAW | BACKGROUND SUPPRESSED | CORONARY ENHANCED
```

### 🎥 Comparison Video

Generated for cine sequences when:

```bash
--save-video
```

is specified.

### 📊 Benchmark JSON

Contains measured processing-performance information.

---

# ⚡ Real-Time Performance

## 🎯 Mandatory Requirement

```text
┌──────────────────────────────────┐
│  MAXIMUM LATENCY ≤ 36 ms/frame   │
└──────────────────────────────────┘
```

The benchmark measures:

```text
🩻 Frame enters pipeline
          ↓
🧠 Processing
          ↓
✨ Enhanced frame produced
```

### Excluded

* 💾 Disk loading
* 💾 File writing
* 🎥 Output encoding

The documented benchmark design times `process_frame()` after a warm-up pass.

---

# 📊 Benchmark Metrics

`benchmark_results.json` reports:

| Metric          | Description                   |
| --------------- | ----------------------------- |
| ⏱️ Average      | Mean processing latency       |
| ⚡ Minimum       | Fastest frame                 |
| 🚨 Maximum      | Slowest frame                 |
| 📊 P50          | Median latency                |
| 📈 P95          | 95th percentile latency       |
| 📈 P99          | 99th percentile latency       |
| 🎞️ FPS         | Frames per second             |
| 🚀 Throughput   | Overall processing throughput |
| 🖼️ Image Size  | Input resolution              |
| 🔢 Data Type    | Input/output dtype            |
| 💻 CPU          | Hardware information          |
| 🧠 RAM          | Memory information            |
| 🔧 OpenCV       | OpenCV configuration          |
| 🧩 Stage Timing | Per-stage processing time     |

---

# ⚠️ Performance Reporting

**Do not claim the 36 ms target until it has been measured on the exact submission hardware and dataset.**

Performance depends on:

* 💻 CPU
* 🖼️ Image resolution
* 🔧 OpenCV build
* 📐 Registration
* 🎞️ Temporal subtraction
* ⚙️ Kernel sizes
* ✨ CLAHE mode
* 🧠 System configuration

Example measurements documented for this project include approximately **4–6 ms average latency** for a synthetic 512×512 sequence and approximately **4.3 ms average** for one provided 512×512 case. These are machine-dependent reference measurements, not guaranteed results.

---

# 🧪 Validation

The project can be tested under different conditions:

```text
                    🧪 TEST DATA
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
       🟢 Clean       🟡 Low         🔴 Noisy
                      Contrast        Motion
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                  📊 Benchmark
                         │
                         ▼
                 🖼️ Visual Analysis
```

The documented synthetic cases include clean, low-contrast, and noisy-motion conditions.

---

# 🧠 Requirement Mapping

| 🎯 Requirement         | 🛠️ Implementation                      |
| ---------------------- | --------------------------------------- |
| 16-bit grayscale       | 🔢 `uint16` processing                  |
| Background suppression | 📦 Box filter + ⚫ Black-hat             |
| Coronary enhancement   | ⚫ Black-hat + 🎯 Vessel boost + ✨ CLAHE |
| Noise handling         | 🌫️ Gaussian denoising                  |
| Contrast variation     | 📊 Normalization                        |
| Temporal subtraction   | 🎞️ Reference-frame subtraction         |
| Motion handling        | 📐 Phase correlation                    |
| Real-time processing   | ⚡ CPU-optimized OpenCV                  |
| ≤36 ms/frame           | 📊 Dedicated benchmark                  |
| Performance reporting  | 📄 JSON output                          |
| Visual comparison      | 🖼️ RAW / PROCESSED / ENHANCED          |
| Video output           | 🎥 Optional comparison video            |

---

# 🔧 Main Configuration Parameters

| ⚙️ Parameter        | 🔢 Default | 🎯 Purpose                          |
| ------------------- | ---------: | ----------------------------------- |
| `gaussian_ksize`    |        `3` | 🌫️ Noise reduction                 |
| `background_kernel` |       `31` | 📦 Background estimation            |
| `blackhat_kernel`   |       `11` | ⚫ Vessel-like structure enhancement |
| `vessel_gain`       |     `1.15` | 🎯 Vessel response boost            |
| `clip_limit`        |      `2.0` | ✨ CLAHE contrast limit              |
| CLAHE tile grid     |    `8 × 8` | 🔍 Local contrast                   |
| `fast_clahe_8bit`   |     `True` | ⚡ Faster CLAHE                      |

---

# 🩺 Medical Imaging Considerations

This project is an **image enhancement/suppression system**, not a diagnostic segmentation model.

It does not explicitly classify every pixel as:

```text
🦴 Rib
🦴 Spine
🫁 Lung
🫀 Vessel
⬜ Background
```

Instead, it uses image-processing characteristics to emphasize vessel-like structures.

### Important Limitations

* ❌ No semantic segmentation
* ❌ No explicit anatomical classification
* ❌ No full cardiac-motion correction
* ❌ No non-rigid registration
* ❌ Translation registration only
* ❌ Synthetic data is not clinically accurate

---

# ⚠️ Known Limitations

1. 🧠 Enhancement/suppression is not semantic segmentation.
2. 📐 Registration handles translation but not cardiac deformation.
3. 🔄 Rotation is not explicitly corrected.
4. 🫀 The algorithm assumes vessels appear darker than surrounding anatomy.
5. 🔬 Multi-scale enhancement is not enabled in the real-time default.
6. 🧪 Synthetic data is intended only for development and latency testing.
7. 🏥 Real coronary angiography datasets are required for meaningful qualitative validation.
8. ⚡ Full 16-bit CLAHE may increase processing latency.
9. 📐 Registration increases computational cost.

---

# 🚀 Future Improvements

Potential future extensions include:

* 🧠 Deep-learning vessel segmentation
* 🔬 Multi-scale vessel enhancement
* 🎮 GPU acceleration
* 📐 Non-rigid registration
* ❤️ Cardiac-motion compensation
* 🎞️ Advanced temporal filtering
* 🫀 Vessel centerline extraction
* 📏 Vessel diameter estimation
* 🔍 Stenosis analysis
* 📊 Quantitative vessel analysis
* 🧪 Larger real-world dataset validation
* ⚡ Optimized GPU/CPU processing

---

# 🛠️ Technologies Used

```text
🐍 Python
👁️ OpenCV
🔢 NumPy
🩻 DICOM
🧠 Classical Computer Vision
⚫ Morphological Image Processing
✨ CLAHE
📐 Phase Correlation
🎞️ Temporal Subtraction
🔢 16-bit Image Processing
📊 Performance Benchmarking
```

---

# 📖 Reproducibility

Generate the synthetic dataset:

```bash
python demo_synthetic.py
```

Run the complete pipeline:

```bash
python main.py \
    --input synthetic_cine \
    --output outputs \
    --reference-frame 0 \
    --save-video
```

Then inspect:

```text
📊 outputs/benchmark_results.json

🖼️ outputs/comparison_frame_0000.png

🎥 outputs/comparison.mp4
```

For visual evaluation, a middle frame is generally more useful than the reference frame because frame `0` may primarily demonstrate background suppression rather than strong contrast-filled vessel enhancement.

---

# 📌 Important Data Policy

Medical imaging data can contain sensitive information.

Before uploading any dataset to GitHub:

```text
🔐 Check anonymization
        ↓
📜 Check dataset license
        ↓
📋 Check redistribution rules
        ↓
🚫 Remove patient-identifying information
        ↓
✅ Upload only permitted data
```

Do not commit restricted or identifiable patient data to the repository.

---

# 🩺 Research / Educational Disclaimer

> ⚠️ This project is intended for **research, education, and assignment purposes only**.
>
> It is not a certified medical device and should not be used for diagnosis, treatment planning, or independent clinical decision-making.

---

# 👨‍💻 Author

## Hrushikesh Kate

🎓 **B.Tech Computer Engineering — AI & ML**

### Areas of Interest

* 🤖 Artificial Intelligence
* 🧠 Machine Learning
* 👁️ Computer Vision
* 🧬 Medical Image Processing
* 🧠 Deep Learning
* ✨ Generative AI
* ⚙️ AI Automation

---

# ⭐ Project Highlights

```text
╔══════════════════════════════════════════════╗
║     🫀 CORONARY ANGIOGRAPHY ENHANCEMENT     ║
╠══════════════════════════════════════════════╣
║ 🩻 16-bit Medical Image Processing           ║
║ ⚫ Black-Hat Vessel Enhancement              ║
║ 🧹 Anatomical Background Suppression         ║
║ 🎞️ Temporal Reference Subtraction            ║
║ 📐 Translation Registration                  ║
║ 🎯 Vessel Response Enhancement               ║
║ ✨ CLAHE Local Contrast Enhancement          ║
║ 🧪 Synthetic Cine Generation                 ║
║ ⚡ Real-Time CPU Pipeline                    ║
║ 📊 Detailed Performance Benchmarking        ║
║ 🎥 Cine / Video Processing                   ║
║ 🖼️ RAW → PROCESSED → ENHANCED               ║
║ 📁 DICOM / NPZ / TIFF / Image Folder        ║
╚══════════════════════════════════════════════╝
```

---

# 🌟 Final Result

```text
        🩻 RAW ANGIOGRAPHY
                │
                ▼
       🧹 BACKGROUND SUPPRESSION
                │
                ▼
        ⚫ VESSEL ENHANCEMENT
                │
                ▼
        ✨ CONTRAST ENHANCEMENT
                │
                ▼
        🫀 CORONARY ENHANCED
                │
                ▼
          📊 BENCHMARK
                │
                ▼
       ⚡ REAL-TIME ANALYSIS
```

> 🫀 **Enhance the vessels. Suppress the background. Measure the performance.**
