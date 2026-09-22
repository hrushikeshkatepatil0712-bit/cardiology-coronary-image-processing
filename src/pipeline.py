from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Dict
import time
import cv2
import numpy as np


@dataclass
class PipelineConfig:
    """Configuration for the real-time coronary enhancement baseline.

    The fast/default path is CPU-only classical image processing. It is designed
    to be explainable and benchmarkable. Parameters should be tuned on the
    chosen angiography dataset and hardware.
    """

    gaussian_ksize: int = 3
    background_kernel: int = 31
    blackhat_kernel: int = 11
    clahe_clip_limit: float = 2.0
    clahe_grid: Tuple[int, int] = (8, 8)
    use_temporal_subtraction: bool = True
    use_translation_registration: bool = False
    percentile_normalization: bool = False
    low_percentile: float = 1.0
    high_percentile: float = 99.5
    vessel_gain: float = 1.15
    fast_clahe_8bit: bool = True


class CoronaryEnhancementPipeline:
    """Fast 16-bit coronary angiography enhancement pipeline.

    Output definitions:
      processed: anatomy/background-suppressed vessel-response image (uint16)
      enhanced: CLAHE-enhanced vessel-response image (uint16)

    The algorithm assumes contrast-filled coronary vessels appear darker than
    much of the surrounding anatomy in the input representation. If a dataset
    is inverted, invert it before processing or use DICOM MONOCHROME1 handling
    in io_utils.py.
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.cfg = config or PipelineConfig()
        self._validate_config()
        self._kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self.cfg.blackhat_kernel, self.cfg.blackhat_kernel),
        )
        self._clahe = cv2.createCLAHE(
            clipLimit=self.cfg.clahe_clip_limit,
            tileGridSize=self.cfg.clahe_grid,
        )
        self._reference16: Optional[np.ndarray] = None
        self._reference_den16: Optional[np.ndarray] = None

    def _validate_config(self) -> None:
        for name in ("gaussian_ksize", "background_kernel", "blackhat_kernel"):
            v = int(getattr(self.cfg, name))
            if v < 1 or v % 2 == 0:
                raise ValueError(f"{name} must be a positive odd integer; got {v}")
        if not (0 <= self.cfg.low_percentile < self.cfg.high_percentile <= 100):
            raise ValueError("Percentiles must satisfy 0 <= low < high <= 100")

    @staticmethod
    def _as_gray(frame: np.ndarray) -> np.ndarray:
        if frame.ndim == 2:
            return frame
        if frame.ndim == 3 and frame.shape[-1] in (3, 4):
            code = cv2.COLOR_BGR2GRAY if frame.shape[-1] == 3 else cv2.COLOR_BGRA2GRAY
            return cv2.cvtColor(frame, code)
        raise ValueError(f"Expected grayscale or BGR/BGRA frame; got shape={frame.shape}")

    @staticmethod
    def to_uint16(frame: np.ndarray) -> np.ndarray:
        """Convert an image to uint16 without assuming an 8-bit input range."""
        x = CoronaryEnhancementPipeline._as_gray(np.asarray(frame))
        if x.dtype == np.uint16:
            return np.ascontiguousarray(x)
        if x.dtype == np.uint8:
            return np.ascontiguousarray(x.astype(np.uint16) * 257)

        xf = x.astype(np.float32, copy=False)
        finite = np.isfinite(xf)
        if not np.any(finite):
            return np.zeros(x.shape, dtype=np.uint16)
        lo = float(np.min(xf[finite]))
        hi = float(np.max(xf[finite]))
        if hi <= lo:
            return np.zeros(x.shape, dtype=np.uint16)
        out = (xf - lo) * (65535.0 / (hi - lo))
        np.clip(out, 0.0, 65535.0, out=out)
        return np.ascontiguousarray(out.astype(np.uint16))

    def normalize16(self, frame: np.ndarray) -> np.ndarray:
        x = self.to_uint16(frame)
        if not self.cfg.percentile_normalization:
            # Fast path: use full frame min/max. This is typically much faster
            # than per-frame percentiles and therefore better for the 36 ms goal.
            mn, mx, _, _ = cv2.minMaxLoc(x)
            if mx <= mn:
                return np.zeros_like(x)
            return cv2.normalize(x, None, 0, 65535, cv2.NORM_MINMAX, dtype=cv2.CV_16U)

        xf = x.astype(np.float32)
        lo = float(np.percentile(xf, self.cfg.low_percentile))
        hi = float(np.percentile(xf, self.cfg.high_percentile))
        if hi <= lo:
            return np.zeros_like(x)
        xf = (xf - lo) * (65535.0 / (hi - lo))
        np.clip(xf, 0.0, 65535.0, out=xf)
        return xf.astype(np.uint16)

    def _denoise(self, frame16: np.ndarray) -> np.ndarray:
        return cv2.GaussianBlur(
            frame16,
            (self.cfg.gaussian_ksize, self.cfg.gaussian_ksize),
            sigmaX=0,
            borderType=cv2.BORDER_REPLICATE,
        )

    def set_reference(self, reference_frame: Optional[np.ndarray]) -> None:
        """Set a pre-contrast/reference cine frame for temporal subtraction.

        A good reference is a frame where contrast-filled arteries are minimal.
        Static ribs/spine/lung structures then cancel more effectively.
        """
        if reference_frame is None:
            self._reference16 = None
            self._reference_den16 = None
            return
        # Keep the reference in the same native uint16 intensity scale as the
        # cine sequence. Per-frame normalization would corrupt temporal subtraction.
        ref = self.to_uint16(reference_frame)
        self._reference16 = ref
        self._reference_den16 = self._denoise(ref)

    @staticmethod
    def _translation_align(reference16: np.ndarray, current16: np.ndarray) -> np.ndarray:
        """Fast translational registration using phase correlation.

        Optional because registration costs latency. It can help when the cine
        sequence has small table/patient translations. It does not compensate
        for cardiac deformation/rotation.
        """
        ref32 = reference16.astype(np.float32)
        cur32 = current16.astype(np.float32)
        shift, _ = cv2.phaseCorrelate(ref32, cur32)
        dx, dy = shift
        M = np.array([[1.0, 0.0, dx], [0.0, 1.0, dy]], dtype=np.float32)
        return cv2.warpAffine(
            reference16,
            M,
            (current16.shape[1], current16.shape[0]),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, Dict[str, float]]:
        """Process one frame and return (processed16, enhanced16, stage_ms)."""
        stage: Dict[str, float] = {}
        t0 = time.perf_counter_ns()

        # For temporal subtraction, preserve the cine sequence's common native
        # uint16 scale. For isolated images, normalize per image for robustness.
        if self.cfg.use_temporal_subtraction and self._reference_den16 is not None:
            norm = self.to_uint16(frame)
        else:
            norm = self.normalize16(frame)
        t1 = time.perf_counter_ns()
        stage["normalize_ms"] = (t1 - t0) / 1e6

        den = self._denoise(norm)
        t2 = time.perf_counter_ns()
        stage["denoise_ms"] = (t2 - t1) / 1e6

        # 1) Suppress slowly varying background (lungs/soft tissue illumination)
        #    and emphasize dark local structures.
        # Fast box filtering is intentionally used instead of a very wide Gaussian.
        # It estimates low-frequency background with substantially lower latency.
        smooth_bg = cv2.boxFilter(
            den,
            ddepth=-1,
            ksize=(self.cfg.background_kernel, self.cfg.background_kernel),
            normalize=True,
            borderType=cv2.BORDER_REPLICATE,
        )
        lowfreq_response = cv2.subtract(smooth_bg, den)

        # Black-hat morphology highlights dark vessel-like structures while
        # suppressing broader anatomy. A single scale is used in the real-time
        # default to protect the 36 ms latency budget.
        blackhat = cv2.morphologyEx(den, cv2.MORPH_BLACKHAT, self._kernel)
        vessel_response = cv2.max(lowfreq_response, blackhat)

        # 3) Temporal/reference subtraction: a pre-contrast reference suppresses
        #    persistent ribs/spine/lung background. This is the closest classical
        #    analogue to digital subtraction for cine sequences.
        if self.cfg.use_temporal_subtraction and self._reference_den16 is not None:
            ref_den = self._reference_den16
            if self.cfg.use_translation_registration:
                ref_den = self._translation_align(ref_den, den)
            temporal = cv2.subtract(ref_den, den)
            vessel_response = cv2.max(vessel_response, temporal)

        t3 = time.perf_counter_ns()
        stage["suppression_ms"] = (t3 - t2) / 1e6

        # Mild high-frequency boost. Keep this simple/fast for real-time use.
        soft = cv2.GaussianBlur(vessel_response, (0, 0), sigmaX=1.2)
        boosted = cv2.addWeighted(
            vessel_response,
            self.cfg.vessel_gain,
            soft,
            -(self.cfg.vessel_gain - 1.0),
            0,
        )
        processed = cv2.normalize(
            boosted, None, 0, 65535, cv2.NORM_MINMAX, dtype=cv2.CV_16U
        )
        t4 = time.perf_counter_ns()
        stage["vessel_boost_ms"] = (t4 - t3) / 1e6

        # Local contrast enhancement. The default fast path converts only the
        # vessel-response image to 8-bit for CLAHE, then maps it back to uint16.
        # Raw input handling and the suppression pipeline remain 16-bit. This
        # significantly reduces latency on CPU. Set fast_clahe_8bit=False if
        # full 16-bit CLAHE is required and benchmark the resulting cost.
        if self.cfg.fast_clahe_8bit:
            p8 = cv2.normalize(processed, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
            e8 = self._clahe.apply(p8)
            enhanced = e8.astype(np.uint16) * np.uint16(257)
        else:
            enhanced = self._clahe.apply(processed)
        t5 = time.perf_counter_ns()
        stage["clahe_ms"] = (t5 - t4) / 1e6
        stage["total_ms"] = (t5 - t0) / 1e6

        return processed, enhanced, stage


def to_display_u8(image16: np.ndarray) -> np.ndarray:
    """Convert processed uint16 to 8-bit only for display/video export."""
    x = CoronaryEnhancementPipeline.to_uint16(image16)
    return cv2.normalize(x, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)


def make_comparison(raw: np.ndarray, processed16: np.ndarray, enhanced16: np.ndarray) -> np.ndarray:
    raw8 = to_display_u8(raw)
    p8 = to_display_u8(processed16)
    e8 = to_display_u8(enhanced16)
    panels = []
    for img, title in ((raw8, "RAW"), (p8, "BACKGROUND SUPPRESSED"), (e8, "CORONARY ENHANCED")):
        bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        cv2.rectangle(bgr, (0, 0), (bgr.shape[1], 28), (0, 0, 0), -1)
        cv2.putText(bgr, title, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)
        panels.append(bgr)
    return cv2.hconcat(panels)
