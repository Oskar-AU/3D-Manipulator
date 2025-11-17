
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from Manipulator.Manipulator import Telemetry

plt.style.use("seaborn-v0_8-darkgrid")


# ---------------------------------------------------------------------------
# Geometry helper
# ---------------------------------------------------------------------------

def _project_distance_to_polyline(points_mm, waypoints_mm):
  
    P = np.asarray(points_mm, float)
    W = np.asarray(waypoints_mm, float)

    S, E = W[:-1], W[1:]          # segment start and end
    V = E - S                     # segment vectors
    L2 = np.maximum(np.sum(V * V, axis=1), 1e-12)  # segment lengths squared

    d_out = np.zeros(len(P))
    for i, p in enumerate(P):
        PS = p - S                               # vector from segment start to point
        t = np.clip(np.einsum("ij,ij->i", PS, V) / L2, 0.0, 1.0)
        proj = S + t[:, None] * V               # projection on each segment
        d = np.linalg.norm(p - proj, axis=1)    # distance to each projection
        d_out[i] = np.min(d)                    # closest segment
    return d_out


# Path analysis
# ---------------------------------------------------------------------------

def plot_path_analysis(intended_waypoints_mm, telemetry: Telemetry,
                       save_figure: bool = False) -> None:

    # Directly trust telemetry.to_arrays() (no try/except / empty checks)
    _, positions_mm, _, _ = telemetry.to_arrays()

    intended = np.asarray(intended_waypoints_mm, dtype=float)
    actual = np.asarray(positions_mm, dtype=float)

    # Cross-track error (mm) to intended polyline
    errors_mm = _project_distance_to_polyline(actual, intended)
    sample_indices = np.arange(len(errors_mm))

    fig = plt.figure(figsize=(16, 10))
    fig.suptitle(
        "3D Manipulator Path Analysis Dashboard",
        fontsize=20,
        fontweight="bold",
        y=0.95,
    )

    # 1. XY Path (top-left)
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.plot(intended[:, 0], intended[:, 1], "b-",
             linewidth=2, label="Intended Path", marker="o", markersize=2)
    ax1.plot(actual[:, 0], actual[:, 1], "r-",
             linewidth=1.5, label="Actual Path", alpha=0.8)
    ax1.scatter(intended[0, 0], intended[0, 1],
                c="green", s=100, marker="s", label="Start", zorder=5)
    ax1.scatter(intended[-1, 0], intended[-1, 1],
                c="red", s=100, marker="X", label="End", zorder=5)
    ax1.set_title("XY Path Comparison", fontsize=14, fontweight="bold")
    ax1.set_xlabel("X (mm)")
    ax1.set_ylabel("Y (mm)")
    ax1.set_aspect("equal")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # 2. XZ Path (top-right)
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.plot(intended[:, 0], intended[:, 2], "b-",
             linewidth=2, label="Intended Path", marker="o", markersize=2)
    ax2.plot(actual[:, 0], actual[:, 2], "r-",
             linewidth=1.5, label="Actual Path", alpha=0.8)
    ax2.scatter(intended[0, 0], intended[0, 2],
                c="green", s=100, marker="s", label="Start", zorder=5)
    ax2.scatter(intended[-1, 0], intended[-1, 2],
                c="red", s=100, marker="X", label="End", zorder=5)
    ax2.set_title("XZ Path Comparison", fontsize=14, fontweight="bold")
    ax2.set_xlabel("X (mm)")
    ax2.set_ylabel("Z (mm)")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # 3. 3D Path (bottom-left)
    ax3 = fig.add_subplot(2, 2, 3, projection="3d")
    ax3.plot(intended[:, 0], intended[:, 1], intended[:, 2],
             "b-", linewidth=2, label="Intended Path", marker="o", markersize=1)
    ax3.plot(actual[:, 0], actual[:, 1], actual[:, 2],
             "r-", linewidth=1.5, label="Actual Path", alpha=0.8)
    ax3.scatter(*intended[0], c="green", s=100, marker="s", label="Start")
    ax3.scatter(*intended[-1], c="red", s=100, marker="X", label="End")
    ax3.set_title("3D Path Comparison", fontsize=14, fontweight="bold")
    ax3.set_xlabel("X (mm)")
    ax3.set_ylabel("Y (mm)")
    ax3.set_zlabel("Z (mm)")
    ax3.legend()

    # 4. Cross-track error (bottom-right)
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.plot(sample_indices, errors_mm, "g-", linewidth=1.5)
    ax4.fill_between(sample_indices, errors_mm, alpha=0.3)
    ax4.set_title("Cross-Track Error to Intended Path", fontsize=14, fontweight="bold")
    ax4.set_xlabel("Sample Number")
    ax4.set_ylabel("Error (mm)")
    ax4.grid(True, alpha=0.3)

    avg_err = float(np.mean(errors_mm))
    max_err = float(np.max(errors_mm))
    rms_err = float(np.sqrt(np.mean(errors_mm ** 2)))

    stats_text = (
        f"Avg Error: {avg_err:.2f} mm\n"
        f"Max Error: {max_err:.2f} mm\n"
        f"RMS Error: {rms_err:.2f} mm\n"
        f"Samples: {len(errors_mm)}"
    )

    ax4.text(
        0.02,
        0.98,
        stats_text,
        transform=ax4.transAxes,
        fontsize=10,
        va="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
    )

    plt.tight_layout(rect=[0, 0, 1, 0.92])

    if save_figure:
        plt.savefig("path_analysis_cross_track.png", dpi=300, bbox_inches="tight")
        print("Figure saved as: path_analysis_cross_track.png")

    plt.show()


# ---------------------------------------------------------------------------
# Velocity analysis
# ---------------------------------------------------------------------------

def plot_velocity_analysis(telemetry: Telemetry, save_figure: bool = False) -> None:
   
    # Again: trust telemetry.to_arrays(); no try/except or empty checks
    t, _, next_velocity_ms, actual_velocities_ms = telemetry.to_arrays()

    axis_labels = ["X (Drive 1)", "Y (Drive 2)", "Z (Drive 3)"]

    fig, axes = plt.subplots(3, 1, figsize=(15, 10), sharex=True)
    fig.suptitle("Velocity Analysis Dashboard", fontsize=16, fontweight="bold")

    for i, ax in enumerate(axes):
        ax.plot(t, actual_velocities_ms[:, i],
                label="Actual Velocity (m/s)", linewidth=1.5)
        ax.plot(t, next_velocity_ms[:, i],
                label="Commanded Velocity (m/s)",
                linestyle="--", linewidth=1.0)
        ax.set_ylabel(f"{axis_labels[i]}\nVel (m/s)")
        ax.set_title(f"{axis_labels[i]} Velocity Tracking",
                     fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3)
        if i == 0:
            ax.legend(loc="upper right", fontsize=8)

    axes[-1].set_xlabel("Time (s)")

    if save_figure:
        plt.savefig("velocity_analysis.png", dpi=300, bbox_inches="tight")
        print("Velocity analysis saved as: velocity_analysis.png")

    plt.show()


# ---------------------------------------------------------------------------

def run_complete_analysis(intended_waypoints_mm, telemetry: Telemetry,
                          save_figures: bool = False) -> None:
    """
    Run path and velocity analysis in sequence.
    """
    print("Running path analysis (cross-track error)…")
    plot_path_analysis(intended_waypoints_mm, telemetry, save_figure=save_figures)

    print("\nRunning velocity analysis…")
    plot_velocity_analysis(telemetry, save_figure=save_figures)

    print("\n=== Complete Analysis Finished ===")