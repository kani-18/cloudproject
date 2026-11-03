PROJECT README
==============

Project Title
-------------
Age-of-Information-Aware Digital Twin Synchronization in Vehicular Edge Networks

1. PROJECT OVERVIEW
-------------------
This project studies how different synchronization strategies affect the freshness
of vehicle information stored in a Digital Twin at a Roadside Unit (RSU).

The implementation uses SUMO to simulate vehicle movement and TraCI to obtain
vehicle states. A Python-based RSU Digital Twin stores the latest successfully
received vehicle state. A simplified communication channel models a fixed
transmission delay and independent packet loss.

The following synchronization strategies are compared:
- Periodic synchronization with intervals of 50 ms, 100 ms and 500 ms.
- Event-triggered synchronization based on changes in vehicle state, with a
  500 ms maximum transmission-attempt interval.
- AoI-aware adaptive synchronization, which selects an update interval based
  on the current AoI and vehicle movement.

2. SOFTWARE AND TOOLS
---------------------
- Ubuntu Linux
- SUMO 1.18.0
- Python 3
- TraCI and SUMO tools
- NumPy
- Pandas
- Matplotlib

SUMO must be installed separately and available in the system PATH. The project
uses SUMO_HOME=/usr/share/sumo in the current tested environment. If SUMO is
installed in another location, update the environment configuration accordingly.

3. PROJECT STRUCTURE
--------------------
The submitted project folder should contain the following main directories:

project/
    src/
        rsu_twin.py
        metrics.py
        channel.py
        strategy_channel_experiment.py
        density_experiment.py
        plot_density_results.py
        main.py
    sumo/
        network and SUMO configuration files
        generated route/trip files
    results/
        density_summary.csv
        experiment summary CSV files
    plots/
        average_aoi_vs_density.png
        position_error_vs_density.png
        overhead_vs_density.png
        pdr_vs_density.png

The exact set of generated SUMO files may depend on the final experiment run.

4. SETUP
--------
Open a terminal in the project folder.

Create and activate a virtual environment if one is not already present:

    python3 -m venv .venv
    source .venv/bin/activate

Install the Python dependencies:

    pip install traci sumolib numpy pandas matplotlib scipy

Check that SUMO is available:

    sumo --version

If SUMO is not found, install SUMO and configure its tools path before running
the Python scripts.

5. RUNNING THE EXPERIMENTS
--------------------------
From the project root directory, activate the virtual environment:

    source .venv/bin/activate

Run the complete density experiment workflow:

    python3 src/density_experiment.py

This orchestrates 25 experiment configurations:
- Five configured demand levels: 5, 10, 20, 50 and 100.
- Three periodic intervals at each demand level.
- One event-triggered configuration at each demand level.
- One adaptive configuration at each demand level.

The final summary is written to:

    results/density_summary.csv

6. GENERATING THE GRAPHS
------------------------
After the experiment summary CSV has been generated, run:

    python3 src/plot_density_results.py

The plotting script generates the following graphs in the plots directory:

- average_aoi_vs_density.png
- position_error_vs_density.png
- overhead_vs_density.png
- pdr_vs_density.png

7. EXPERIMENT CONFIGURATION
---------------------------
The reported experiments use these settings:

- Simulation duration: 120 seconds
- Simulation step: 0.05 seconds
- Simulated channel delay: 50 ms
- Independent packet-loss probability: 5%
- Assumed packet size for overhead calculation: 100 bytes
- Random seed: 42
- Configured demand levels: 5, 10, 20 and 50 and 100

The event-triggered policy checks position, speed, heading and acceleration
changes. Its configured thresholds are 5 m, 2 m/s, 15 degrees and 2 m/s^2,
respectively. It also attempts an update at least once every 500 ms.

The adaptive policy uses AoI and vehicle-state thresholds to select between
50 ms, 100 ms and 500 ms update intervals.

8. OUTPUT METRICS
-----------------
The experiment summary includes:

- Average, 95th-percentile and maximum AoI
- Average and maximum position error
- Average speed error
- Average heading error
- Transmission attempts
- Delivered and dropped packets
- Packet delivery ratio (PDR)
- Estimated communication overhead in bytes per second

The overhead is calculated using the assumed 100-byte packet size and the
number of attempted transmissions. It does not include full protocol headers
or other network-layer overhead.

9. MODEL LIMITATIONS
--------------------
The communication channel is a simplified software model. It applies a fixed
50 ms delay and independent 5% packet loss. It does not model radio propagation,
interference, contention, bandwidth sharing, retransmissions or a complete
vehicular wireless communication protocol.

The configured demand values identify traffic-generation scenarios. They do
not guarantee that the same number of vehicles is simultaneously active.

10. GITHUB REPOSITORY
---------------------
GitHub repository URL:
[Add your repository URL here]

The source code should be uploaded to the repository with a separate README.md
that describes the project, setup, execution steps, experiment configuration
and results.

11. SUBMISSION CONTENTS
-----------------------
The final master folder should contain these three items:

1. Project folder - source code, SUMO files, results and plots.
2. Project_Report.pdf - project understanding, methodology, implementation
   and experimental results.
3. readme.txt - this file, containing project and execution instructions.

12. CONTACT / PROJECT DETAILS
-----------------------------
Student name: [Enter name]
Roll number / USN: [Enter roll number]
Department: [Enter department]
Institution: National Institute of Technology Karnataka, Surathkal
Project mentor: [Enter mentor name]

Before submission, verify that the source files and SUMO configuration files
in the project folder match the versions used to generate the reported results.
