# SWUM Stick Figure Animator

`swum_stick_figure.py` reads Swumsuit `body geometry.dat` / `body_geometry.dat` and `joint motion.dat` / `joint_motion.dat` files and renders the relative joint-motion animation as a 3D stick figure.

This reproduces the joint-motion style animation that can be derived from those two input files alone. It does not reproduce the solver-generated absolute swimming trajectory from `Output_data/motion.dat`.

## Requirements

- Python 3.10+
- `numpy`
- `matplotlib`

## Usage

Run from a Swumsuit project folder:

```bash
python swum_stick_figure.py --project-folder path/to/Project
```

Run from explicit files:

```bash
python swum_stick_figure.py \
  --body-geometry path/to/body_geometry.dat \
  --joint-motion path/to/joint_motion.dat
```

Save a snapshot:

```bash
python swum_stick_figure.py \
  --project-folder path/to/Project \
  --snapshot frame0.png \
  --snapshot-frame 0 \
  --no-show
```

Save an animation:

```bash
python swum_stick_figure.py \
  --project-folder path/to/Project \
  --save crawl.gif \
  --fps 12
```

Try the bundled official sample:

```bash
python swum_stick_figure.py --project-folder examples/standard_crawl
```

Useful options:

- `--normalized`: keep SWUM's height-normalized coordinates instead of meters.
- `--frame-step N`: use every `N`th frame.
- `--elev` and `--azim`: adjust the 3D camera.
- `--no-show`: render without opening a window.
