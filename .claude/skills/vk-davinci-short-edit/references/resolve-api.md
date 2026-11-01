# Resolve scripting notes observed on macOS

These are tested behaviors from one Resolve 20 beta session, not a guarantee for every version. Inspect the installed API and check return values.

## Connection and project

- The local Python module was at `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules/DaVinciResolveScript.py`. `scriptapp('Resolve')` returned `None` until Resolve had fully launched.
- Set project timeline resolution and fps before creating/importing the timeline: `timelineResolutionWidth`, `timelineResolutionHeight`, `timelineFrameRate`. For this case they were 1080, 1920, 30. Set timeline start timecode to `00:00:00:00` and use `timeline.GetStartFrame()` as the base for `recordFrame`.
- `MediaPool.ImportMedia(paths)` returned media in an order different from `paths`. Map each returned item with `item.GetClipProperty('File Path')`; compare path sets. Do **not** zip requested paths to returned items by position.
- Numbered PNG names such as `number_1.png` through `number_3.png` can be interpreted as an image sequence. Use nonsequential names or explicitly disable sequence handling. PNG stills received a default 150-frame duration in this session, so a generated alpha MOV with controlled frame count was used for title animations; keep the PNG source for revisions.

## Timeline arithmetic and tracks

- `AppendToTimeline` with `startFrame` and `endFrame` uses a half-open source interval: duration = `endFrame - startFrame`. To append N frames, set `endFrame = startFrame + N`. An earlier `+N-1` caused one black frame at every cut. `TimelineItem.GetEnd() - GetStart()` confirmed the interval length.
- `recordFrame` is the absolute timeline frame relative to `GetStartFrame()`. Use `mediaType: 1` for video and `2` for audio, and an explicit `trackIndex`.
- `CreateEmptyTimeline` already creates V1 and A1. To make V1–V3 and A1–A4, add two video tracks and three audio tracks; assert counts afterwards.
- Validate each append, each clip's start/end, and the timeline end frame before rendering. Per-shot `ZoomX`, `ZoomY`, and `Pan` worked for reframing, but rotation metadata and Resolve transforms require visual inspection. Do not reuse one pan/zoom for an entire shoot without checking.

## Render and XML

- In this installation, `SetCurrentRenderFormatAndCodec` accepted `('mov', 'ProRes422')` and `('mp4', 'H264')`; `QuickTime` was not a format key. Enumerate `GetRenderFormats()` and `GetRenderCodecs(format)` in a new environment.
- `SetRenderSettings` accepted `AudioCodec: 'lpcm'` for PCM in MOV and `'aac'` in MP4. `LinearPCM` and a ProRes `VideoQuality: 'Best'` setting failed in this case. Assert settings, job creation, render completion, and file existence.
- Render jobs sequentially when their audio format differs. A job can inherit prior settings. Use a unique temporary output basename and replace the final file only after successful rendering; one attempt to set `ReplaceExistingFilesInPlace` failed.
- `Timeline.Export(path, EXPORT_FCPXML_1_10)` created a directory/bundle containing `Info.fcpxml`, although the target path ended in `.fcpxml`. Export to a fresh temporary path, copy/rename `Info.fcpxml` to the desired standalone file, then parse the XML. Export failed when the bundle path already existed.
- Reopen/import the `.drp` when practical, and inspect the FCPXML import in Final Cut for alpha, rotation, crops, speed-derived inserts, frame rate, source relinking, and audio. Valid XML alone does not prove a faithful Final Cut handoff.

## Catching frame-boundary failure

The first render had a one-frame black gap at every cut. A conventional blackdetect threshold of several frames missed it. Use `ffmpeg -vf blackdetect=d=0.0:pix_th=0.02:pic_th=0.98` and inspect emitted `black_start` intervals; visual review at cut frames remains useful. Do not assume a successful full-file decode excludes edit gaps.
