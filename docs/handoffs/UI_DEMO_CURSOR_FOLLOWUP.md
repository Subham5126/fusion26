# T19 UI follow-up: demo mode and cursor

2026-10-10. Root E:\Fusion; branch Subham; base 1bad730757f2183985595d6ecee911c1179925e9. User explicitly requested restoring one synthetic demo under Detection mode, superseding the earlier removal of public demo entry points for this specific workflow.

Changed implementation files:
- frontend/src/components/workbench/LocalWorkbench.tsx
- frontend/src/components/layout/AppNavigation.tsx
- frontend/src/pages/LandingPage.tsx
- frontend/src/components/ui/CustomCursor.tsx
- frontend/src/styles/interactions.css

Also created this handoff and updated FINAL_RELEASE_ALLOWLIST.txt. Earlier release changes remain uncommitted and are preserved.

Detection mode now offers Synthetic demo, starting the existing POST /api/analyze/demo workflow on selection. It reuses job polling and DemoWorkbench native backend frame loading/ScientificOverlay. It is explicitly labeled synthetic, does not upload local files, and keeps confirmed local files available when switching back. Mode switching clears mismatched result state. Busy jobs disable selection and offer Stop monitoring; completed/failed/cancelled demo runs can be retried. No backend contract, detector, tracking source or dependencies changed. The existing demo uses five 64x48 frames; it is not presented as real ESA data.

Removed redundant header and closing launch CTAs; one hero Launch Workbench button remains, alongside the ordinary Mission Workbench navigation link.

Removed the second cursor dot and its independent hover scale, which could scale the translation and displace the dot. One ring now follows viewport pointer coordinates directly without positional lag or click scaling. Hover styling remains; native cursor, image inspection suppression and reduced-motion/coarse-pointer handling remain.

Actual checks: node tests/run-data-tests.mjs: 123 passed; node tests/overlay.test.mjs: 19 passed; npm run build: TypeScript and Vite passed, existing >500 kB landing chunk warning. Backend unchanged, so the full Python suite was not rerun in this follow-up.

Actual browser: selecting demo automatically completed a backend job with five detections, one confirmed track and two predictions. First frame showed one observed point; final frame showed five genuine observations plus distinct forecasts. Switching to Standard preserved the previously selected five local frames and enabled Analyze local images. Home DOM contains exactly one Launch Workbench CTA and zero custom-cursor-dot elements. Ring center [953,37] matches its pointer translation [953,37]. Console warning/error collection was empty. Evidence: .cache/final-release/demo-mode-followup.png and home-ui-followup.png. Generated screenshots are not publication files.

Reproduce: open http://127.0.0.1:5173/#/workbench and select Detection mode > Synthetic demo. No files required. Inspect final frame & forecasts, then select Standard to return to uploaded-image mode.

No commit, push or deployment. No model accuracy or registration changes claimed. Existing FINAL_ORBITTRACE_RELEASE limitations continue to apply.
