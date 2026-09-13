#!/usr/bin/env python3
"""
analyzer/probe.py - Fast Local Pre-Flight Video Validator

Performs instantaneous (< 0.5s) structural checks via ffprobe and ffmpeg:
1. Aspect Ratio: strictly 9:16 vertical check (flags 16:9 horizontal / square uploads).
2. Resolution: checks if width >= 1080 and height >= 1920.
3. Audio Volume Dynamics: measures mean volume, peak volume, and digital clipping risks.
"""

import json
import subprocess
import sys
from typing import Dict, Any


def probe_video_structure(video_path: str) -> Dict[str, Any]:
    """Inspects container, streams, and codecs using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": f"ffprobe failed: {result.stderr.strip()}"}

    data = json.loads(result.stdout)
    vstream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    astream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)

    if not vstream:
        return {"error": "No video stream detected in file."}

    width = int(vstream.get("width", 0))
    height = int(vstream.get("height", 0))
    duration = float(data.get("format", {}).get("duration", 0.0))
    fps_raw = vstream.get("r_frame_rate", "30/1")
    try:
        num, den = fps_raw.split("/")
        fps = round(float(num) / float(den), 2)
    except Exception:
        fps = 30.0

    # Calculate Aspect Ratio
    ratio = width / height if height > 0 else 0.0
    is_vertical_9_16 = abs(ratio - (9.0 / 16.0)) < 0.05
    is_horizontal_16_9 = abs(ratio - (16.0 / 9.0)) < 0.05
    is_square_1_1 = abs(ratio - 1.0) < 0.05

    if is_vertical_9_16:
        ratio_label = "9:16 (Vertical Reel / Short)"
    elif is_horizontal_16_9:
        ratio_label = "16:9 (Horizontal Widescreen)"
    elif is_square_1_1:
        ratio_label = "1:1 (Square)"
    else:
        ratio_label = f"Custom ({width}:{height})"

    # Resolution Check (Ad standard is 1080x1920)
    meets_resolution = (width >= 1080 and height >= 1920) if is_vertical_9_16 else (width >= 1920 and height >= 1080)

    # Fast Audio Dynamics (volumedetect)
    audio_metrics = probe_audio_dynamics(video_path) if astream else {
        "has_audio": False,
        "mean_volume_db": -99.0,
        "max_volume_db": -99.0,
        "clipping_detected": False
    }

    return {
        "valid": True,
        "duration_sec": round(duration, 2),
        "width": width,
        "height": height,
        "fps": fps,
        "aspect_ratio": round(ratio, 4),
        "aspect_ratio_label": ratio_label,
        "is_vertical_9_16": is_vertical_9_16,
        "meets_resolution_1080p": meets_resolution,
        "audio": audio_metrics
    }


def probe_audio_dynamics(video_path: str) -> Dict[str, Any]:
    """Runs ffmpeg volumedetect to catch clipping or muffled audio."""
    cmd = [
        "ffmpeg", "-i", video_path, "-af", "volumedetect", "-f", "null", "-"
    ]
    proc = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)

    mean_vol = -20.0
    max_vol = -5.0
    for line in proc.stderr.splitlines():
        if "mean_volume:" in line:
            parts = line.split("mean_volume:")
            if len(parts) > 1:
                mean_vol = float(parts[1].replace("dB", "").strip())
        elif "max_volume:" in line:
            parts = line.split("max_volume:")
            if len(parts) > 1:
                max_vol = float(parts[1].replace("dB", "").strip())

    # Clipping occurs when max_volume hits 0.0 dB
    clipping = max_vol >= -0.1

    return {
        "has_audio": True,
        "mean_volume_db": mean_vol,
        "max_volume_db": max_vol,
        "clipping_detected": clipping
    }


if __name__ == "__main__":
    test_path = sys.argv[1] if len(sys.argv) > 1 else "/home/rythamo/from rahul laptop/content and ediiting/round 2 stick figures/test_sync.mp4"
    print(f"--- Probing: {test_path} ---")
    info = probe_video_structure(test_path)
    print(json.dumps(info, indent=2))
