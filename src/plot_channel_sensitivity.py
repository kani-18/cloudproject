
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("results/channel_sensitivity_summary.csv")

# Plot 1: Packet delivery ratio
plt.figure()
plt.plot(
    df["condition"],
    df["pdr_percent"],
    marker="o"
)
plt.xlabel("Channel condition")
plt.ylabel("Packet Delivery Ratio (%)")
plt.title("Channel Condition vs Packet Delivery Ratio")
plt.grid(True)
plt.tight_layout()
plt.savefig("plots/channel_pdr.png", dpi=300)
plt.close()

# Plot 2: Average Age of Information
plt.figure()
plt.plot(
    df["condition"],
    df["average_aoi_s"] * 1000,
    marker="o"
)
plt.xlabel("Channel condition")
plt.ylabel("Average AoI (ms)")
plt.title("Channel Condition vs Average AoI")
plt.grid(True)
plt.tight_layout()
plt.savefig("plots/channel_aoi.png", dpi=300)
plt.close()

# Plot 3: Average position error
plt.figure()
plt.plot(
    df["condition"],
    df["average_position_error_m"],
    marker="o"
)
plt.xlabel("Channel condition")
plt.ylabel("Average position error (m)")
plt.title("Channel Condition vs Position Error")
plt.grid(True)
plt.tight_layout()
plt.savefig("plots/channel_position_error.png", dpi=300)
plt.close()

print("Saved plots/channel_pdr.png")
print("Saved plots/channel_aoi.png")
print("Saved plots/channel_position_error.png")
