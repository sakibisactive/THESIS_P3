#!/usr/bin/env python3
import os
import sys
import random
import subprocess
import xml.etree.ElementTree as ET

def main():
    # Ensure the virtual environment's bin folder is in the system PATH so subprocess can find 'sumo'
    venv_bin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv", "bin")
    path_dirs = [venv_bin, "/home/shiku/THESIS/.venv/bin"]
    sys_bin_dir = os.path.dirname(sys.executable)
    if sys_bin_dir:
        path_dirs.append(sys_bin_dir)
        
    for p_dir in path_dirs:
        if os.path.exists(p_dir) and p_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = p_dir + os.pathsep + os.environ.get("PATH", "")

    net_file = "data/networks/midtown_manhattan.net.xml"
    output_dir = "outputs"
    route_file = os.path.join(output_dir, "light_trips.rou.xml")
    tripinfo_file = os.path.join(output_dir, "light_tripinfo.xml")
    summary_file = os.path.join(output_dir, "light_simulation_summary.md")
    
    os.makedirs(output_dir, exist_ok=True)
    
    print("============================================================")
    # 1. Parse Network Map Details
    print(f"Parsing network map: {net_file} ...")
    if not os.path.exists(net_file):
        print(f"Error: Network file {net_file} not found.")
        sys.exit(1)
        
    try:
        tree = ET.parse(net_file)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML network file: {e}")
        sys.exit(1)
        
    centerline_length = 0.0
    total_lane_length = 0.0
    passenger_edges = []
    
    for edge in root.findall("edge"):
        edge_id = edge.get("id")
        if edge_id.startswith(":"):
            continue  # Skip junction internal edges
            
        edge_allowed = False
        edge_len = 0.0
        
        for lane in edge.findall("lane"):
            allow = lane.get("allow")
            disallow = lane.get("disallow")
            
            is_passenger_allowed = True
            if allow is not None:
                is_passenger_allowed = "passenger" in allow
            if disallow is not None:
                is_passenger_allowed = "passenger" not in disallow
                
            if is_passenger_allowed:
                edge_allowed = True
                lane_len = float(lane.get("length"))
                total_lane_length += lane_len
                edge_len = lane_len
                
        if edge_allowed:
            centerline_length += edge_len
            passenger_edges.append(edge_id)
            
    print(f"Successfully parsed map:")
    print(f"  - Centerline Road Distance: {centerline_length / 1000.0:.3f} km ({centerline_length:.2f} m)")
    print(f"  - Total Lane Distance:      {total_lane_length / 1000.0:.3f} km ({total_lane_length:.2f} m)")
    print(f"  - Valid Passenger Edges:    {len(passenger_edges)}")
    
    # 2. Generate Random Trips
    num_trips = 150
    if len(sys.argv) > 1:
        try:
            num_trips = int(sys.argv[1])
        except ValueError:
            print(f"Warning: Could not parse '{sys.argv[1]}' as an integer. Using default of 150 vehicles.")
            
    print(f"\nGenerating {num_trips} random passenger trips...")
    
    random.seed(42)  # For reproducibility
    
    trips_content = '<routes>\n'
    trips_content += '    <vType id="passenger_car" vClass="passenger" accel="2.6" decel="4.5" sigma="0.5" length="5.0" minGap="2.5" maxSpeed="13.89"/>\n'
    
    # Scale departure intervals so all vehicles are spawned within the first 1800 seconds (30 minutes)
    depart_interval = 1800.0 / num_trips if num_trips > 0 else 1.0
    
    for i in range(num_trips):
        start_edge = random.choice(passenger_edges)
        end_edge = random.choice(passenger_edges)
        while start_edge == end_edge:
            end_edge = random.choice(passenger_edges)
            
        trips_content += f'    <trip id="veh_{i}" type="passenger_car" depart="{i * depart_interval:.2f}" from="{start_edge}" to="{end_edge}"/>\n'
    trips_content += '</routes>\n'
    
    with open(route_file, "w") as rf:
        rf.write(trips_content)
        
    # 3. Run SUMO Simulation
    print("\nRunning SUMO simulation...")
    sumo_cmd = [
        "sumo",
        "-n", net_file,
        "-r", route_file,
        "--tripinfo-output", tripinfo_file,
        "--ignore-route-errors",
        "--no-warnings",
        "--no-step-log",
        "--end", "3600"
    ]
    
    # Check if sumo is in PATH
    try:
        subprocess.run(["sumo", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        print("Error: 'sumo' binary not found. Please make sure SUMO is installed and added to your PATH.")
        sys.exit(1)
        
    result = subprocess.run(sumo_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"SUMO simulation failed with return code {result.returncode}")
        print("Stdout:", result.stdout)
        print("Stderr:", result.stderr)
        sys.exit(1)
        
    # 4. Parse Results
    print("Processing simulation results...")
    if not os.path.exists(tripinfo_file):
        print(f"Error: tripinfo output file {tripinfo_file} was not generated.")
        sys.exit(1)
        
    try:
        trip_tree = ET.parse(tripinfo_file)
        trip_root = trip_tree.getroot()
    except Exception as e:
        print(f"Error parsing tripinfo XML: {e}")
        sys.exit(1)
        
    completed_trips = 0
    total_completed_distance = 0.0
    
    for tripinfo in trip_root.findall("tripinfo"):
        completed_trips += 1
        total_completed_distance += float(tripinfo.get("routeLength"))
        
    completion_percentage = (completed_trips / num_trips) * 100.0 if num_trips > 0 else 0.0
    avg_distance = (total_completed_distance / completed_trips) if completed_trips > 0 else 0.0
    
    # 5. Output Summary Report
    print("\n============================================================")
    print("                 LIGHT MAP SIMULATION RESULTS               ")
    print("============================================================")
    print(f"1. Total Scheduled Trips:       {num_trips}")
    print(f"2. Vehicles Completed Trips:     {completed_trips}")
    print(f"3. Trip Completion Rate:        {completion_percentage:.2f}%")
    print(f"4. Average Completed Distance:  {avg_distance / 1000.0:.3f} km ({avg_distance:.2f} m)")
    print(f"5. Map Centerline Distance:     {centerline_length / 1000.0:.3f} km ({centerline_length:.2f} m)")
    print(f"6. Map Total Lane Distance:     {total_lane_length / 1000.0:.3f} km ({total_lane_length:.2f} m)")
    print("============================================================")
    
    # 6. Save Markdown File
    report_content = f"""# Midtown Manhattan Map Light Simulation Report

This report summarizes details and trip statistics on the **Midtown Manhattan** map (`{net_file}`).

## 1. Map Structural Specifications
* **Map Centerline Road Distance:** **{centerline_length / 1000.0:.3f} km** ({centerline_length:.2f} meters)
* **Map Total Lane Distance:** **{total_lane_length / 1000.0:.3f} km** ({total_lane_length:.2f} meters)
* **Valid Passenger Vehicle Edges:** **{len(passenger_edges)}**

## 2. Vehicle Trip Performance
* **Total Trips Scheduled:** **{num_trips}**
* **Vehicles Completed All Trips:** **{completed_trips}**
* **Trip Completion Percentage:** **{completion_percentage:.2f}%**
* **Average Completed Trip Distance:** **{avg_distance / 1000.0:.3f} km** ({avg_distance:.2f} meters)

---
*Note: Trip routes were generated randomly across valid passenger roads and simulated using SUMO's built-in shortest-path router.*
"""
    
    try:
        with open(summary_file, "w") as sf:
            sf.write(report_content)
        print(f"Saved markdown summary to: {summary_file}")
    except Exception as e:
        print(f"Warning: Could not write summary markdown: {e}")
        
    # 7. Cleanup
    try:
        if os.path.exists(route_file):
            os.remove(route_file)
        if os.path.exists(tripinfo_file):
            os.remove(tripinfo_file)
    except Exception as e:
        print(f"Warning during file cleanup: {e}")

if __name__ == "__main__":
    main()
