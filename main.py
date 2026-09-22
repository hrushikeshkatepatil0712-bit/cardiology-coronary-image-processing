from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.pipeline import PipelineConfig, CoronaryEnhancementPipeline, make_comparison, to_display_u8
from src.io_utils import load_input
from src.benchmark import benchmark


def save_u16_tiff(path: Path, image16: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(path), image16)
    if not ok:
        raise RuntimeError(f"Failed to write {path}")


def save_sequence_video(path: Path, comparisons, fps: float = 20.0) -> None:
    if not comparisons:
        return
    h, w = comparisons[0].shape[:2]
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps if fps > 0 else 20.0, (w, h)
    )
    if not writer.isOpened():
        raise RuntimeError(f"Could not create video writer: {path}")
    for frame in comparisons:
        writer.write(frame)
    writer.release()


def main() -> None:
    ap = argparse.ArgumentParser(description="Real-time coronary angiography enhancement baseline")
    ap.add_argument("--input", required=True, help="Image, DICOM, NPZ cine, video, or folder of images")
    ap.add_argument("--output", default="outputs", help="Output directory")
    ap.add_argument("--reference-frame", type=int, default=0, help="Pre-contrast/reference frame index for cine sequences")
    ap.add_argument("--no-temporal", action="store_true", help="Disable reference-frame subtraction")
    ap.add_argument("--register", action="store_true", help="Enable translation-only reference registration (slower)")
    ap.add_argument("--percentile-normalization", action="store_true", help="More robust but slower per-frame normalization")
    ap.add_argument("--full-16bit-clahe", action="store_true", help="Use 16-bit CLAHE instead of the faster 8-bit local-contrast stage")
    ap.add_argument("--max-frames", type=int, default=None)
    ap.add_argument("--save-video", action="store_true")
    ap.add_argument("--no-benchmark", action="store_true")
    args = ap.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    frames, input_meta = load_input(args.input, max_frames=args.max_frames)
    if not frames:
        raise RuntimeError("No frames loaded")

    cfg = PipelineConfig(
        use_temporal_subtraction=not args.no_temporal,
        use_translation_registration=args.register,
        percentile_normalization=args.percentile_normalization,
        fast_clahe_8bit=not args.full_16bit_clahe,
    )
    pipe = CoronaryEnhancementPipeline(cfg)

    ref_idx = max(0, min(args.reference_frame, len(frames) - 1))
    if len(frames) > 1 and not args.no_temporal:
        pipe.set_reference(frames[ref_idx])

    comparisons = []
    first_processed = None
    first_enhanced = None
    for i, frame in enumerate(frames):
        processed, enhanced, _ = pipe.process_frame(frame)
        if i == 0:
            first_processed, first_enhanced = processed, enhanced
        if args.save_video:
            comparisons.append(make_comparison(frame, processed, enhanced))

    # Save 16-bit TIFF examples to prove high-bit-depth processing.
    save_u16_tiff(out / "raw_frame_0000_16bit.tiff", pipe.to_uint16(frames[0]))
    save_u16_tiff(out / "processed_frame_0000_16bit.tiff", first_processed)
    save_u16_tiff(out / "enhanced_frame_0000_16bit.tiff", first_enhanced)
    cv2.imwrite(str(out / "comparison_frame_0000.png"), make_comparison(frames[0], first_processed, first_enhanced))

    if args.save_video and len(frames) > 1:
        source_fps = float(input_meta.get("source_fps", 20.0) or 20.0)
        save_sequence_video(out / "comparison.mp4", comparisons, fps=source_fps)

    result = {
        "input_metadata": input_meta,
        "pipeline_config": vars(cfg),
    }
    if not args.no_benchmark:
        # Fixed reference remains set; I/O and file writing are deliberately excluded.
        result["benchmark"] = benchmark(pipe, frames)
        with open(out / "benchmark_results.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    print(f"\nOutputs written to: {out.resolve()}")


if __name__ == "__main__":
    main()
