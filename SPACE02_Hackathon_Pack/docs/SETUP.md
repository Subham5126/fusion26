# Setup and planned developer commands

## Current readiness

This pack contains documentation only. The following module/script names are **planned interfaces** that the bootstrap and implementation tasks must create. They have not been executed here. In the actual repo, document only commands that run; label remaining commands pending implementation.

## Environment

- Python 3.11 or 3.12 in `.venv`; Node LTS compatible with the chosen Vite version if using React.
- Backend dependencies: NumPy, OpenCV headless, SciPy, Pillow, Pydantic, FastAPI, Uvicorn and multipart support. Development: pytest and a lightweight formatter/linter.
- Optional dependencies are separate extras: Astropy and model-training tools. P0 imports cannot require them.
- Resolve dependency compatibility at setup and save lockfiles. No unverified “tested versions” claim.

## Intended Linux/macOS workflow

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e './backend[dev]'
python scripts/generate_demo.py --config configs/demo.yaml --seed 26
python scripts/analyze_sequence.py --manifest data/manifests/demo.json --config configs/pipeline.yaml
python scripts/evaluate.py --manifest data/manifests/test.json --config configs/pipeline.yaml
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Frontend in a second terminal, from `frontend/`: use `npm ci` after a real package lock exists, then `npm run dev`. Initial bootstrap resolves dependencies with `npm install` and records the lock. Frontend API defaults to local backend; use a dev proxy or explicit local-only CORS origin.

## Intended Windows PowerShell workflow

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e "./backend[dev]"
python scripts/generate_demo.py --config configs/demo.yaml --seed 26
python scripts/analyze_sequence.py --manifest data/manifests/demo.json --config configs/pipeline.yaml
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Use whichever installed Python version matches the declared project requirement. If activation is unavailable, invoke `.venv`'s Python directly. Do not change global security settings solely to activate a shell.

## Configuration

`pipeline.yaml`: profile, threshold/noise settings, candidate cap, gate distance, confirmation count, maximum consecutive misses, prediction horizon, upload/job limits and output directory. `demo.yaml`: image dimensions, frames, star model, target model, artifact/noise parameters and seed. Freeze them for evaluation.

## Offline preparation

Install and cache dependencies before travel if event rules permit. Store locally generated demo frames and results plus the instructions to regenerate them. Test with networking unavailable. Download optional datasets outside Git. Keep source provenance and licenses next to the data manifest.

## Troubleshooting

| Failure | First action |
|---|---|
| OpenCV import/UI library issue | Use headless wheel; inspect environment conflict |
| Backend import path broken | Validate editable install and app-dir; remove hard-coded absolute paths |
| UI cannot contact API | Check health route, port and proxy/CORS |
| Model weights unavailable | Use CPU detector; no silent pretend inference |
| Dataset download stalls | Continue synthetic P0; mark real-data validation pending |
| GPU unavailable | Keep GPU extras disabled |
| Track disappears | Inspect proposals and gates before changing UI |
| spotGEO results poor | Inspect acquisition mode and registration; do not lower threshold blindly |

## Release verification

After implementation, record actual environment, install command, generated-demo command, analysis command, evaluator command, API smoke result and frontend build. A missing dependency or unimplemented entry point is a known limitation, not a passing check.
