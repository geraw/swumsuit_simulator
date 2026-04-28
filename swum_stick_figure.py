from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


SEGMENT_NAMES = [
    "",
    "lower_waist",
    "upper_waist",
    "lower_breast",
    "upper_breast",
    "shoulder",
    "neck",
    "head",
    "upper_hip",
    "lower_hip",
    "right_thigh",
    "left_thigh",
    "right_shank",
    "left_shank",
    "right_foot",
    "left_foot",
    "right_upper_arm",
    "left_upper_arm",
    "right_forearm",
    "left_forearm",
    "right_hand",
    "left_hand",
]

CONNECTORS = [
    ("tip", 6, "root", 7),
    ("tip", 4, "root", 16),
    ("tip", 4, "root", 17),
    ("tip", 9, "root", 10),
    ("tip", 9, "root", 11),
    ("tip", 12, "root", 14),
    ("tip", 13, "root", 15),
]


@dataclass(frozen=True)
class SegmentGeometry:
    root_depth: float
    root_width: float
    tip_depth: float
    tip_width: float
    length: float
    density: float


@dataclass(frozen=True)
class BodyGeometry:
    segments: list[SegmentGeometry]
    misc: list[float]

    @property
    def actual_height(self) -> float:
        return self.misc[7]

    @property
    def shoulder_root_y(self) -> float:
        return self.misc[0]

    @property
    def shoulder_root_z(self) -> float:
        return self.misc[1]

    @property
    def head_root_x(self) -> float:
        return self.misc[2]

    @property
    def hip_joint_y(self) -> float:
        return self.misc[3]

    @property
    def hip_joint_z(self) -> float:
        return self.misc[4]

    @property
    def foot_joint_z(self) -> float:
        return self.misc[5]

    @property
    def hip_split_angle(self) -> float:
        return self.misc[6]


@dataclass(frozen=True)
class RotationTrack:
    segment_no: int
    axis_no: int
    angles_deg: list[float]


@dataclass(frozen=True)
class JointMotion:
    num_frames: int
    tracks: list[RotationTrack]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render a SWUM/Swumsuit joint-motion animation as a 3D stick figure."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--project-folder",
        type=Path,
        help="Folder that contains body_geometry.dat and joint_motion.dat.",
    )
    source.add_argument(
        "--body-geometry",
        type=Path,
        help="Path to body_geometry.dat.",
    )
    parser.add_argument(
        "--joint-motion",
        type=Path,
        help="Path to joint_motion.dat. Required with --body-geometry.",
    )
    parser.add_argument(
        "--save",
        type=Path,
        help="Optional output animation path (.gif or .mp4).",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Optional snapshot path (.png) for one frame.",
    )
    parser.add_argument(
        "--snapshot-frame",
        type=int,
        default=0,
        help="Zero-based frame index used by --snapshot.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=12,
        help="Playback and export frame rate.",
    )
    parser.add_argument(
        "--frame-step",
        type=int,
        default=1,
        help="Use every Nth frame from joint_motion.dat.",
    )
    parser.add_argument(
        "--normalized",
        action="store_true",
        help="Keep SWUM's height-normalized coordinates instead of meters.",
    )
    parser.add_argument(
        "--elev",
        type=float,
        default=20.0,
        help="Matplotlib camera elevation angle.",
    )
    parser.add_argument(
        "--azim",
        type=float,
        default=-65.0,
        help="Matplotlib camera azimuth angle.",
    )
    parser.add_argument(
        "--line-width",
        type=float,
        default=2.5,
        help="Stick figure line width.",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Do not open an interactive window.",
    )
    return parser.parse_args()


def first_existing_path(candidates: Sequence[Path]) -> Path | None:
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def resolve_input_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.project_folder is not None:
        body_path = first_existing_path(
            [
                args.project_folder / "body_geometry.dat",
                args.project_folder / "body geometry.dat",
            ]
        )
        motion_path = first_existing_path(
            [
                args.project_folder / "joint_motion.dat",
                args.project_folder / "joint motion.dat",
            ]
        )
    else:
        if args.joint_motion is None:
            raise SystemExit("--joint-motion is required with --body-geometry.")
        body_path = args.body_geometry
        motion_path = args.joint_motion

    if body_path is None:
        raise SystemExit("Missing body geometry file in the project folder.")
    if motion_path is None:
        raise SystemExit("Missing joint motion file in the project folder.")

    if not body_path.is_file():
        raise SystemExit(f"Missing body geometry file: {body_path}")
    if not motion_path.is_file():
        raise SystemExit(f"Missing joint motion file: {motion_path}")
    return body_path, motion_path


def non_empty_lines(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def parse_body_geometry(path: Path) -> BodyGeometry:
    lines = non_empty_lines(path)
    if len(lines) < 30:
        raise ValueError(
            f"{path} has {len(lines)} non-empty lines, but SWUM body geometry needs 30."
        )

    segments: list[SegmentGeometry] = []
    for index in range(21):
        parts = [float(token) for token in lines[index].split()]
        if len(parts) != 6:
            raise ValueError(
                f"Segment line {index + 1} in {path} must contain 6 floats."
            )
        segments.append(SegmentGeometry(*parts))

    misc = [float(lines[21 + index].split()[0]) for index in range(9)]
    return BodyGeometry(segments=segments, misc=misc)


def parse_joint_motion(path: Path) -> JointMotion:
    lines = non_empty_lines(path)
    if not lines:
        raise ValueError(f"{path} is empty.")

    num_frames = int(float(lines[0]))
    cursor = 1
    tracks: list[RotationTrack] = []

    while cursor < len(lines):
        tokens = lines[cursor].split()
        cursor += 1
        if len(tokens) < 2:
            raise ValueError(f"Invalid rotation header near line {cursor} in {path}.")

        segment_no = int(float(tokens[0]))
        axis_no = int(float(tokens[1]))
        if segment_no == 0 and axis_no == 0:
            break

        if not 1 <= segment_no <= 21:
            raise ValueError(f"Invalid segment number {segment_no} in {path}.")
        if not 1 <= axis_no <= 9:
            raise ValueError(f"Invalid axis number {axis_no} in {path}.")

        if cursor + num_frames > len(lines):
            raise ValueError(f"Rotation block for segment {segment_no} is truncated.")

        angles_deg = [float(lines[cursor + offset]) for offset in range(num_frames)]
        cursor += num_frames
        tracks.append(RotationTrack(segment_no=segment_no, axis_no=axis_no, angles_deg=angles_deg))

    return JointMotion(num_frames=num_frames, tracks=tracks)


def vec(x: float, y: float, z: float) -> np.ndarray:
    return np.array([x, y, z], dtype=float)


def rotate_xyz(vector: np.ndarray, rx: float = 0.0, ry: float = 0.0, rz: float = 0.0) -> np.ndarray:
    x, y, z = vector

    x1 = x
    y1 = y * math.cos(rx) - z * math.sin(rx)
    z1 = y * math.sin(rx) + z * math.cos(rx)

    x2 = x1 * math.cos(ry) + z1 * math.sin(ry)
    y2 = y1
    z2 = -x1 * math.sin(ry) + z1 * math.cos(ry)

    x3 = x2 * math.cos(rz) - y2 * math.sin(rz)
    y3 = x2 * math.sin(rz) + y2 * math.cos(rz)
    z3 = z2
    return vec(x3, y3, z3)


def rotate_about_axis(vector: np.ndarray, axis_no: int, theta: float) -> np.ndarray:
    axis = ((axis_no - 1) % 3) + 1
    if axis == 1:
        return rotate_xyz(vector, rx=theta)
    if axis == 2:
        return rotate_xyz(vector, ry=theta)
    return rotate_xyz(vector, rz=theta)


def compute_frame(body: BodyGeometry, motion: JointMotion, frame_index: int, scale: float) -> tuple[np.ndarray, np.ndarray]:
    lengths = [0.0] + [segment.length * scale for segment in body.segments]

    e1 = [vec(0.0, 0.0, 0.0)] + [vec(1.0, 0.0, 0.0) for _ in range(21)]
    e2 = [vec(0.0, 0.0, 0.0)] + [vec(0.0, 1.0, 0.0) for _ in range(21)]
    e3 = [vec(0.0, 0.0, 0.0)] + [vec(0.0, 0.0, 1.0) for _ in range(21)]

    upper_breast_tip_width = body.segments[3].tip_width * scale
    xs2ra = vec(0.0, -upper_breast_tip_width, -body.shoulder_root_z * scale)
    xs2la = vec(0.0, upper_breast_tip_width, -body.shoulder_root_z * scale)
    xnb2ha = vec(body.head_root_x * scale, 0.0, 0.0)
    xh2rl = vec(0.0, -body.hip_joint_y * scale, -body.hip_joint_z * scale)
    xh2ll = vec(0.0, body.hip_joint_y * scale, -body.hip_joint_z * scale)
    xtj2tra = vec(0.0, 0.0, body.hip_joint_z * scale)
    xtj2tla = vec(0.0, 0.0, body.hip_joint_z * scale)
    xsh2rf = vec(0.0, 0.0, body.foot_joint_z * scale)
    xsh2lf = vec(0.0, 0.0, body.foot_joint_z * scale)
    xfj2ra = vec(0.0, 0.0, -body.foot_joint_z * scale)
    xfj2la = vec(0.0, 0.0, -body.foot_joint_z * scale)
    xuaj2ra = vec(0.0, -body.shoulder_root_y * scale, -body.shoulder_root_z * scale)
    xuaj2la = vec(0.0, body.shoulder_root_y * scale, -body.shoulder_root_z * scale)

    for segment_no in range(8, 16):
        theta = math.pi
        if segment_no == 8:
            theta = math.pi + body.hip_split_angle
        elif segment_no == 9:
            theta = math.pi - body.hip_split_angle
            xh2rl = rotate_about_axis(xh2rl, 2, theta)
            xh2ll = rotate_about_axis(xh2ll, 2, theta)
        elif segment_no == 10:
            xtj2tra = rotate_about_axis(xtj2tra, 2, theta)
        elif segment_no == 11:
            xtj2tla = rotate_about_axis(xtj2tla, 2, theta)
        elif segment_no == 12:
            xsh2rf = rotate_about_axis(xsh2rf, 2, theta)
        elif segment_no == 13:
            xsh2lf = rotate_about_axis(xsh2lf, 2, theta)
        elif segment_no == 14:
            xfj2ra = rotate_about_axis(xfj2ra, 2, theta)
        elif segment_no == 15:
            xfj2la = rotate_about_axis(xfj2la, 2, theta)

        e1[segment_no] = rotate_about_axis(e1[segment_no], 2, theta)
        e2[segment_no] = rotate_about_axis(e2[segment_no], 2, theta)
        e3[segment_no] = rotate_about_axis(e3[segment_no], 2, theta)

    for track in motion.tracks:
        theta = math.radians(track.angles_deg[frame_index])
        segment_no = track.segment_no
        axis_no = track.axis_no

        if axis_no <= 3:
            e1[segment_no] = rotate_about_axis(e1[segment_no], axis_no, theta)
            e2[segment_no] = rotate_about_axis(e2[segment_no], axis_no, theta)
            e3[segment_no] = rotate_about_axis(e3[segment_no], axis_no, theta)

        if segment_no == 4:
            if axis_no <= 3:
                xs2ra = rotate_about_axis(xs2ra, axis_no, theta)
                xs2la = rotate_about_axis(xs2la, axis_no, theta)
            elif 4 <= axis_no <= 6:
                xs2ra = rotate_about_axis(xs2ra, axis_no, theta)
            elif 7 <= axis_no <= 9:
                xs2la = rotate_about_axis(xs2la, axis_no, theta)
        elif segment_no == 7:
            xnb2ha = rotate_about_axis(xnb2ha, axis_no, theta)
        elif segment_no == 9:
            xh2rl = rotate_about_axis(xh2rl, axis_no, theta)
            xh2ll = rotate_about_axis(xh2ll, axis_no, theta)
        elif segment_no == 10:
            xtj2tra = rotate_about_axis(xtj2tra, axis_no, theta)
        elif segment_no == 11:
            xtj2tla = rotate_about_axis(xtj2tla, axis_no, theta)
        elif segment_no == 12:
            xsh2rf = rotate_about_axis(xsh2rf, axis_no, theta)
        elif segment_no == 13:
            xsh2lf = rotate_about_axis(xsh2lf, axis_no, theta)
        elif segment_no == 14:
            xfj2ra = rotate_about_axis(xfj2ra, axis_no, theta)
        elif segment_no == 15:
            xfj2la = rotate_about_axis(xfj2la, axis_no, theta)
        elif segment_no == 16:
            xuaj2ra = rotate_about_axis(xuaj2ra, axis_no, theta)
        elif segment_no == 17:
            xuaj2la = rotate_about_axis(xuaj2la, axis_no, theta)

    roots = np.zeros((22, 3), dtype=float)
    tips = np.zeros((22, 3), dtype=float)

    roots[1] = vec(0.0, 0.0, 0.0)
    tips[1] = roots[1] + lengths[1] * e3[1]

    for segment_no in (2, 3, 4, 5, 6):
        roots[segment_no] = tips[segment_no - 1]
        tips[segment_no] = roots[segment_no] + lengths[segment_no] * e3[segment_no]

    roots[7] = tips[6] + xnb2ha
    tips[7] = roots[7] + lengths[7] * e3[7]

    roots[8] = roots[1]
    tips[8] = roots[8] + lengths[8] * e3[8]

    roots[9] = tips[8]
    tips[9] = roots[9] + lengths[9] * e3[9]

    roots[10] = tips[9] + xh2rl + xtj2tra
    tips[10] = roots[10] + lengths[10] * e3[10]

    roots[11] = tips[9] + xh2ll + xtj2tla
    tips[11] = roots[11] + lengths[11] * e3[11]

    roots[12] = tips[10]
    tips[12] = roots[12] + lengths[12] * e3[12]

    roots[13] = tips[11]
    tips[13] = roots[13] + lengths[13] * e3[13]

    roots[14] = tips[12] + xfj2ra + xsh2rf
    tips[14] = roots[14] + lengths[14] * e3[14]

    roots[15] = tips[13] + xfj2la + xsh2lf
    tips[15] = roots[15] + lengths[15] * e3[15]

    roots[16] = tips[4] + xs2ra + xuaj2ra
    tips[16] = roots[16] + lengths[16] * e3[16]

    roots[17] = tips[4] + xs2la + xuaj2la
    tips[17] = roots[17] + lengths[17] * e3[17]

    roots[18] = tips[16]
    tips[18] = roots[18] + lengths[18] * e3[18]

    roots[19] = tips[17]
    tips[19] = roots[19] + lengths[19] * e3[19]

    roots[20] = tips[18]
    tips[20] = roots[20] + lengths[20] * e3[20]

    roots[21] = tips[19]
    tips[21] = roots[21] + lengths[21] * e3[21]
    return roots, tips


def build_frames(body: BodyGeometry, motion: JointMotion, frame_step: int, normalized: bool) -> tuple[list[tuple[np.ndarray, np.ndarray]], list[int]]:
    if frame_step <= 0:
        raise ValueError("--frame-step must be positive.")

    scale = 1.0
    if not normalized and body.actual_height > 0.0:
        scale = body.actual_height

    frame_indices = list(range(0, motion.num_frames, frame_step))
    frames = [compute_frame(body, motion, index, scale) for index in frame_indices]
    return frames, frame_indices


def frame_lines(roots: np.ndarray, tips: np.ndarray) -> list[np.ndarray]:
    lines = [np.vstack((roots[segment_no], tips[segment_no])) for segment_no in range(1, 22)]
    for start_kind, start_segment, end_kind, end_segment in CONNECTORS:
        start_point = roots[start_segment] if start_kind == "root" else tips[start_segment]
        end_point = roots[end_segment] if end_kind == "root" else tips[end_segment]
        lines.append(np.vstack((start_point, end_point)))
    return lines


def bounds_for_frames(frames: Sequence[tuple[np.ndarray, np.ndarray]]) -> tuple[np.ndarray, float]:
    all_points = []
    for roots, tips in frames:
        all_points.append(roots[1:])
        all_points.append(tips[1:])
    points = np.concatenate(all_points, axis=0)
    minimum = points.min(axis=0)
    maximum = points.max(axis=0)
    center = (minimum + maximum) / 2.0
    radius = max((maximum - minimum).max() * 0.6, 0.2)
    return center, radius


def import_matplotlib(no_show: bool):
    import matplotlib

    if no_show:
        matplotlib.use("Agg")

    import matplotlib.pyplot as plt
    from matplotlib import animation

    return plt, animation


def save_animation(anim, animation_module, output_path: Path, fps: int) -> None:
    suffix = output_path.suffix.lower()
    if suffix == ".gif":
        writer = animation_module.PillowWriter(fps=fps)
    elif suffix == ".mp4":
        writer = animation_module.FFMpegWriter(fps=fps)
    else:
        raise ValueError("Animation output must end with .gif or .mp4")
    anim.save(output_path, writer=writer)


def plot_animation(
    frames: Sequence[tuple[np.ndarray, np.ndarray]],
    frame_indices: Sequence[int],
    motion: JointMotion,
    args: argparse.Namespace,
) -> None:
    if not frames:
        raise ValueError("No frames were generated.")

    plt, animation = import_matplotlib(args.no_show)

    figure = plt.figure(figsize=(8, 8))
    axis = figure.add_subplot(111, projection="3d")
    axis.set_facecolor("#d8eef8")
    figure.patch.set_facecolor("white")

    center, radius = bounds_for_frames(frames)
    axis.set_xlim(center[0] - radius, center[0] + radius)
    axis.set_ylim(center[1] - radius, center[1] + radius)
    axis.set_zlim(center[2] - radius, center[2] + radius)
    if hasattr(axis, "set_box_aspect"):
        axis.set_box_aspect((1, 1, 1))
    axis.set_xlabel("x")
    axis.set_ylabel("y")
    axis.set_zlabel("z")
    axis.view_init(elev=args.elev, azim=args.azim)
    axis.grid(False)

    first_lines = frame_lines(*frames[0])
    artists = []
    for index, line in enumerate(first_lines):
        color = "#d99a00" if index < 21 else "#5a5a5a"
        width = args.line_width if index < 21 else max(args.line_width * 0.7, 1.0)
        (artist,) = axis.plot(
            line[:, 0],
            line[:, 1],
            line[:, 2],
            color=color,
            linewidth=width,
            solid_capstyle="round",
        )
        artists.append(artist)

    title = axis.set_title("")

    def update(frame_position: int) -> Iterable[object]:
        lines = frame_lines(*frames[frame_position])
        for artist, line in zip(artists, lines):
            artist.set_data(line[:, 0], line[:, 1])
            artist.set_3d_properties(line[:, 2])

        source_frame = frame_indices[frame_position] + 1
        title.set_text(f"SWUM joint motion frame {source_frame}/{motion.num_frames}")
        return [*artists, title]

    update(0)

    if args.snapshot is not None:
        snapshot_index = max(0, min(args.snapshot_frame, len(frames) - 1))
        update(snapshot_index)
        figure.savefig(args.snapshot, dpi=180, bbox_inches="tight")

    anim = None
    needs_animation = args.save is not None or not args.no_show
    if needs_animation:
        anim = animation.FuncAnimation(
            figure,
            update,
            frames=len(frames),
            interval=1000.0 / args.fps,
            blit=False,
            repeat=True,
        )

    if args.save is not None:
        save_animation(anim, animation, args.save, args.fps)

    if not args.no_show:
        plt.show()
    else:
        plt.close(figure)


def main() -> None:
    args = parse_args()
    body_path, motion_path = resolve_input_paths(args)
    body = parse_body_geometry(body_path)
    motion = parse_joint_motion(motion_path)
    frames, frame_indices = build_frames(
        body=body,
        motion=motion,
        frame_step=args.frame_step,
        normalized=args.normalized,
    )
    plot_animation(frames=frames, frame_indices=frame_indices, motion=motion, args=args)


if __name__ == "__main__":
    main()
