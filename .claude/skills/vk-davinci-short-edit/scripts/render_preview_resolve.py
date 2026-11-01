#!/usr/bin/env python3
"""Render a non-destructive H.264 MP4 preview from the open DaVinci Resolve project.

The script uses Resolve's official scripting API. It never clears the render queue,
changes project media, or replaces an existing output unless --overwrite is given.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MODULE_PATHS = (
    "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules/DaVinciResolveScript.py",
    "/opt/resolve/Developer/Scripting/Modules/DaVinciResolveScript.py",
    os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    + r"\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules\DaVinciResolveScript.py",
)
TERMINAL_STATES = {"Complete", "Failed", "Cancelled"}
STOP_WAIT_SECONDS = 30


def stop_render(project: Any, staged: Path, poll_interval: float) -> None:
    """Stop Resolve's render, wait for it to let go of the file, then remove the partial."""
    project.StopRendering()
    deadline = time.monotonic() + STOP_WAIT_SECONDS
    while project.IsRenderingInProgress() and time.monotonic() < deadline:
        time.sleep(poll_interval)
    staged.unlink(missing_ok=True)


def resolve_api(module_path: str | None):
    """Load the installed Resolve API module without requiring it on PYTHONPATH."""
    candidates = [module_path] if module_path else []
    candidates += [os.environ.get("RESOLVE_SCRIPT_API"), *DEFAULT_MODULE_PATHS]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if path.is_file():
            # Import normally: the official wrapper swaps sys.modules[name] for
            # fusionscript, so spec_from_file_location can return the stale wrapper.
            module_name = "DaVinciResolveScript"
            sys.path.insert(0, str(path.parent))
            sys.modules.pop(module_name, None)
            try:
                module = importlib.import_module(module_name)
            finally:
                try:
                    sys.path.remove(str(path.parent))
                except ValueError:
                    pass
            if callable(getattr(module, "scriptapp", None)):
                return module, str(path)
            raise RuntimeError(f"Imported Resolve module lacks scriptapp(): {path}")
    raise RuntimeError(
        "DaVinciResolveScript.py not found. Pass --api-module or set RESOLVE_SCRIPT_API."
    )


def connect(api_module: Any):
    resolve = api_module.scriptapp("Resolve")
    if resolve is None:
        raise RuntimeError("Could not connect to Resolve. Open Resolve and its project first.")
    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject() if manager else None
    if project is None:
        raise RuntimeError("Resolve has no current project open.")
    timeline = project.GetCurrentTimeline()
    if timeline is None:
        raise RuntimeError("The current project has no active timeline.")
    return resolve, project, timeline


def delete_job(project: Any, job_id: str) -> None:
    """Leave the project's render queue as it was: remove the one job this run added."""
    try:
        deleted = project.DeleteRenderJob(job_id)
    except Exception as exc:
        deleted, reason = False, f"{type(exc).__name__}: {exc}"
    else:
        reason = "Resolve returned False"
    if not deleted:
        warning = {"warning": f"Could not delete render job {job_id} from the queue ({reason})"}
        print(json.dumps(warning, ensure_ascii=False), file=sys.stderr)


def api_inventory(project: Any, timeline: Any, api_path: str, include_formats: bool) -> dict[str, Any]:
    data = {
        "api_module": api_path,
        "project": project.GetName(),
        "timeline": timeline.GetName(),
        "timeline_frame_rate": timeline.GetSetting("timelineFrameRate"),
        "timeline_width": timeline.GetSetting("timelineResolutionWidth"),
        "timeline_height": timeline.GetSetting("timelineResolutionHeight"),
    }
    if include_formats:
        formats = project.GetRenderFormats() or {}
        data["render_formats_and_codecs"] = {}
        for fmt in formats:
            try:
                data["render_formats_and_codecs"][fmt] = project.GetRenderCodecs(fmt) or {}
            except Exception as exc:  # best effort across Resolve versions
                data["render_formats_and_codecs"][fmt] = {"error": str(exc)}
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output", nargs="?", type=Path,
        help="MP4 file path. Default: <cwd>/<project>_preview.mp4",
    )
    parser.add_argument("--api-module", help="Path to DaVinciResolveScript.py")
    parser.add_argument("--project", help="Require this exact name for the active project")
    parser.add_argument("--timeline", help="Require this exact name for the active timeline")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing output path")
    parser.add_argument("--dry-run", action="store_true", help="Connect and report planned output; do not queue or render")
    parser.add_argument("--introspect", action="store_true", help="Report project/timeline and installed render formats; do not render")
    parser.add_argument("--timeout", type=int, default=1200, help="Render timeout in seconds (default: 1200)")
    parser.add_argument("--poll-interval", type=float, default=2.0, help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.timeout < 1 or args.poll_interval <= 0:
        parser.error("--timeout and --poll-interval must be positive")

    project = job_id = staged = None
    keep_staged = False
    try:
        api, api_path = resolve_api(args.api_module)
        resolve, project, timeline = connect(api)
        if args.project and project.GetName() != args.project:
            raise RuntimeError(f"Active project is {project.GetName()!r}, expected {args.project!r}")
        if args.timeline and timeline.GetName() != args.timeline:
            raise RuntimeError(f"Active timeline is {timeline.GetName()!r}, expected {args.timeline!r}")
        target = (args.output or Path.cwd() / f"{project.GetName()}_preview.mp4").expanduser().resolve()
        if target.suffix.lower() != ".mp4":
            raise RuntimeError(f"Preview output must end in .mp4: {target}")
        if target.exists() and not args.overwrite:
            raise FileExistsError(f"Output already exists (use --overwrite to replace): {target}")
        if not target.parent.is_dir():
            raise RuntimeError(f"Output directory does not exist: {target.parent}")

        result: dict[str, Any] = {
            "status": "planned" if args.dry_run or args.introspect else "starting",
            "output": str(target),
            "overwrite_allowed": bool(args.overwrite),
            "render": {"format": "mp4", "codec": "H264", "all_timeline_frames": True,
                       "video": True, "audio": True},
            **api_inventory(project, timeline, api_path, args.introspect),
        }
        if args.introspect or args.dry_run:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        # Resolve's Timeline.GetEndFrame() is exclusive, like the half-open intervals of
        # AppendToTimeline and TimelineItem.GetStart()/GetEnd(): the timeline holds
        # GetEndFrame() - GetStartFrame() frames, and a full render must have exactly that many.
        timeline_frames = int(timeline.GetEndFrame()) - int(timeline.GetStartFrame())
        result["timeline_frames"] = timeline_frames
        if not project.SetCurrentRenderFormatAndCodec("mp4", "H264"):
            raise RuntimeError("Resolve rejected render format/codec mp4/H264")
        # Resolve renders into a unique staging name. Publish the requested path only
        # after Resolve reports completion and the staged file is present and nonempty.
        staging_name = f"{target.stem}.render-{uuid.uuid4().hex}.mp4"
        staged = target.parent / staging_name
        settings = {
            "SelectAllFrames": True,
            "TargetDir": str(target.parent),
            "CustomName": staged.stem,
            "ExportVideo": True,
            "ExportAudio": True,
            "AudioCodec": "aac",
            "FormatWidth": int(timeline.GetSetting("timelineResolutionWidth")),
            "FormatHeight": int(timeline.GetSetting("timelineResolutionHeight")),
            "FrameRate": float(timeline.GetSetting("timelineFrameRate")),
        }
        if not project.SetRenderSettings(settings):
            raise RuntimeError(f"Resolve rejected render settings: {settings}")
        job_id = project.AddRenderJob()
        if not job_id:
            raise RuntimeError("Resolve failed to add preview render job")
        result["job_id"] = job_id
        if not project.StartRendering(job_id):
            raise RuntimeError(f"Resolve failed to start render job {job_id}")
        result["status"] = "rendering"
        started = time.monotonic()
        while True:
            job_status = project.GetRenderJobStatus(job_id) or {}
            state = job_status.get("JobStatus")
            result["job_status"] = job_status
            if state in TERMINAL_STATES:
                break
            if time.monotonic() - started >= args.timeout:
                result["status"] = "timeout"
                stop_render(project, staged, args.poll_interval)
                raise TimeoutError(f"Render exceeded {args.timeout}s; job status: {job_status}")
            time.sleep(args.poll_interval)
        if state != "Complete":
            result["status"] = str(state or "failed")
            raise RuntimeError(f"Resolve render did not complete successfully: {job_status}")
        if not staged.is_file() or staged.stat().st_size == 0:
            result["status"] = "failed"
            raise RuntimeError(f"Resolve reported completion but staged output is missing/empty: {staged}")
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-count_frames", "-show_entries",
             "format=format_name,duration,size:"
             "stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames",
             "-of", "json", str(staged)],
            text=True, capture_output=True, timeout=600,
        )
        if probe.returncode:
            raise RuntimeError(f"ffprobe rejected staged preview: {probe.stderr.strip()}")
        media = json.loads(probe.stdout)
        video_streams = [s for s in media.get("streams", []) if s.get("codec_type") == "video"]
        audio_streams = [s for s in media.get("streams", []) if s.get("codec_type") == "audio"]
        if not video_streams or video_streams[0].get("codec_name") != "h264":
            raise RuntimeError(f"Preview has no H.264 video stream: {media}")
        if not audio_streams:
            raise RuntimeError(f"Preview has no audio stream: {media}")
        if (video_streams[0].get("width"), video_streams[0].get("height")) != (
            settings["FormatWidth"], settings["FormatHeight"]
        ):
            raise RuntimeError(f"Preview dimensions differ from timeline: {media}")
        rendered_frames = video_streams[0].get("nb_read_frames")
        if str(rendered_frames) != str(timeline_frames):
            raise RuntimeError(
                f"Preview has {rendered_frames} video frames, timeline has {timeline_frames}"
            )
        if "mp4" not in media.get("format", {}).get("format_name", ""):
            raise RuntimeError(f"Preview container is not MP4: {media.get('format')}")
        decoded = subprocess.run(
            ["ffmpeg", "-v", "error", "-xerror", "-i", str(staged), "-f", "null", "-"],
            text=True, capture_output=True, timeout=600,
        )
        if decoded.returncode:
            raise RuntimeError(f"Preview full decode failed: {decoded.stderr[-1000:]}")
        if target.exists() and not args.overwrite:
            result["status"] = "output_conflict"
            keep_staged = True
            raise FileExistsError(f"Output appeared during render; preserving both files: {target}")
        staged.replace(target)

        result["status"] = "complete"
        result["completed_at"] = datetime.now(timezone.utc).isoformat()
        result["file"] = {"path": str(target), "bytes": target.stat().st_size}
        result["media_probe"] = media
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        error = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(error, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    finally:
        # A staged file that was not published is a failed or partial render; only an
        # output conflict keeps it, as the message there promises both files.
        if staged is not None and not keep_staged:
            staged.unlink(missing_ok=True)
        if job_id:
            delete_job(project, job_id)


if __name__ == "__main__":
    raise SystemExit(main())
