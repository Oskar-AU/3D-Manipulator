
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

    

    # Determine dimensionality (2 or 3). If telemetry provides only 1D, we'll treat as 2D with zeros.
    n_axes = actual.shape[1] if actual.ndim == 2 else 1

    # Cross-track error (mm) to intended polyline (works for 2D or 3D)
    errors_mm = _project_distance_to_polyline(actual, intended)
    sample_indices = np.arange(len(errors_mm))

    # Layout: for 2 axes -> [XY | cross-track], for 3 axes -> [XY, XZ, 3D, cross-track]
    if n_axes == 2:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle("Manipulator Path Analysis (2-axis)", fontsize=18, fontweight="bold", y=0.98)

        # XY Path
        ax1.plot(actual[:, 0], actual[:, 1], "r-", linewidth=1.5, label="Actual Path", alpha=0.8)
        
        if intended.shape[1] >= 2:
            ax1.plot(intended[:, 0], intended[:, 1], "b--", linewidth=1.0, label="Intended Path", alpha=0.6)
        ax1.set_title("XY Path Comparison")
        ax1.set_xlabel("X (mm)")
        ax1.set_ylabel("Y (mm)")
        ax1.set_aspect("equal")
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # Cross-track error
        ax2.plot(sample_indices, errors_mm, "g-", linewidth=1.2)
        
        ax2.fill_between(sample_indices, errors_mm, alpha=0.2)
        ax2.set_title("Cross-Track Error to Intended Path")
        ax2.set_xlabel("Sample Number")
        ax2.set_ylabel("Error (mm)")
        ax2.grid(True, alpha=0.3)

    else:
        # Default to handling 3D or higher as 3D visualization + cross-track
        fig = plt.figure(figsize=(16, 10))
        fig.suptitle("3D Manipulator Path Analysis Dashboard", fontsize=20, fontweight="bold", y=0.95)

        # XY Path
        ax1 = fig.add_subplot(2, 2, 1)
        ax1.plot(actual[:, 0], actual[:, 1], "r-", linewidth=1.5, label="Actual Path", alpha=0.8)
        
        ax1.plot(intended[:, 0], intended[:, 1], "b--", linewidth=1.0, label="Intended Path", alpha=0.6)
        ax1.set_title("XY Path Comparison")
        ax1.set_xlabel("X (mm)")
        ax1.set_ylabel("Y (mm)")
        ax1.set_aspect("equal")
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # XZ Path
        ax2 = fig.add_subplot(2, 2, 2)
        ax2.plot(actual[:, 0], actual[:, 2], "r-", linewidth=1.5, alpha=0.8)
        ax2.plot(intended[:, 0], intended[:, 2], "b--", linewidth=1.0, alpha=0.6)
        ax2.set_title("XZ Path Comparison")
        ax2.set_xlabel("X (mm)")
        ax2.set_ylabel("Z (mm)")
        ax2.grid(True, alpha=0.3)

        # 3D Path
        try:
            ax3 = fig.add_subplot(2, 2, 3, projection="3d")
            ax3.plot(intended[:, 0], intended[:, 1], intended[:, 2], "b-", linewidth=1.2, label="Intended")
            ax3.plot(actual[:, 0], actual[:, 1], actual[:, 2], "r-", linewidth=1.2, label="Actual")
            
            ax3.set_title("3D Path Comparison")
            ax3.set_xlabel("X (mm)")
            ax3.set_ylabel("Y (mm)")
            ax3.set_zlabel("Z (mm)")
            ax3.legend()
        except Exception:
            # Matplotlib 3D not available; skip 3D plot
            pass

        # Cross-track error (bottom-right)
        ax4 = fig.add_subplot(2, 2, 4)
        ax4.plot(sample_indices, errors_mm, "g-", linewidth=1.2)
        
        ax4.fill_between(sample_indices, errors_mm, alpha=0.2)
        ax4.set_title("Cross-Track Error to Intended Path")
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

    # Place stats on whatever axes exist: prefer cross-track axis if present
    try:
        if n_axes == 2:
            ax2.text(
                0.02,
                0.98,
                stats_text,
                transform=ax2.transAxes,
                fontsize=10,
                va="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
            )
        else:
            ax4.text(
                0.02,
                0.98,
                stats_text,
                transform=ax4.transAxes,
                fontsize=10,
                va="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
            )
    except Exception:
        # If axes not found, silently continue
        pass

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

    commanded = np.asarray(next_velocity_ms)
    actual = np.asarray(actual_velocities_ms)

    # Determine number of axes (drives)
    n_axes = actual.shape[1] if (hasattr(actual, "ndim") and actual.ndim == 2) else 1

    base_labels = ["X (Drive 1)", "Y (Drive 2)", "Z (Drive 3)"]
    axis_labels = base_labels[:n_axes]

    fig, axes = plt.subplots(n_axes, 1, figsize=(12, 3 * max(1, n_axes)), sharex=True)
    fig.suptitle("Velocity Analysis Dashboard", fontsize=16, fontweight="bold")

    # Normalize axes to iterable list
    if n_axes == 1:
        axes = [axes]

    for i, ax in enumerate(axes):
        ax.plot(t, actual[:, i], label="Actual Velocity (m/s)", linewidth=1.5)
        ax.plot(t, commanded[:, i], label="Commanded Velocity (m/s)", linestyle="--", linewidth=1.0)
        ax.set_ylabel(f"{axis_labels[i]}\nVel (m/s)")
        ax.set_title(f"{axis_labels[i]} Velocity Tracking", fontsize=12, fontweight="bold")
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