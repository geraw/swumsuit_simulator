from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np


DEFAULT_DATA_PATH = Path("asaf-reaserch/Data/Misha_7/data.npy")
DEFAULT_OUTPUT_PATH = Path("tmp/misha_7_frame60_18_points.dat")
DEFAULT_JOINT_MOTION_OUTPUT_PATH = Path("tmp/misha_7_frame60_joint_motion.dat")
DEFAULT_TEMPLATE_PATH = Path("examples/standard_crawl/joint_motion.dat")
DEFAULT_REMOVED_JOINTS = ("pelvis", "left finger", "right finger")
SWUM_NUMSP = 18


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract one 18-point pose frame from Misha data.npy and write it as "
            "a simple coordinate .dat file."
        )
    )
    parser.add_argument(
        "--data-path",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="Path to a data.npy dict with pose_3d, joint_names, and fps.",
    )
    parser.add_argument(
        "--frame",
        type=int,
        default=60,
        help="Zero-based frame index to export.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Destination .dat path.",
    )
    parser.add_argument(
        "--format",
        choices=("points", "swumsuit-joint-motion"),
        default="points",
        help=(
            "'points' writes a custom 18-point coordinate .dat. "
            "'swumsuit-joint-motion' writes a Swumsuit-compliant joint_motion.dat."
        ),
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=DEFAULT_TEMPLATE_PATH,
        help="Swumsuit joint_motion.dat template used for block order and template-only blocks.",
    )
    parser.add_argument(
        "--remove-joint",
        action="append",
        default=None,
        help=(
            "Joint name to remove. May be repeated. Defaults to pelvis, "
            "left finger, and right finger."
        ),
    )
    parser.add_argument(
        "--align-body-to-z",
        action="store_true",
        help="Pelvis-center and rotate the full 21-point pose so pelvis-to-head is +Z before extraction.",
    )
    return parser.parse_args()


def load_misha_data(path: Path) -> tuple[np.ndarray, list[str], float | None]:
    blob = np.load(path, allow_pickle=True)
    if not isinstance(blob, np.ndarray) or blob.ndim != 0:
        raise ValueError(f"{path} must contain a NumPy object dict.")

    data = blob.item()
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a dict.")

    pose = np.asarray(data["pose_3d"], dtype=np.float64)
    if pose.ndim != 3 or pose.shape[1:] != (21, 3):
        raise ValueError(f"pose_3d must have shape (frames, 21, 3); got {pose.shape}.")

    joint_names = list(data.get("joint_names", [f"joint_{index}" for index in range(21)]))
    if len(joint_names) != 21:
        raise ValueError(f"Expected 21 joint names; got {len(joint_names)}.")

    fps_value = data.get("fps")
    fps = float(fps_value) if fps_value is not None else None
    return pose, joint_names, fps


def rotation_between(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    src = np.asarray(src, dtype=np.float64).reshape(3)
    dst = np.asarray(dst, dtype=np.float64).reshape(3)
    src = src / (np.linalg.norm(src) + 1e-12)
    dst = dst / (np.linalg.norm(dst) + 1e-12)

    cos_angle = float(np.clip(np.dot(src, dst), -1.0, 1.0))
    if cos_angle > 0.9999:
        return np.eye(3)
    if cos_angle < -0.9999:
        return np.diag([1.0, -1.0, -1.0])

    axis = np.cross(src, dst)
    axis = axis / (np.linalg.norm(axis) + 1e-12)
    theta = float(np.arccos(cos_angle))
    x, y, z = axis
    skew = np.array(
        [
            [0.0, -z, y],
            [z, 0.0, -x],
            [-y, x, 0.0],
        ],
        dtype=np.float64,
    )
    return np.eye(3) + np.sin(theta) * skew + (1.0 - np.cos(theta)) * (skew @ skew)


def align_frame_body_to_z(frame: np.ndarray, pelvis_index: int, head_index: int) -> np.ndarray:
    pelvis = frame[pelvis_index]
    body_axis = frame[head_index] - pelvis
    if np.linalg.norm(body_axis) < 1e-8:
        return frame - pelvis

    rotation = rotation_between(body_axis, np.array([0.0, 0.0, 1.0], dtype=np.float64))
    return (rotation @ (frame - pelvis).T).T


def removed_indices(joint_names: Sequence[str], remove_joint_names: Sequence[str]) -> list[int]:
    name_to_index = {name: index for index, name in enumerate(joint_names)}
    missing = [name for name in remove_joint_names if name not in name_to_index]
    if missing:
        raise ValueError(f"Unknown joint name(s): {', '.join(missing)}")
    return sorted(name_to_index[name] for name in remove_joint_names)


def extract_frame_18_points(
    pose: np.ndarray,
    joint_names: Sequence[str],
    frame_index: int,
    remove_joint_names: Sequence[str],
    align_body_to_z: bool,
) -> tuple[np.ndarray, list[str], list[int]]:
    if frame_index < 0 or frame_index >= pose.shape[0]:
        raise IndexError(f"Frame {frame_index} is outside valid range 0..{pose.shape[0] - 1}.")

    frame = np.array(pose[frame_index], dtype=np.float64, copy=True)
    if align_body_to_z:
        frame = align_frame_body_to_z(
            frame,
            pelvis_index=joint_names.index("pelvis"),
            head_index=joint_names.index("head"),
        )

    remove_indices = set(removed_indices(joint_names, remove_joint_names))
    keep_indices = [index for index in range(len(joint_names)) if index not in remove_indices]
    points = frame[keep_indices]
    names = [joint_names[index] for index in keep_indices]

    if points.shape != (18, 3):
        raise ValueError(f"Expected 18 extracted points; got {points.shape[0]}.")
    return points, names, keep_indices


def reconstruct_21_from_18(
    points: np.ndarray,
    names: Sequence[str],
    joint_names: Sequence[str],
) -> np.ndarray:
    name_to_point = {name: points[index] for index, name in enumerate(names)}
    reconstructed = np.zeros((21, 3), dtype=np.float64)

    for index, name in enumerate(joint_names):
        if name in name_to_point:
            reconstructed[index] = name_to_point[name]
        elif name == "pelvis":
            reconstructed[index] = (
                name_to_point["left hip"] + name_to_point["right hip"]
            ) / 2.0
        elif name == "left finger":
            reconstructed[index] = name_to_point["left wrist"]
        elif name == "right finger":
            reconstructed[index] = name_to_point["right wrist"]
        else:
            raise ValueError(f"Cannot reconstruct missing joint: {name}")

    return reconstructed


def write_swumsuit_joint_motion_dat(
    output_path: Path,
    frame21: np.ndarray,
    template_path: Path,
) -> None:
    import sys

    data_to_swumsuit = Path("asaf-reaserch/DataToSwumsuit").resolve()
    if not data_to_swumsuit.exists():
        raise FileNotFoundError(
            "Missing asaf-reaserch/DataToSwumsuit. Clone Belilus/asaf-reaserch first."
        )
    sys.path.insert(0, str(data_to_swumsuit))

    from swum_pipeline.core.alignment import align_body_to_z
    from swum_pipeline.io.template import NUMSP, parse_template
    from swum_pipeline.pipeline.phase2_blocks import compute_all_blocks

    if NUMSP != SWUM_NUMSP:
        raise ValueError(f"Expected Swumsuit NUMSP={SWUM_NUMSP}; got {NUMSP}.")

    # The upstream kinematic helper expects the standard 18-frame cycle shape,
    # so repeat the source pose for computation and then serialize one sample.
    pose_cycle = np.repeat(frame21[np.newaxis, :, :], NUMSP, axis=0)
    pose_aligned = align_body_to_z(pose_cycle)

    template_blocks = parse_template(template_path, numsp=NUMSP)
    if not template_blocks:
        raise ValueError(f"No rotation blocks found in template: {template_path}")
    output_blocks = compute_all_blocks(
        pose_aligned,
        template_blocks,
        numsp=NUMSP,
        trunk_pitch_mode="scale",
        arms_mode="template",
    )

    lines = [" 1\n"]
    for block in output_blocks:
        lines.append(f" {block.segm} {block.axis}\n")
        lines.append(f" {float(block.values[0]):.4f}\n")
    lines.append("0 0\n")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(lines), encoding="utf-8")


def write_points_dat(
    output_path: Path,
    points: np.ndarray,
    names: Sequence[str],
    source_indices: Sequence[int],
    *,
    data_path: Path,
    frame_index: int,
    fps: float | None,
    removed: Sequence[str],
    aligned: bool,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# misha_18_points_dat_v1\n",
        f"# source {data_path.as_posix()}\n",
        f"# frame_index {frame_index}\n",
        f"# fps {fps if fps is not None else 'unknown'}\n",
        f"# aligned_body_to_z {int(aligned)}\n",
        f"# removed_joints {','.join(name.replace(' ', '_') for name in removed)}\n",
        "# columns marker_index source_joint_index joint_name x y z\n",
        "1\n",
        f"{len(points)}\n",
    ]

    for marker_index, (source_index, name, point) in enumerate(zip(source_indices, names, points)):
        safe_name = name.replace(" ", "_")
        lines.append(
            f"{marker_index:02d} {source_index:02d} {safe_name} "
            f"{point[0]:.9f} {point[1]:.9f} {point[2]:.9f}\n"
        )

    output_path.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    remove_joint_names = tuple(args.remove_joint) if args.remove_joint else DEFAULT_REMOVED_JOINTS
    if args.format == "swumsuit-joint-motion" and args.output == DEFAULT_OUTPUT_PATH:
        args.output = DEFAULT_JOINT_MOTION_OUTPUT_PATH

    pose, joint_names, fps = load_misha_data(args.data_path)
    points, names, source_indices = extract_frame_18_points(
        pose=pose,
        joint_names=joint_names,
        frame_index=args.frame,
        remove_joint_names=remove_joint_names,
        align_body_to_z=args.align_body_to_z,
    )
    if args.format == "swumsuit-joint-motion":
        frame21 = reconstruct_21_from_18(points, names, joint_names)
        write_swumsuit_joint_motion_dat(args.output, frame21, args.template)
        print(f"Wrote Swumsuit joint_motion.dat from frame {args.frame} to {args.output}")
    else:
        write_points_dat(
            args.output,
            points,
            names,
            source_indices,
            data_path=args.data_path,
            frame_index=args.frame,
            fps=fps,
            removed=remove_joint_names,
            aligned=args.align_body_to_z,
        )
        print(f"Wrote {len(points)} points from frame {args.frame} to {args.output}")


if __name__ == "__main__":
    main()
