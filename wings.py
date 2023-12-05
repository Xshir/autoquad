from dronekit import connect, VehicleMode
import time
from lidar import read_tfluna_data

class AutonomousQuadcopter:

    def __init__(self):
        serial_port = '/dev/ttyACM0'; baud_rate = 9600
        self.vehicle = connect(serial_port, baud=baud_rate, wait_ready=True)
        
    
    def altitude_control(self, current_altitude, target_altitude, current_throttle):
        print(f"Altitude: {current_altitude} meters")

        altitude_difference = current_altitude - target_altitude

        if abs(altitude_difference) <= 0.5:  # A small tolerance to avoid constant adjustments
            return current_throttle  # No adjustment needed

        # Adjust throttle based on altitude difference
        throttle_adjustment = 10 * (altitude_difference / abs(altitude_difference))
        new_throttle = max(1000, min(1600, current_throttle + throttle_adjustment))
        print(new_throttle)
        return int(new_throttle)

    def takeoff(self, rpm, target_altitude):
        self.vehicle.mode = VehicleMode("ALT_HOLD")
        takeoff_throttle = rpm
        start_time = time.time()  # Record the start time
        reached_target_altitude = False

        while True:
            self.vehicle.channels.overrides['3'] = int(takeoff_throttle)
            time.sleep(0.2)  # Wait for stability
            distance, temp, signal_strength = read_tfluna_data()
            self.current_altitude = distance
            current_altitude = distance

            # Check if altitude requirements are met
            print(f"Altitude: {current_altitude} meters")
            if current_altitude >= target_altitude * 0.90:
                if not reached_target_altitude:
                    reached_target_altitude = True
                    print(f"[QUADCOPTER] Altitude Reached\nAltitude Level: {current_altitude}m | ({current_altitude/target_altitude}% of Target Altitude) | Reached RPM: {takeoff_throttle}")
                else:
                    # Hovering logic
                    if current_altitude >= target_altitude + 0.4:
                        takeoff_throttle -= 20  # Reduce throttle
                    else:
                        takeoff_throttle += 20  # Increase throttle

            # Check if RPM exceeds 1660
            if takeoff_throttle > 1700:
                print("[FAILSAFE] RPM exceeded 1660 - Cutting power and landing.")
                self.vehicle.channels.overrides['3'] = 1000  # Set throttle to minimum
                # self.vehicle.mode = VehicleMode("LAND")
                self.vehicle.armed = False
                return 0  # Indicate that takeoff failed

            # Check if it's been more than 5 seconds
            if time.time() - start_time > 5:
                print("[FAILSAFE] Takeoff not successful within 5 seconds - Cutting power and landing.")
                self.vehicle.channels.overrides['3'] = 1000  # Set throttle to minimum
                # self.vehicle.mode = VehicleMode("LAND")
                self.vehicle.armed = False
                return 0  # Indicate that takeoff failed

            # Break the loop if altitude is within 0.4cm of the target for hovering
            if reached_target_altitude and target_altitude - 0.4 <= current_altitude <= target_altitude + 0.4:
                break

            print(takeoff_throttle)

        return takeoff_throttle


    
    def roll(self, takeoff_rpm, direction, duration, bank):
        if direction == "left":
            roll_value = -bank
        elif direction == "right":
            roll_value = bank
        else: ValueError("[PROGRAMMED ERROR] Argument should be left or right")
    
        self.vehicle.channels.overrides['1'] = takeoff_rpm + roll_value
        time.sleep(duration)

        self.vehicle.channels.overrides['1'] = takeoff_rpm # Docs say value can be
        
        
    

    def basic_mission(self, target_altitude):
        """
        Arms the motors, takes off to the specified altitude, rolls right for a brief moment,
        and then lands.
        """
        takeoff_rpm = 1300
        startup_mode = "STABILIZE"
        self.vehicle.mode = VehicleMode(startup_mode)  # indoor flight without GPS mode 
        print(f"[PROGRAM STATUS]: MODE SET TO {startup_mode} | BATT: {self.vehicle.battery.level} @ {self.vehicle.battery.current}") 
        self.vehicle.armed = True

        loop_count = 0
        while not self.vehicle.armed:
            loop_count += 1
            if loop_count % 5 == 0: # every 5 loops (every (approx) 5s)
                print("[PROGRAM STATUS]: ARMING | WAITING FOR COMPLETION")

            time.sleep(1)


        print("[PROGRAM STATUS]: ARM SET | ARM COMPLETE")
        print("[PROGRAM STATUS]: TAKEOFF")
        if self.vehicle.armed:
            result_of_takeoff = self.takeoff(1300, 1)
            print(f"Vehicle is armed: {self.vehicle.armed} on takeoff!")
        elif not self.vehicle.armed:
            print(f"Vehicle is armed: {self.vehicle.armed} on takeoff!")

        if result_of_takeoff > 0: # successful takeoff since rpm is not 0 indicating no takeoff failure.
            #self.roll(takeoff_rpm, 'right', 1, 50)
            # Landing phase
            time.sleep(1)
            self.vehicle.mode = VehicleMode("LAND")
            print("[Quadcopter] Landing Now.")