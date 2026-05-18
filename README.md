# SWUM Stick Figure Animator

`swum_stick_figure.py` reads Swumsuit `body geometry.dat` / `body_geometry.dat` and `joint motion.dat` / `joint_motion.dat` files and renders the relative joint-motion animation as a 3D stick figure.

This reproduces the joint-motion style animation that can be derived from those two input files alone. It does not reproduce the solver-generated absolute swimming trajectory from `Output_data/motion.dat`.

## Requirements

- Python 3.10+
- `numpy`
- `matplotlib`
- `scipy` for Swumsuit-compliant `joint_motion.dat` export from Misha pose data

Install the runtime dependencies in a local virtual environment:

```bash
python -m venv .venv
./.venv/Scripts/python -m pip install --upgrade pip numpy matplotlib scipy
```

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

Render the sample with purple stick-figure markers:

```bash
python swum_stick_figure.py \
  --project-folder examples/standard_crawl \
  --snapshot tmp/standard_crawl_18_points.png \
  --snapshot-frame 0 \
  --no-show
```

Useful options:

- `--normalized`: keep SWUM's height-normalized coordinates instead of meters.
- `--frame-step N`: use every `N`th frame.
- `--elev` and `--azim`: adjust the 3D camera.
- `--point-size N`: adjust the purple marker size.
- `--no-show`: render without opening a window.

## Purple markers

The renderer paints a fixed set of purple markers on the stick figure. The current set is configured in `swum_stick_figure.py` as `MARKER_POINTS`.

The marker set includes one mid-back point and the arm endpoints. It intentionally does not mark every SWUM segment root/tip, because that creates too many points for comparison with 3D pose data.

## Misha frame export

`extract_misha_18_points.py` converts one frame from a Misha `data.npy` file into a simple 18-point coordinate `.dat` file.

The default input is:

```text
asaf-reaserch/Data/Misha_7/data.npy
```

The Misha source has 21 joints. The extractor removes:

- `pelvis`
- `left finger`
- `right finger`

That leaves 18 coordinate points for a single frame.

Export frame 60 as a custom coordinate `.dat`:

```bash
python extract_misha_18_points.py \
  --frame 60 \
  --output tmp/misha_7_frame60_18_points.dat
```

Export frame 60 after pelvis-centering and rotating the body so pelvis-to-head is `+Z`:

```bash
python extract_misha_18_points.py \
  --frame 60 \
  --align-body-to-z \
  --output tmp/misha_7_frame60_18_points_aligned.dat
```

Export frame 60 as a Swumsuit-compliant `joint_motion.dat`:

```bash
python extract_misha_18_points.py \
  --format swumsuit-joint-motion \
  --frame 60 \
  --output tmp/misha_7_frame60_joint_motion.dat
```

For a single requested Misha frame, the exporter writes a one-frame `joint_motion.dat`: the file starts with `1`, every rotation block contains one angle value, and the file ends with `0 0`. Missing joints from the 18-point representation are reconstructed as follows:

- `pelvis`: midpoint of `left hip` and `right hip`
- `left finger`: copied from `left wrist`
- `right finger`: copied from `right wrist`

The output format is a coordinate `.dat` file with one frame and 18 rows:

```text
# misha_18_points_dat_v1
# columns marker_index source_joint_index joint_name x y z
1
18
00 01 spine_t12 ...
```

The coordinate `.dat` format is not a Swumsuit `joint_motion.dat` file. Use `--format swumsuit-joint-motion` when the output must be opened by Swumsuit.
