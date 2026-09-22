"""Generate a synthetic 16-bit cine sequence for installation/latency testing only.

This is NOT a clinically realistic dataset and must not be used to claim medical
accuracy. It simply proves that the pipeline accepts 16-bit frames and that the
benchmarking code works before a public angiography dataset is downloaded.
"""
from pathlib import Path
import cv2
import numpy as np


def build_frame(i: int, n: int = 60, size: int = 512) -> np.ndarray:
    rng = np.random.default_rng(1234 + i)
    y, x = np.mgrid[0:size, 0:size]

    # Smooth anatomical background / vignette.
    img = 39000 + 7000 * np.exp(-(((x-size*0.52)/210)**2 + ((y-size*0.52)/230)**2))

    # Bright-ish rib-like arcs.
    canvas = np.clip(img, 0, 65535).astype(np.uint16)
    for r in range(210, 390, 30):
        cv2.ellipse(canvas, (size//2, size//2+15), (r, int(r*0.70)), 0, 205, 335, 50000, 4)
    cv2.line(canvas, (size//2, 70), (size//2, 460), 51000, 13)  # spine-like structure

    # Contrast bolus rises after frame 5 and then fades.
    t = i / max(1, n-1)
    bolus = max(0.0, np.sin(np.pi * min(1.0, max(0.0, (t-0.08)/0.80))))
    dark = int(12000 * bolus)
    if dark > 0:
        pts = [(256, 190), (235, 215), (205, 245), (175, 280), (150, 325)]
        pts2 = [(256, 190), (280, 225), (310, 255), (340, 300), (360, 345)]
        pts3 = [(235, 215), (250, 260), (265, 305), (275, 355)]
        for path in (pts, pts2, pts3):
            cv2.polylines(canvas, [np.asarray(path, np.int32)], False, max(0, 36000-dark), 5, cv2.LINE_AA)
        # branches
        cv2.line(canvas, (205,245), (220,300), max(0, 37000-dark), 3, cv2.LINE_AA)
        cv2.line(canvas, (310,255), (295,315), max(0, 37000-dark), 3, cv2.LINE_AA)

    noise = rng.normal(0, 600, (size, size)).astype(np.int32)
    out = np.clip(canvas.astype(np.int32) + noise, 0, 65535).astype(np.uint16)
    return out


def main():
    out = Path("synthetic_cine")
    out.mkdir(exist_ok=True)
    for i in range(60):
        frame = build_frame(i)
        cv2.imwrite(str(out / f"frame_{i:04d}.tiff"), frame)
    print(f"Wrote 60 synthetic 16-bit TIFF frames to {out.resolve()}")


if __name__ == "__main__":
    main()
