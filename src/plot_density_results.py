import os
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

# Resolve paths relative to the project root, regardless of the current directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "results" / "density_summary.csv"
OUTPUT_DIR = PROJECT_ROOT / "plots"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if not INPUT_FILE.is_file():
    raise FileNotFoundError(f"Results file not found: {INPUT_FILE}")

df = pd.read_csv(INPUT_FILE)

required_columns = {
    "density",
    "strategy",
    "interval_ms",
    "average_aoi_s",
    "average_position_error_m",
    "overhead_bytes_per_sec",
    "pdr_percent",
}
missing_columns = required_columns - set(df.columns)
if missing_columns:
    raise ValueError(
        "The results CSV is missing required columns: "
        + ", ".join(sorted(missing_columns))
    )

# Convert numeric columns safely.
numeric_columns = [
    "density",
    "interval_ms",
    "average_aoi_s",
    "average_position_error_m",
    "overhead_bytes_per_sec",
    "pdr_percent",
]
for column in numeric_columns:
    df[column] = pd.to_numeric(df[column], errors="coerce")

# Give each periodic interval its own legend entry.
def make_label(row):
    strategy = str(row["strategy"]).strip().lower()
    if strategy == "periodic":
        interval = row["interval_ms"]
        if pd.isna(interval):
            return "Periodic (interval missing)"
        return f"Periodic {int(round(interval))} ms"
    if strategy == "event-triggered":
        return "Event-triggered"
    if strategy == "adaptive":
        return "AoI-aware adaptive"
    return str(row["strategy"])

df["label"] = df.apply(make_label, axis=1)

strategies = [
    "Periodic 50 ms",
    "Periodic 100 ms",
    "Periodic 500 ms",
    "Event-triggered",
    "AoI-aware adaptive",
]

# metric, y-axis label, title, output filename
graphs = [
    (
        "average_aoi_s",
        "Average AoI (seconds)",
        "Average AoI vs. Configured Vehicle Demand",
        "average_aoi_vs_demand.png",
    ),
    (
        "average_position_error_m",
        "Average Position Error (metres)",
        "Average Position Error vs. Configured Vehicle Demand",
        "position_error_vs_demand.png",
    ),
    (
        "overhead_bytes_per_sec",
        "Communication Overhead (bytes/second)",
        "Communication Overhead vs. Configured Vehicle Demand",
        "communication_overhead_vs_demand.png",
    ),
    (
        "pdr_percent",
        "Packet Delivery Ratio (%)",
        "Packet Delivery Ratio vs. Configured Vehicle Demand",
        "pdr_vs_demand.png",
    ),
]

def plot_metric(metric, ylabel, title, filename):
    fig, ax = plt.subplots(figsize=(9, 5.5))

    for strategy in strategies:
        part = df[df["label"] == strategy].sort_values("density")
        if not part.empty:
            ax.plot(
                part["density"],
                part[metric],
                marker="o",
                linewidth=2,
                label=strategy,
            )

    ax.set_title(title)
    ax.set_xlabel("Configured Demand Level (vehicles)")
    ax.set_ylabel(ylabel)
    ax.set_xticks(sorted(df["density"].dropna().unique()))
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()
    fig.tight_layout()

    output_path = OUTPUT_DIR / filename
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {output_path}")

for graph in graphs:
    plot_metric(*graph)

print("\nAll four graphs generated successfully.")
