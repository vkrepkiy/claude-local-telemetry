# Automated preview rendering and delivery

Hand this to a cheap mechanical subagent (`vk-errand` on Claude, Luna on OpenAI) only after the timeline owner has named the exact project, timeline, destination, and expected format. It should run a deterministic command, verify the resulting file, and return a clickable absolute path plus a compact status. It should not inspect footage, change creative choices, overwrite the only preview, or claim user approval.

## DaVinci Resolve

Resolve must be running with the project open and Preferences → System → General → External scripting using: Local; external scripting may need DaVinci Resolve Studio. Run the script with `--dry-run` first: it connects and reports without rendering, and exits 1 with a JSON reason when Resolve or its scripting module cannot be reached. The scripting README under Resolve's `Developer/Scripting/` folder (macOS `/Library/Application Support/Blackmagic Design/DaVinci Resolve/`, Windows `%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\`, Linux `/opt/resolve/`) documents `SetCurrentRenderFormatAndCodec`, `SetRenderSettings`, `AddRenderJob`, `StartRendering(jobId)`, and `GetRenderJobStatus(jobId)`. This gives a supported route to render the current timeline of an open Resolve session; `--project` and `--timeline` only check that the open ones are the expected ones, they do not switch to them. Use [render_preview_resolve.py](../scripts/render_preview_resolve.py); pass an explicit output path and project/timeline identity. It writes a unique staged file, checks the job, H.264/AAC streams, dimensions, frame count against the timeline and full decode, then publishes the requested path and removes its render job; on a timeout it stops the render and deletes the partial file. It refuses to overwrite a previous preview without `--overwrite`.

```bash
python3 scripts/render_preview_resolve.py \
  --project PROJECT_NAME --timeline TIMELINE_NAME \
  /absolute/output/path/review_preview.mp4
```

The fast-model assignment can be: “Run this exact command against the named open Resolve project. Do not change the cut or source. Return status, duration, resolution, audio presence, and a clickable preview path; report any failure.” Return the path to the user; a local file link is delivery in this workspace, not a social upload. Before rendering, check that the requested timeline is the intended candidate version.

## Final Cut Pro

Apple documents [Export File / Share](https://support.apple.com/en-eg/guide/final-cut-pro/ver0192a47b8/mac) and configurable [share destinations](https://support.apple.com/en-euro/guide/final-cut-pro/ver9fd008a21/mac). Apple's [custom share destination API](https://developer.apple.com/documentation/professional-video-applications/receiving-media-and-data-through-a-custom-share-destination) lets a companion app receive rendered media and XML, but the documented user flow still initiates Share in Final Cut. This is not the same as a simple, tested headless command to render an arbitrary library/project. UI automation of Command-E is possible in principle but depends on window state and Accessibility permission and must be tested on the exact installation. No Final Cut render command has been validated.

If Final Cut has already exported a mezzanine master, a lightweight model can make a viewing H.264 MP4 with `ffmpeg` and validate it. That is **transcoding an existing render**, not rendering the editable FCP project. FCPXML is an interchange description and also cannot render by itself.
