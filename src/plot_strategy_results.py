import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

os.makedirs("plots", exist_ok=True)

df = pd.read_csv("results/strategy_channel_summary.csv")

# Give each strategy a readable label.
def strategy_label(row):
    if row["strategy"] == "periodic":
        return f"Periodic {int(row['interval_ms'])} ms"
    return row["strategy"].replace("-", " ").title()

df["label"] = df.apply(strategy_label, axis=1)
labels = df["label"].tolist()
x = np.arange(len(df))

# Graph 1: AoI comparison
fig, axes = plt.subplots(1, 3, figsize=(16, 5))

aoi_metrics = [
    ("average_aoi_s", "Average AoI (s)"),
    ("p95_aoi_s", "95th-percentile AoI (s)"),
    ("maximum_aoi_s", "Maximum AoI (s)"),
]

for ax, (column, title) in zip(axes, aoi_metrics):
    ax.bar(x, df[column])
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylabel("Seconds")
    ax.grid(axis="y", alpha=0.3)

fig.suptitle("Age of Information Across Synchronization Strategies")
fig.tight_layout()
fig.savefig("plots/strategy_aoi_comparison.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# Graph 2: Position error comparison
fig, ax = plt.subplots(figsize=(10, 6))
width = 0.36

ax.bar(
    x - width / 2,
    df["average_position_error_m"],
    width,
    label="Average position error",
)
ax.bar(
    x + width / 2,
    df["maximum_position_error_m"],
    width,
    label="Maximum position error",
)

ax.set_title("Digital Twin Position Error")
ax.set_ylabel("Position error (m)")
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=30, ha="right")
ax.legend()
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig("plots/strategy_position_error.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# Graph 3: Communication overhead
fig, ax = plt.subplots(figsize=(10, 6))

bars = ax.bar(x, df["overhead_bytes_per_sec"])
ax.set_title("Communication Overhead by Strategy")
ax.set_ylabel("Overhead (bytes/second)")
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=30, ha="right")
ax.grid(axis="y", alpha=0.3)

for bar, value in zip(bars, df["overhead_bytes_per_sec"]):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        f"{value:.0f}",
        ha="center",
        va="bottom",
        fontsize=8,
    )

fig.tight_layout()
fig.savefig("plots/strategy_communication_overhead.png", dpi=200, bbox_inches="tight")
plt.close(fig)

print("Created plots:")
print("plots/strategy_aoi_comparison.png")
print("plots/strategy_position_error.png")
print("plots/strategy_communication_overhead.png")
