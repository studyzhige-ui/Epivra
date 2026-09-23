# Desktop release engineering

The base app is one edition. OCR and Docker analysis are independent optional
components configured by the user. There are two native artifacts, not four
parallel product editions.

Run on Windows x64 or macOS 14+ Apple Silicon, using Python 3.12+:

```
python -m pip install -e ".[mcp]" build ruff mypy resvg-py pillow
python tools/build_desktop.py --output dist/desktop
```

The build fetches a fixed python-build-standalone CPython 3.12.13 archive and
checks its upstream SHA-256 before extraction. Runtime URLs and digests are in
the build script. A build-only `--runtime-archive` argument accepts an already
downloaded archive with the same required digest. No Python from the build
machine is copied into the product.

The wheel and all base dependencies are installed inside that relocatable
runtime. Package metadata and licenses stay bundled; THIRD-PARTY-PACKAGES.json
records exact installed versions. The app icon is rendered from the repository
SVG. Windows uses a .NET Framework launcher compiled for x64; macOS uses a
native arm64 launcher inside an application bundle. Sandbox build resources are
copied explicitly. No source workspace, .env or research state is packaged.

The mandatory smoke check copies the built application to another directory,
removes system Python from PATH, launches the native entry point in an empty
workspace, and checks Web assets/authentication, duplicate launch, a real parser
subprocess, Tk, shutdown and restart. All provider credentials are excluded.

The GitHub Desktop release workflow runs native regression and bundle checks
on windows-2022 and macos-14 arm64. Manual dispatch builds artifacts only. A
matching v0.3.x tag publishes a **prerelease**, only after both jobs pass.

Current artifacts are unsigned (macOS runtime binaries have only ad-hoc
integrity signatures). No Developer ID trust or notarization is claimed.
For a trusted general release, provision real Windows publisher and Apple
Developer ID credentials, sign the full payload on the matching runner,
notarize and staple the macOS bundle, and validate the downloaded quarantined
artifact on clean machines. Never simulate this by removing quarantine or
disabling Gatekeeper/SmartScreen.

Release acceptance does not include the deferred semantic quality of research
reports. Optional component download/installation and actual Docker workloads
must be reported independently of the base application smoke check.
