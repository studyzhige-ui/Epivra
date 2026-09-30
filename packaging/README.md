# Windows desktop release engineering

Windows x64 is the supported build target. One edition includes the restricted
Python analysis archive. OCR remains an independent optional download.
macOS build and verification are discontinued.

```powershell
python -m pip install -e ".[mcp]" build ruff mypy resvg-py pillow
python tools/build_analysis_bundle.py
python tools/build_desktop.py --output dist/desktop
```

The analysis build verifies the pinned CPython archive, compiler wheel and all
scientific wheel hashes. It builds the reviewed CPython IO correction, tests real
overlapped IO and the complete LPAC scientific/boundary workload, then creates
dist/analysis/runtime.zip and bundle.json with provenance and file hashes.
Offline inputs: --runtime-archive, --compiler-wheel, --wheelhouse, --source-cache.
Use a fresh output directory.

The desktop builder includes the archive in its credential-free runtime.
Preparation verifies and extracts it locally and performs restricted analysis
before atomically marking it ready. End users need no Docker, compiler or download
of scientific libraries.

Desktop acceptance relocates the application, removes system Python from PATH,
and checks launch, authentication, duplicate launch, parser subprocesses, Tk,
shutdown and restart, using empty data and no provider keys.

GitHub builds on windows-2022. Manual dispatch builds artifacts only by default;
explicitly selecting `publish` or pushing a matching v0.3.x tag publishes a release
marked Latest after checks. Publication verifies the archive checksum and its
clean source commit/version provenance. Artifacts remain unsigned.
Existing release assets are never overwritten: a retry skips identical uploaded
SHA-256 digests, may add missing files, and stops if existing bytes differ.

Public offline regressions and desktop acceptance tools are tracked in the
repository; see [development checks](../docs/DEVELOPMENT.md). Private evaluations
and paid-provider research-quality checks are separate from release acceptance.
