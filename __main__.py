from dronekit import connect, VehicleMode
from wings import AutonomousQuadcopter
from webapp.app import run_webapp
import time
import threading


vehicle = AutonomousQuadcopter()
webapp_thread = threading.Thread(target=run_webapp)
fly = False

try:
    target_altitude = 0.3
    if not fly:
        print('not flying')
    else: 
        vehicle.basic_mission(target_altitude)
except Exception as e:
    print(f"An error occurred: {e}")

finally:
    print("Closing the connection.")
    vehicle.vehicle.close()
