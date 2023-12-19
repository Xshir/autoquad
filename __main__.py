from dronekit import connect, VehicleMode
from wings import AutonomousQuadcopter

import time
import threading
import traceback


vehicle = AutonomousQuadcopter()


try:
    target_altitude = 0.3
    vehicle.basic_mission(target_altitude)
except Exception as e:
    print(f"An error occurred in the mission: {e}")
    print(traceback.extract_tb())

finally:
    print("Closing the connection.")
    vehicle.vehicle.close()