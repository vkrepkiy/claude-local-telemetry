#!/usr/bin/env python3
"""Make timestamped contact sheets for continuous raw video takes.

FFmpeg extracts frames. Pillow adds labels below each frame and assembles pages.
The source files are only read. Each run writes an auditable manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".mkv", ".avi"}
PTS_RE = re.compile(r"\bn:\s*0\s+pts:\s*-?\d+\s+pts_time:([0-9.]+)")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def probe(video: Path) -> dict:
    result = run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries",
        "format=duration,start_time:stream=width,height,start_time,avg_frame_rate,r_frame_rate"
        ":stream_tags=rotate:stream_side_data=rotation",
        "-of", "json", str(video),
    ])
    if result.returncode:
        raise RuntimeError(f"ffprobe failed for {video}: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    if not streams or "duration" not in data.get("format", {}):
        raise RuntimeError(f"No usable video stream or duration: {video}")
    stream = streams[0]
    turned = read_rotation(stream) % 180 != 0
    format_start = float(data["format"].get("start_time", 0.0))
    video_start = float(stream.get("start_time", format_start))
    return {
        "duration": float(data["format"]["duration"]),
        # Frame times are reported from the first video frame; seeks count from the container start.
        "video_start": video_start,
        "seek_offset": video_start - format_start,
        "fps": read_frame_rate(stream),
        "source_width": stream["width"],
        "source_height": stream["height"],
        "display_width": stream["height"] if turned else stream["width"],
        "display_height": stream["width"] if turned else stream["height"],
    }


def read_frame_rate(stream: dict) -> float | None:
    for key in ("avg_frame_rate", "r_frame_rate"):
        try:
            rate = Fraction(stream.get(key, ""))
        except (ValueError, ZeroDivisionError):
            continue
        if rate > 0:
            return round(float(rate), 6)
    return None


def read_rotation(stream: dict) -> int:
    """Degrees the player turns the coded frame, from the display matrix or the legacy tag."""
    for side_data in stream.get("side_data_list", []):
        if "rotation" in side_data:
            return int(float(side_data["rotation"]))
    return int(float(stream.get("tags", {}).get("rotate", 0)))


def cadence(duration: float) -> float:
    if duration <= 15:
        return 1.0
    if duration <= 40:
        return 2.0
    return 3.0


def sampling_times(duration: float, interval: float, start: float, end: float) -> list[float]:
    if end <= start:
        raise ValueError("End must follow start")
    if duration < 1 and start == 0 and end == duration:
        return [round(duration / 2, 3)]
    first = min(start + 0.25, end - 0.05)
    times = []
    t = first
    while t < end - 0.05:
        times.append(round(t, 3))
        t += interval
    # Ensure the last part of a take is represented without overcrowding short takes.
    last = min(duration - 0.08, end - 0.08)
    if last > start and (not times or last - times[-1] > interval * 0.75):
        times.append(round(last, 3))
    return sorted(set(max(0.0, min(duration - 0.04, t)) for t in times))


def clock(seconds: float) -> str:
    minutes = int(seconds // 60)
    return f"{minutes:02d}:{seconds - minutes * 60:05.2f}"


def extract(video: Path, seconds: float, target: Path, max_width: int, max_height: int,
            origin: dict) -> float:
    """Return the frame time in seconds since the first video frame."""
    seek = max(0.0, seconds + origin["seek_offset"])
    result = run([
        "ffmpeg", "-hide_banner", "-loglevel", "info", "-y", "-ss", f"{seek:.3f}",
        "-copyts", "-i", str(video), "-map", "0:v:0", "-frames:v", "1",
        "-vf", f"showinfo,scale={max_width}:{max_height}:force_original_aspect_ratio=decrease",
        "-q:v", "3", str(target),
    ])
    if result.returncode or not target.is_file():
        raise RuntimeError(f"ffmpeg failed at {clock(seconds)} in {video}: {result.stderr[-1200:]}")
    match = PTS_RE.search(result.stderr)
    if not match:
        raise RuntimeError(f"Could not read actual frame PTS at {clock(seconds)} in {video}")
    return round(float(match.group(1)) - origin["video_start"], 6)


def extract_with_retry(video: Path, seconds: float, target: Path,
                       max_width: int, max_height: int, origin: dict) -> tuple[float, float]:
    """Some containers report audio-tail duration beyond their last video frame."""
    last_error = None
    for retreat in (0.0, 0.08, 0.16, 0.32, 0.64, 1.0):
        seek = max(0.0, seconds - retreat)
        target.unlink(missing_ok=True)
        try:
            return extract(video, seek, target, max_width, max_height, origin), seek
        except RuntimeError as error:
            last_error = error
    raise RuntimeError(f"Could not extract a frame near {clock(seconds)}: {last_error}")


def get_font(size: int, specified: str | None) -> ImageFont.FreeTypeFont:
    for path in [specified, "/System/Library/Fonts/Supplemental/Arial.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if path and Path(path).is_file():
            return ImageFont.truetype(path, size)
    raise RuntimeError("A TrueType font is required; supply --font /path/to/font.ttf")


def make_pages(out_dir: Path, frames: list[dict], source_name: str, sample_set_id: str,
               portrait: bool, tile_width: int, font_path: str | None) -> list[dict]:
    columns, max_rows = (2, 2) if portrait else (3, 3)
    with Image.open(out_dir / frames[0]["frame_path"]) as first:
        frame_height = round(tile_width * min(2.5, first.height / first.width))
    caption_height = 48
    tile_height = frame_height + caption_height
    margin = 14
    cell_gap = 14
    header_height = 82
    label_font = get_font(27, font_path)
    title_font = get_font(27, font_path)
    subtitle_font = get_font(21, font_path)
    pages = []
    page_count = math.ceil(len(frames) / (columns * max_rows))
    for page_index in range(page_count):
        start = page_index * columns * max_rows
        group = frames[start:start + columns * max_rows]
        page_columns = min(columns, len(group))
        if not portrait and len(group) == 4:
            page_columns = 2
        used_rows = math.ceil(len(group) / page_columns)
        canvas = Image.new("RGB", (page_columns * tile_width + (page_columns - 1) * cell_gap + 2 * margin,
                                   used_rows * tile_height + (used_rows - 1) * cell_gap
                                   + header_height + 2 * margin), "#101010")
        draw = ImageDraw.Draw(canvas)
        draw.text((margin, 7), f"{source_name}     page {page_index + 1}/{page_count}",
                  font=title_font, fill="white")
        draw.text((margin, 43), f"{sample_set_id}   time MM:SS.ss", font=subtitle_font, fill="#b8d9ff")
        for j, frame in enumerate(group):
            row, col = divmod(j, page_columns)
            x = margin + col * (tile_width + cell_gap)
            y = margin + header_height + row * (tile_height + cell_gap)
            with Image.open(out_dir / frame["frame_path"]) as image:
                image = image.convert("RGB")
                # Letterbox inside the cell; preserve the recorded orientation.
                image.thumbnail((tile_width, frame_height), Image.Resampling.LANCZOS)
                px = x + (tile_width - image.width) // 2
                py = y + (frame_height - image.height) // 2
                canvas.paste(image, (px, py))
            draw.rectangle((x, y + frame_height, x + tile_width - 1,
                            y + tile_height - 1), fill="#191919")
            prefix = "D#" if sample_set_id != "overview" else "#"
            draw.text((x + 12, y + frame_height + 7), f"{prefix}{frame['index']:02d}",
                      font=label_font, fill="#b8d9ff")
            draw.line((x + 92, y + frame_height + 9, x + 92,
                       y + tile_height - 9), fill="#777777", width=2)
            draw.text((x + 108, y + frame_height + 7), clock(frame["actual_seconds"]),
                      font=label_font, fill="white")
            # Keep the frame and its exact time in one visible bounded unit.
            draw.rectangle((x - 3, y - 3, x + tile_width + 2, y + tile_height + 2),
                           outline="#67b7ff", width=3)
            frame["page"] = page_index + 1
            frame["cell"] = j + 1
        page_name = f"sheet_{page_index + 1:02d}.jpg"
        canvas.save(out_dir / page_name, quality=88, subsampling=0)
        pages.append({"page": page_index + 1, "path": page_name,
                      "frame_indices": [f["index"] for f in group],
                      "columns": page_columns, "rows": used_rows})
    return pages


def process(video: Path, output_root: Path, args: argparse.Namespace) -> dict:
    info = probe(video)
    duration = info["duration"]
    start = max(0.0, args.start)
    end = min(duration, args.end if args.end is not None else duration)
    interval = args.interval or cadence(duration)
    if interval < 0.1 or start >= end:
        raise ValueError(f"Invalid sampling range or interval for {video}")
    source_id = video.stem + "-" + hashlib.sha256(str(video.resolve()).encode()).hexdigest()[:8]
    suffix = f"range_{clock(start).replace(':','-')}_{clock(end).replace(':','-')}" if args.end is not None or start else "overview"
    out_dir = output_root / source_id / suffix
    out_dir.mkdir(parents=True, exist_ok=True)
    for pattern in ("frame_*.jpg", "sheet_*.jpg", "manifest.json"):
        for old in out_dir.glob(pattern):
            old.unlink()
    times = sampling_times(duration, interval, start, end)
    frames = []
    preview_width = args.tile_width or 640
    first_name = "frame_001.jpg"
    first_actual, first_seek = extract_with_retry(video, times[0], out_dir / first_name,
                                                   preview_width, round(preview_width * 2.5), info)
    with Image.open(out_dir / first_name) as first:
        portrait = first.height > first.width
    tile_width = args.tile_width or (480 if portrait else 640)
    if tile_width != preview_width:
        first_actual, first_seek = extract_with_retry(video, times[0], out_dir / first_name,
                                                       tile_width, round(tile_width * 2.5), info)
    frames.append({"index": 1, "requested_seconds": times[0], "seek_seconds": first_seek,
                   "actual_seconds": first_actual, "frame_path": first_name})
    for t in times[1:]:
        index = len(frames) + 1
        name = f"frame_{index:03d}.jpg"
        actual, used_seek = extract_with_retry(video, t, out_dir / name, tile_width,
                                                round(tile_width * 2.5), info)
        if actual <= frames[-1]["actual_seconds"] + 0.02:
            (out_dir / name).unlink()
            continue
        frames.append({"index": index, "requested_seconds": t, "seek_seconds": used_seek,
                       "actual_seconds": actual, "frame_path": name})
    pages = make_pages(out_dir, frames, video.name, suffix, portrait, tile_width, args.font)
    manifest = {"schema_version": 1, "source_id": source_id,
                "source_path": str(video.resolve()), "duration_seconds": duration,
                "fps": info["fps"],
                "source_width": info["source_width"], "source_height": info["source_height"],
                "display_width": info["display_width"], "display_height": info["display_height"],
                "display_orientation": "portrait" if portrait else "landscape",
                "sample_set_id": suffix, "sampling_interval_seconds": interval, "sample_range": [start, end],
                "tile_width": tile_width, "frames": frames, "pages": pages}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return {"source_id": source_id, "duration": duration, "out_dir": str(out_dir),
            "frames": len(frames), "pages": len(pages)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="one video file or a directory of videos")
    parser.add_argument("output", type=Path, help="directory for contact sheets and manifests")
    parser.add_argument("--interval", type=float, help="override automatic 1/2/3 second cadence")
    parser.add_argument("--start", type=float, default=0.0, help="start of optional detail range in seconds")
    parser.add_argument("--end", type=float, help="end of optional detail range in seconds")
    parser.add_argument("--tile-width", type=int, help="override adaptive cell width (640 landscape, 480 portrait)")
    parser.add_argument("--font", help="TrueType font for timestamps")
    args = parser.parse_args()
    if args.tile_width is not None and (args.tile_width < 320 or args.tile_width > 1200):
        parser.error("--tile-width must be between 320 and 1200")
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            parser.error(f"{tool} is not on PATH")
    if args.source.is_file():
        videos = [args.source]
    elif args.source.is_dir():
        videos = sorted(p for p in args.source.iterdir()
                        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS)
    else:
        parser.error("source is not a file or directory")
    if not videos:
        parser.error("no video files found")
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    failures = []
    for video in videos:
        try:
            result = process(video, args.output, args)
            results.append(result)
            print(f"{video.name}: {result['frames']} frames, {result['pages']} pages -> {result['out_dir']}", flush=True)
        except Exception as error:
            failures.append({"source_path": str(video), "error": str(error)})
            print(f"ERROR {video.name}: {error}", file=sys.stderr, flush=True)
    (args.output / "run_index.json").write_text(json.dumps(
        {"results": results, "failures": failures}, indent=2, ensure_ascii=False) + "\n")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
