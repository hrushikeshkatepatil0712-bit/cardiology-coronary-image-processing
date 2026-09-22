from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple, Any
import cv2
import numpy as np

IMAGE_EXTS = {".png", ".tif", ".tiff", ".pgm", ".bmp", ".jpg", ".jpeg"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".m4v"}


def _scale_to_uint16(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr)
    if arr.dtype == np.uint16:
        return np.ascontiguousarray(arr)
    if arr.dtype == np.uint8:
        return np.ascontiguousarray(arr.astype(np.uint16) * 257)
    af = arr.astype(np.float32)
    finite = np.isfinite(af)
    if not np.any(finite):
        return np.zeros(arr.shape, dtype=np.uint16)
    lo = float(af[finite].min())
    hi = float(af[finite].max())
    if hi <= lo:
        return np.zeros(arr.shape, dtype=np.uint16)
    af = (af - lo) * (65535.0 / (hi - lo))
    np.clip(af, 0, 65535, out=af)
    return np.ascontiguousarray(af.astype(np.uint16))



def _scale_sequence_to_uint16(arr: np.ndarray) -> np.ndarray:
    """Scale a complete sequence with one common mapping to preserve temporal differences."""
    arr = np.asarray(arr)
    if arr.dtype == np.uint16:
        return np.ascontiguousarray(arr)
    if arr.dtype == np.uint8:
        return np.ascontiguousarray(arr.astype(np.uint16) * 257)
    af = arr.astype(np.float32)
    finite = np.isfinite(af)
    if not np.any(finite):
        return np.zeros(arr.shape, dtype=np.uint16)
    lo = float(af[finite].min())
    hi = float(af[finite].max())
    if hi <= lo:
        return np.zeros(arr.shape, dtype=np.uint16)
    af = (af - lo) * (65535.0 / (hi - lo))
    np.clip(af, 0, 65535, out=af)
    return np.ascontiguousarray(af.astype(np.uint16))

def _gray(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr)
    if arr.ndim == 2:
        return arr
    if arr.ndim == 3 and arr.shape[-1] in (3, 4):
        code = cv2.COLOR_BGR2GRAY if arr.shape[-1] == 3 else cv2.COLOR_BGRA2GRAY
        return cv2.cvtColor(arr, code)
    raise ValueError(f"Cannot convert array with shape {arr.shape} to a grayscale frame")


def load_image(path: Path) -> np.ndarray:
    # IMREAD_UNCHANGED is essential to preserve 16-bit TIFF/PNG when present.
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"OpenCV could not read image: {path}")
    return _scale_to_uint16(_gray(img))


def load_dicom(path: Path) -> Tuple[List[np.ndarray], dict]:
    try:
        import pydicom
    except ImportError as exc:
        raise RuntimeError("pydicom is required for DICOM input: pip install pydicom") from exc

    ds = pydicom.dcmread(str(path))
    px = ds.pixel_array
    meta = {
        "Rows": getattr(ds, "Rows", None),
        "Columns": getattr(ds, "Columns", None),
        "NumberOfFrames": getattr(ds, "NumberOfFrames", 1),
        "BitsStored": getattr(ds, "BitsStored", None),
        "BitsAllocated": getattr(ds, "BitsAllocated", None),
        "PhotometricInterpretation": getattr(ds, "PhotometricInterpretation", None),
    }

    slope = float(getattr(ds, "RescaleSlope", 1.0))
    intercept = float(getattr(ds, "RescaleIntercept", 0.0))
    if slope != 1.0 or intercept != 0.0 or not np.issubdtype(px.dtype, np.unsignedinteger):
        px = px.astype(np.float32) * slope + intercept

    if px.ndim == 2:
        px = px[None, ...]
    elif px.ndim == 4 and px.shape[-1] in (3, 4):
        px = np.stack([_gray(f) for f in px], axis=0)
    elif px.ndim != 3:
        raise ValueError(f"Unsupported DICOM pixel array shape: {px.shape}")

    # One common scale for the entire cine sequence preserves frame-to-frame
    # intensity differences needed by temporal/reference subtraction.
    px16 = _scale_sequence_to_uint16(px)
    mono1 = str(meta.get("PhotometricInterpretation") or "").upper() == "MONOCHROME1"
    if mono1:
        px16 = np.uint16(65535) - px16
    frames = [np.ascontiguousarray(f) for f in px16]
    return frames, meta


def _find_frame_array(obj: Any) -> Optional[np.ndarray]:
    """Find a plausible image/video ndarray recursively in an NPZ/object dict."""
    if isinstance(obj, np.ndarray):
        if obj.dtype == object and obj.size == 1:
            try:
                return _find_frame_array(obj.item())
            except Exception:
                pass
        if obj.ndim in (2, 3, 4) and obj.size > 1024:
            return obj
        return None
    if isinstance(obj, dict):
        # Prefer likely image/video keys first.
        preferred = ["frames", "video", "images", "image", "pixel_array", "data", "arr_0"]
        for k in preferred:
            if k in obj:
                found = _find_frame_array(obj[k])
                if found is not None:
                    return found
        for v in obj.values():
            found = _find_frame_array(v)
            if found is not None:
                return found
    if isinstance(obj, (list, tuple)):
        for v in obj:
            found = _find_frame_array(v)
            if found is not None:
                return found
    return None


def load_npz(path: Path) -> Tuple[List[np.ndarray], dict]:
    data = np.load(str(path), allow_pickle=True)
    obj = {k: data[k] for k in data.files}
    arr = _find_frame_array(obj)
    if arr is None:
        raise ValueError(f"Could not locate a 2D/3D/4D image array in NPZ keys: {data.files}")

    if arr.ndim == 2:
        arr = arr[None, ...]
    elif arr.ndim == 4 and arr.shape[-1] in (3, 4):
        arr = np.stack([_gray(f) for f in arr], axis=0)
    elif arr.ndim == 3:
        # Could be HxWxC single image or FxHxW sequence.
        if arr.shape[-1] in (3, 4) and arr.shape[0] > 32 and arr.shape[1] > 32:
            arr = _gray(arr)[None, ...]
    else:
        raise ValueError(f"Unsupported NPZ frame array shape: {arr.shape}")

    arr16 = _scale_sequence_to_uint16(arr)
    frames = [np.ascontiguousarray(f) for f in arr16]
    return frames, {"npz_keys": data.files, "shape": tuple(arr.shape)}


def load_video(path: Path, max_frames: Optional[int] = None) -> Tuple[List[np.ndarray], dict]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frames.append(gray.astype(np.uint16) * 257)
        if max_frames is not None and len(frames) >= max_frames:
            break
    cap.release()
    return frames, {"source_fps": fps, "frame_count": len(frames), "note": "Video codecs decode to 8-bit; use DICOM/TIFF/NPZ for true high-bit-depth input."}


def load_input(path: str, max_frames: Optional[int] = None) -> Tuple[List[np.ndarray], dict]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)

    if p.is_dir():
        files = sorted([q for q in p.iterdir() if q.suffix.lower() in IMAGE_EXTS])
        if max_frames is not None:
            files = files[:max_frames]
        if not files:
            raise ValueError(f"No supported images found in folder: {p}")
        frames = [load_image(q) for q in files]
        return frames, {"type": "image_folder", "frame_count": len(frames)}

    ext = p.suffix.lower()
    if ext == ".dcm":
        frames, meta = load_dicom(p)
        if max_frames is not None:
            frames = frames[:max_frames]
        meta["type"] = "dicom"
        meta["frame_count_loaded"] = len(frames)
        return frames, meta
    if ext == ".npz":
        frames, meta = load_npz(p)
        if max_frames is not None:
            frames = frames[:max_frames]
        meta["type"] = "npz"
        meta["frame_count_loaded"] = len(frames)
        return frames, meta
    if ext in IMAGE_EXTS:
        return [load_image(p)], {"type": "image", "frame_count": 1}
    if ext in VIDEO_EXTS:
        frames, meta = load_video(p, max_frames=max_frames)
        meta["type"] = "video"
        return frames, meta

    raise ValueError(f"Unsupported input extension: {ext}")
