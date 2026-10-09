# Demo, pitch and judge questions

## Claim we can defend

“OrbitTrace processes telescope-style image sequences to detect orbital-object candidates, connect their observations across frames, and estimate a short image-plane trajectory. We evaluate it with labeled synthetic scenes and, if completed, separately validate localization on real telescope imagery.”

Only include real-data validation or a claimed improvement after it has actually been run.

## Three-minute demonstration

| Time | Show | Explain |
|---|---|---|
| 0:00–0:25 | Raw noisy sequence | Small sources and artifacts are hard to review manually |
| 0:25–1:00 | Run analysis; play annotated frames | Actual detections with persistent track IDs |
| 1:00–1:35 | One missed observation and evidence panel | Prediction maintains a hypothesis; hollow point was not detected |
| 1:35–2:05 | Trajectory and export | Short image-plane path, declared units and fit evidence |
| 2:05–2:35 | Baseline comparison on held-out set | Measured trade-off in recall, false tracks and runtime |
| 2:35–3:00 | Failure case and optional real sequence | Honest supported scope; future work follows observed failures |

If processing takes too long live, run one small fresh sequence and show a clearly labeled saved benchmark. Have a backup recording and local results. Do not stage artificial detections behind a fake run button.

## Suggested presentation structure

1. Problem and user: manual review of faint/noisy telescope candidates.
2. PS coverage: detection, tracking and rough trajectory.
3. Pipeline and why temporal evidence helps.
4. Actual experiments: data split, baseline and measured results.
5. Live demo plus limitations and next step.

No slide deck has been created by this planning task; this is its content outline.

## Questions to prepare

**How do you know this is debris, not an active satellite?** We do not certify identity from a short uncalibrated sequence. These are candidate orbital sources for analyst review; catalog correlation and additional calibrated observations are future work.

**Is the trajectory a real orbit?** No. It is a local image-plane estimate in a declared coordinate frame and time unit. A physical orbit requires suitable astrometry, timestamps, observer location and additional modeling.

**Why not just YOLO?** Per-frame detection is only one part of the PS. Our initial CPU pipeline emphasizes temporal association, artifact handling and explainable evidence. A trained detector is an interchangeable proposal source if we can validate it.

**What is new compared with the linked repo?** Its README centers on Blender-generated debris-body imagery and lists tracking as future work. Our contribution is telescope-sequence association and review, tested under noise and missed observations. We acknowledge established methods and claim measured engineering contributions rather than a new scientific invention. [S7]

**Are synthetic results enough?** The supplied PS allows synthetic telescope images. Synthetic truth supports reproducible tracking evaluation, but it does not prove field performance. Show real-data validation separately if completed, and state domain gaps.

**Why does spotGEO require special treatment?** Its acquisition regime, morphology and inter-frame camera rotation differ from our simple stable-star scenes. Real-data adapters need their own alignment and scoring discipline. [S2, S4]

**Does temporal confirmation remove hot pixels?** Not by itself. Persistent sensor artifacts require additional sensor/morphology evidence; show the negative artifact experiment and report remaining ambiguity.

**How fast and accurate is it?** Give the measured sample count, hardware, matching rule, latency and trade-offs. If a metric was not measured, say so.

## Submission checklist

- Correct PS ID and team identification per organizer instructions.
- Reproducible setup and actual run commands.
- Source/code/data attributions and preparation disclosure if required.
- Measured report, configs and selected demo assets.
- Backup demo recording, accessible locally.
- No external credentials, full dataset archives or unsupported achievement claims.
- Verify required portal upload formats and deadline; they were not confirmed here.
