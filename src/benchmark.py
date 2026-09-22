from __future__ import annotations

from typing import Sequence, Dict, Any
import os
import platform
import time
import cv2
import numpy as np

from .pipeline import CoronaryEnhancementPipeline


def hardware_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "logical_cpu_count": os.cpu_count(),
        "opencv_version": cv2.__version__,
        "opencv_cuda_device_count": int(cv2.cuda.getCudaEnabledDeviceCount()) if hasattr(cv2, "cuda") else 0,
    }
    try:
        import psutil
        info["ram_gb"] = round(psutil.virtual_memory().total / (1024**3), 2)
    except Exception:
        info["ram_gb"] = "psutil unavailable"
    return info


def benchmark(
    pipeline: CoronaryEnhancementPipeline,
    frames: Sequence[np.ndarray],
    warmup: int = 5,
) -> Dict[str, Any]:
    if not frames:
        raise ValueError("No frames to benchmark")

    # Warm-up excludes Python/OpenCV one-time initialization from measured runs.
    for i in range(min(warmup, len(frames))):
        pipeline.process_frame(frames[i])

    latencies = []
    stage_totals = {}
    t_all = time.perf_counter_ns()
    for frame in frames:
        t0 = time.perf_counter_ns()
        _, _, stages = pipeline.process_frame(frame)
        t1 = time.perf_counter_ns()
        latencies.append((t1 - t0) / 1e6)
        for k, v in stages.items():
            stage_totals.setdefault(k, []).append(v)
    t_end = time.perf_counter_ns()

    a = np.asarray(latencies, dtype=np.float64)
    total_s = (t_end - t_all) / 1e9
    result: Dict[str, Any] = {
        "frames_tested": int(len(a)),
        "height": int(frames[0].shape[0]),
        "width": int(frames[0].shape[1]),
        "dtype": str(frames[0].dtype),
        "average_latency_ms": float(a.mean()),
        "minimum_latency_ms": float(a.min()),
        "maximum_latency_ms": float(a.max()),
        "p50_latency_ms": float(np.percentile(a, 50)),
        "p95_latency_ms": float(np.percentile(a, 95)),
        "p99_latency_ms": float(np.percentile(a, 99)),
        "fps_from_average_latency": float(1000.0 / a.mean()),
        "throughput_fps_total": float(len(a) / total_s),
        "meets_36ms_maximum": bool(a.max() <= 36.0),
        "hardware": hardware_info(),
        "mean_stage_ms": {k: float(np.mean(v)) for k, v in stage_totals.items()},
    }
    return result
