# Coronary Angiography Image Enhancement — Real-Time Baseline

## Purpose
This project is a research/assignment baseline for enhancing contrast-filled coronary arteries in X-ray/cine angiography while suppressing slowly varying anatomical background and persistent structures. It supports 16-bit grayscale processing and measures end-to-end **processing-pipeline latency** per frame.

> **Important:** This is research/educational software, not a certified medical device and not for diagnosis or clinical decision-making.

## What the pipeline does
1. Preserve/convert input to 16-bit grayscale.
2. Normalize intensity.
3. Apply light Gaussian denoising.
4. Estimate/suppress slowly varying anatomical background using a fast box filter.
5. Use black-hat morphology to emphasize dark, thin vessel-like structures.
6. Optionally subtract a pre-contrast cine reference frame to suppress persistent ribs/spine/lung background.
7. Apply a light vessel-response boost.
8. Apply CLAHE for local contrast enhancement. The default real-time path uses 8-bit CLAHE on the vessel-response image for speed, then maps the result back to uint16; raw input and background-suppression processing remain 16-bit.
9. Produce raw / background-suppressed / coronary-enhanced comparisons.
10. Benchmark average, minimum, maximum, p50/p95/p99 latency and FPS.

## Supported input
- 16-bit TIFF/PNG/PGM and common image formats
- Multi-frame DICOM (`.dcm`)
- NumPy compressed cine (`.npz`) such as public angiography datasets
- MP4/AVI/MOV/MKV (decoded video is usually 8-bit, so use DICOM/TIFF/NPZ to demonstrate true 16-bit support)
- Folder of image frames

## Setup
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Quick installation test with synthetic 16-bit data
```bash
python demo_synthetic.py
python main.py --input synthetic_cine --output outputs --reference-frame 0 --save-video
```

The synthetic sequence is only for code/latency testing. Do not use it to claim medical accuracy.

## Run on a DICOM cine
```bash
python main.py --input path/to/coronary_cine.dcm --output outputs --reference-frame 0 --save-video
```

## Run on an NPZ cine dataset
```bash
python main.py --input path/to/study/view.npz --output outputs --reference-frame 0 --max-frames 300 --save-video
```

## Run on a folder of extracted 16-bit frames
```bash
python main.py --input path/to/frames --output outputs --reference-frame 0 --save-video
```

## Reference frame
For cine sequences, `--reference-frame` should ideally point to a **pre-contrast or low-contrast frame** where coronary arteries are not yet strongly opacified. This improves cancellation of persistent ribs/spine/background anatomy. DICOM/NPZ cine frames are kept on one common uint16 intensity scale so temporal subtraction remains meaningful.

If a useful reference is unavailable:
```bash
python main.py --input path/to/data --output outputs --no-temporal
```

## Optional translation registration
Small table/patient translations can be handled with:
```bash
python main.py --input path/to/data --output outputs --reference-frame 0 --register
```
Registration costs latency, so benchmark with and without it. It does not correct full cardiac deformation.

## Full 16-bit CLAHE option
For maximum bit-depth preservation in the final local-contrast stage:
```bash
python main.py --input path/to/data --output outputs --full-16bit-clahe
```
This is slower on many CPUs, so re-run the latency benchmark before claiming the 36 ms target.

## 36 ms requirement
The assignment's mandatory requirement is **maximum processing latency <= 36 ms/frame**. The benchmark deliberately excludes disk loading and output-file writing, and measures from the frame entering the processing pipeline until the final enhanced frame is produced.

`outputs/benchmark_results.json` reports:
- average latency
- minimum latency
- maximum latency
- p50 / p95 / p99
- FPS from mean latency
- overall throughput
- image size and dtype
- CPU/RAM/OpenCV configuration
- whether the measured maximum was <= 36 ms

**Do not claim the 36 ms target until it is measured on the exact submission hardware and real dataset.** Performance depends on CPU, resolution, OpenCV build, registration, and parameters.

## Output files
- `raw_frame_0000_16bit.tiff`
- `processed_frame_0000_16bit.tiff`
- `enhanced_frame_0000_16bit.tiff`
- `comparison_frame_0000.png`
- `comparison.mp4` (for sequences when `--save-video` is used)
- `benchmark_results.json`

## Dataset recommendation
For cine/sequence behaviour, use a public coronary angiography **video** dataset such as CoronaryDominance or CADICA. For expert-labeled vessel validation, use ARCADE or DCA1. Follow each dataset's license/usage rules and do not redistribute restricted data.

## Interpreting the method honestly
This baseline performs **suppression/enhancement**, not anatomical semantic segmentation of every rib/spine/lung structure. The reference-frame subtraction suppresses persistent anatomy, while local morphology emphasizes vessel-like structures. If the evaluator expects explicit pixel-wise anatomical removal, a trained segmentation model would be a separate, more complex extension and must still satisfy the 36 ms limit.
