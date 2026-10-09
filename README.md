# OrbitTrace — original Fusion integration

The one working project is **E:\Fusion**, branch **Subham**. Its original .git,
datasets, experimental YOLO work and unrelated edits are preserved. The integrated
app uses existing suitability/OpenCV/registration/tracking/fitting implementations
and the latest live frontend design with neon boxes, observed paths and forecasts.

Terminal 1:
```powershell
Set-Location E:\Fusion
.\scripts\Start-Backend.ps1
```
Terminal 2:
```powershell
Set-Location E:\Fusion\frontend
..\scripts\Start-Frontend.ps1
```

Open http://127.0.0.1:5173/#/workbench ; API http://127.0.0.1:8000/docs.
Services are already running at the verification checkpoint; launch scripts refuse
occupied ports rather than creating duplicates or killing processes.

- [Setup, exact test reproduction and outputs](docs/SETUP.md)
- [Actual readiness](docs/STATUS.md)
- [Original-directory integration report](docs/handoffs/T19_ORIGINAL_INTEGRATION.md)
- [Exact changed/created file allowlist](docs/handoffs/T19_ORIGINAL_INTEGRATION_FILES.txt)
- [Review-only old-workspace audit](docs/ORIGINAL_WORKSPACE_CLEANUP.md)

Five ordered native grayscale PNG/JPEG images drive the actual API. Synthetic demo
is clearly labeled; ESA train/84 has detections without confirmed trajectories.
Candidate does not certify debris identity; image-plane tracks establish no orbit,
altitude, physical speed or collision probability. Quality is heuristic. No Git
commit/push or workspace deletion was performed. YOLO remains experimental.
