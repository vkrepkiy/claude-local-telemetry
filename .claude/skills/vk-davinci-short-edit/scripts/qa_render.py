#!/usr/bin/env python3
"""Deterministic checks for a Resolve short-edit delivery; visual/audio review is separate."""

import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# volumedetect measures 16-bit samples, so a hard-clipped signal reads 0.0 dB and
# never above it. A sample peak this close to full scale is treated as clipping.
CLIPPING_PEAK_DBFS = -0.1
# r_frame_rate is the base rate the stream can represent; avg_frame_rate is frames
# over duration. They disagree by more than this fraction only for variable frame rate.
VARIABLE_FRAME_RATE_TOLERANCE = 0.01


class ArgumentParser(argparse.ArgumentParser):
    """Usage errors exit 1 like every other failure of this script."""

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def run(args, timeout=600):
    try:
        return subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise RuntimeError(f"{args[0]} not found on PATH; install ffmpeg") from exc


def parse_rate(text):
    """Turn an ffprobe rate such as '30000/1001' into frames per second."""
    top, _, bottom = str(text).partition("/")
    rate = float(top) / float(bottom or 1)
    if rate <= 0:
        raise ValueError(f"unknown frame rate {text!r}")
    return rate


def inspect_media(path, decode):
    probe = run([
        "ffprobe", "-v", "error", "-count_frames", "-show_entries",
        "format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,nb_read_frames",
        "-of", "json", str(path),
    ])
    if probe.returncode:
        raise RuntimeError(f"ffprobe failed for {path}: {probe.stderr.strip()}")
    data = json.loads(probe.stdout)
    videos = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    audios = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    if not videos:
        raise RuntimeError(f"No video stream: {path}")
    v = videos[0]
    result = {
        "bytes": path.stat().st_size,
        "container_duration_seconds": float(data.get("format", {}).get("duration", 0)),
        "video": {k: v.get(k) for k in ("codec_name", "width", "height", "r_frame_rate", "avg_frame_rate", "nb_read_frames")},
        "audio_codecs": [s.get("codec_name") for s in audios],
    }
    if decode:
        full = run(["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"])
        result["full_decode_ok"] = full.returncode == 0
        if full.returncode:
            result["decode_error"] = full.stderr[-1500:]
    black = run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
        "-vf", "blackdetect=d=0.0:pix_th=0.02:pic_th=0.98",
        "-an", "-f", "null", "-",
    ])
    if black.returncode:
        result["blackdetect_error"] = black.stderr[-1500:]
    result["black_intervals"] = [
        {"start": float(a), "end": float(b), "duration": float(c)}
        for a, b, c in re.findall(
            r"black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)", black.stderr
        )
    ]
    if audios:
        volume = run([
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
            "-vn", "-af", "volumedetect", "-f", "null", "-",
        ])
        peak = re.search(r"max_volume: ([\d.-]+) dB", volume.stderr)
        result["sample_peak_dbfs"] = float(peak.group(1)) if peak else None
        if volume.returncode:
            result["volume_error"] = volume.stderr[-1500:]
    return result


DELIVERABLE_SUFFIXES = {
    "project": ".drp", "preview": "_preview.mp4", "master": "_master.mov",
    "xml": ".fcpxml", "report": "_report.json",
}
DEFAULT_REQUIRED = "preview,report"


def parse_required(text):
    names = [name.strip() for name in text.split(",") if name.strip()]
    unknown = sorted(set(names) - set(DELIVERABLE_SUFFIXES))
    if unknown or not names:
        raise argparse.ArgumentTypeError(
            f"expected a comma list from {', '.join(DELIVERABLE_SUFFIXES)}; got {text!r}"
        )
    return set(names)


def read_report_timeline(path):
    """Read the report contract {"timeline": {"frames": <int>, "fps": <number>}}."""
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError(f"not JSON: {exc}") from exc
    timeline = report.get("timeline") if isinstance(report, dict) else None
    if not isinstance(timeline, dict):
        raise ValueError('expected an object with a "timeline" object')
    frames, fps = timeline.get("frames"), timeline.get("fps")
    if isinstance(frames, bool) or not isinstance(frames, int) or frames <= 0:
        raise ValueError(f"timeline.frames must be a positive integer, got {frames!r}")
    if isinstance(fps, bool) or not isinstance(fps, (int, float)) or fps <= 0:
        raise ValueError(f"timeline.fps must be a positive number, got {fps!r}")
    return {"frames": frames, "fps": fps}


def main():
    p = ArgumentParser(description=__doc__)
    p.add_argument("prefix", type=Path, help="Path without suffix, e.g. /path/edit_A_v1")
    p.add_argument("--width", type=int, default=1080)
    p.add_argument("--height", type=int, default=1920)
    p.add_argument("--fps", type=float, default=None, help="Expected output frame rate")
    p.add_argument("--skip-full-decode", action="store_true", help="For quick repeated checks only")
    p.add_argument(
        "--require", type=parse_required, default=parse_required(DEFAULT_REQUIRED),
        help=f"Deliverables that must exist, comma list from {','.join(DELIVERABLE_SUFFIXES)} "
             f"(default: {DEFAULT_REQUIRED}). Files present but not required are still checked.",
    )
    args = p.parse_args()
    prefix = args.prefix
    paths = {name: Path(str(prefix) + suffix) for name, suffix in DELIVERABLE_SUFFIXES.items()}
    result = {"files": {}, "media": {}, "errors": [], "manual_checks": [
        "Watch full edit and first three seconds", "Confirm evidence-critical source action and number identity",
        "Check phone safe area, crop, title alpha, sound synchronization, and Final Cut import",
    ]}
    for name, path in paths.items():
        exists = path.is_file() and path.stat().st_size > 0
        result["files"][name] = {"path": str(path), "required": name in args.require, "exists_nonempty": exists}
        if not exists and name in args.require:
            result["errors"].append(f"Missing or empty {name}: {path}")
    if result["files"]["xml"]["exists_nonempty"]:
        try:
            result["xml_root"] = ET.parse(paths["xml"]).getroot().tag
        except ET.ParseError as exc:
            result["errors"].append(f"Invalid XML: {exc}")
    timeline = {}
    if result["files"]["report"]["exists_nonempty"]:
        try:
            timeline = read_report_timeline(paths["report"])
        except ValueError as exc:
            result["errors"].append(f"Invalid report {paths['report']}: {exc}")
    expected_frames = timeline.get("frames")
    expected_fps = args.fps or timeline.get("fps")
    for name in ("preview", "master"):
        if not result["files"][name]["exists_nonempty"]:
            continue
        try:
            media = inspect_media(paths[name], not args.skip_full_decode)
            result["media"][name] = media
            video = media["video"]
            if (video["width"], video["height"]) != (args.width, args.height):
                result["errors"].append(f"{name}: unexpected resolution")
            if not media["audio_codecs"]:
                result["errors"].append(f"{name}: missing audio")
            if media.get("full_decode_ok") is False:
                result["errors"].append(f"{name}: full decode failed")
            if media["black_intervals"]:
                result["errors"].append(f"{name}: detected black intervals; inspect whether intentional")
            peak = media.get("sample_peak_dbfs")
            if peak is not None and peak >= CLIPPING_PEAK_DBFS:
                result["errors"].append(
                    f"{name}: audio clipping, sample peak {peak} dBFS >= {CLIPPING_PEAK_DBFS} dBFS"
                )
            if expected_frames is not None and int(video["nb_read_frames"]) != int(expected_frames):
                result["errors"].append(f"{name}: video frame count differs from report")
            average_fps = parse_rate(video["avg_frame_rate"])
            base_fps = parse_rate(video["r_frame_rate"])
            if abs(base_fps - average_fps) > VARIABLE_FRAME_RATE_TOLERANCE * base_fps:
                result["errors"].append(
                    f"{name}: variable frame rate (r_frame_rate {video['r_frame_rate']}, "
                    f"avg_frame_rate {video['avg_frame_rate']})"
                )
            if expected_fps is not None and abs(average_fps - float(expected_fps)) > 0.01:
                result["errors"].append(
                    f"{name}: average frame rate {average_fps:.3f} differs from expected {expected_fps}"
                )
        except (RuntimeError, ValueError, TypeError, KeyError, ZeroDivisionError, OSError,
                subprocess.TimeoutExpired) as exc:
            result["errors"].append(f"{name}: {exc}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["errors"] else 0


def run_guarded():
    """Every failure is a message and exit 1, never a traceback."""
    try:
        return main()
    except Exception as exc:  # last resort; expected failures are reported by main()
        print(json.dumps({"errors": [f"{type(exc).__name__}: {exc}"]}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(run_guarded())
