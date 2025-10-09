# Myring Profile Explorer

An interactive PyQt6 desktop tool for designing and analysing axisymmetric hulls that follow the
**Myring (Prestero-style) profile**. The app converts the original MATLAB workflow into a responsive
Python experience with live 2D and 3D plots, editable geometry constants, and on-the-fly hydrostatic
metrics.

<p align="center">
  <img src="resources/App_Screenshot.jpg" alt="Myring Profile Explorer UI" width="900"/>
</p>

---

## Highlights

- **Full geometry control** – edit the canonical Myring parameters (diameter, exponent, head/mid/tail
  lengths, offsets, tail angle) plus optional front/stern cut radii.
- **Real-time visualisation** – the 2D profile and 3D hull surfaces update as you type, with freeze
  and manual-apply controls for heavy edits.
- **Interactive scaling** – dedicated sliders scale the 2D and 3D axes independently for precise
  inspection without altering the core geometry.
- **Hydrostatics at a glance** – instant readouts for effective length, L/D ratio, volume, CB
  position, wetted area, Reynolds number, friction coefficient, and drag estimate.
- **Deterministic solver** – numerical code mirrors the `myring_truncated_pure.m` reference
  implementation, including optional inversion from target cut radii to offsets.

---

## Quick Start

> The project ships with a local virtual environment (`.venv`) for isolation. Refresh it if required.

```powershell
cd "D:\Office work\UL\Control\Python\gui_app"
.venv\Scripts\Activate.ps1                    # Activate the bundled venv
python -m pip install -r requirements.txt     # Install dependencies (first run)
python -m src.app.main                        # Launch the GUI
```

### Requirements

- Python **3.13** (other 3.11+ versions should also work)
- Windows PowerShell (commands above) or a shell of your choice
- No additional native dependencies – everything runs in pure Python

---

## Using the Application

| Section                        | Description                                                                 |
| ------------------------------ | --------------------------------------------------------------------------- |
| **Geometry Inputs**            | Core Myring parameters. Changing offsets or tail angle adjusts the profile.|
| **Front / Stern Radius (mm)**  | Optional cut radii. When specified, the solver back-computes the necessary offsets. Leave blank to auto-fill. |
| **Freeze / Apply Now**         | Toggle automatic updates or apply changes in batches for heavy edits.      |
| **Reset Defaults**             | Restores the canonical MATLAB-derived baseline.                            |
| **Plot Scaling**               | Axis multipliers for the 2D/3D plots. Use these to zoom without affecting the underlying numbers. |
| **Calculated Metrics**         | Live hydrostatics, offsets, and Reynolds/friction estimates.                |

Both legends are draggable; park them wherever they best suit your workflow.

---

## Project Layout

```
gui_app/
├── .venv/                   # Project-specific virtual environment
├── resources/               # Assets, screenshots, icons (add as needed)
├── src/
│   └── app/
│       ├── __init__.py
│       ├── main.py          # Application entry point
│       ├── core/            # Numerical solver (Myring calculations)
│       │   └── calculations.py
│       ├── graphics/        # Future rendering helpers
│       └── ui/
│           └── main_window.py
├── tests/                   # Pytest-based test suite (placeholder)
├── CONTRIBUTING.md          # Contribution guidelines
├── CHANGELOG.md             # Release notes
├── LICENSE                  # Project license
└── README.md                # You are here
```

---

## Development Notes

- Formatting follows standard PEP 8 conventions. `ruff` or `black` can be added if you prefer
  enforced linting – guidelines are noted in `CONTRIBUTING.md`.
- Unit tests live in `tests/`. The current placeholder verifies the package wiring; extend it with
  regression tests as you expand the solver.
- Hydrostatic calculations are encapsulated in `MyringParams`/`compute_myring_profile`. Keep UI code
  thin and delegate to this module for numerical work.
- When introducing new dependencies, update `requirements.txt` and, if the library is optional,
  document the feature it unlocks in this README.

---

## Packaging & Distribution

The project currently ships as a source app. To distribute binaries:

1. Ensure `pyproject.toml` or `setup.cfg` is added for metadata.
2. Use `pyinstaller` (already in the global environment, or add to `requirements.txt`) to create a
   single-folder or single-file executable.
3. Document any packaging steps in this README and in `CONTRIBUTING.md`.

---

## Contributing

We welcome improvements! See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the coding guideline, branch
strategy, and pull request checklist. Please open an issue before embarking on large features so we
can sync expectations.

---

## License

This project is released under the [MIT License](LICENSE). Feel free to fork, adapt, and integrate it
into your own tools with attribution.

---

## Roadmap Ideas

- Export tabulated geometry and hydrostatics to CSV.
- Batch run support for multiple parameter sets.
- Enhanced 3D visualisation (mesh slicing, texture overlays, video export).
- Test coverage for atypical input ranges and solver edge cases.

If you build one of these features, let the maintainers know – it might make the official roadmap!
