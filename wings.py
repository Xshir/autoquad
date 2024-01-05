from dronekit import connect, VehicleMode
import time
from lidar import read_tfluna_data

def lidar_failsafe_action():
    self.vehicle.channels.overrides['3'] = 1001
    self.vehicle.armed = False
    print("[FAILSAFE] Check Lidar Connections or Configuration | If not Lidar Issue; Check throttle params")


class AutonomousQuadcopter:

    def __init__(self):
        serial_port = '/dev/ttyACM0'; baud_rate = 9600
        self.vehicle = connect(serial_port, baud=baud_rate, wait_ready=True)
        self.current_altitude = 0
        self.lidar_failsafe_action = lidar_failsafe_action
        
    def rangefinder_takeoff(self):
            """
            Takes off on ALT_HOLD mode. Returns "Reached Target Altitude" as a string if success. Returns "Failed" as a string if failed.
            """
            self.target_altitude = 0.4
            if self.vehicle.rangefinder.distance is None: # second check
                self.lidar_failsafe_action()
                return "Failed"
            
            self.vehicle.mode = VehicleMode("ALT_HOLD")
            print("ALT HOLD")
            self.vehicle.channels.overrides['3'] = 1700  # throttle to takeoff (adjust if needed)
            has_hit_target = False

            while 1: # while True but faster binary compilation
                print(f"rngfnd dist: {self.vehicle.rangefinder.distance} | target altitude: {self.target_altitude} | has_hit_target: {has_hit_target}")
                if self.vehicle.rangefinder.distance <= self.target_altitude and has_hit_target is True: 
                    print('LOWERED AFTER HITTING TARGET')
                    self.lidar_failsafe_action()
                if self.vehicle.rangefinder.distance >= self.target_altitude * 0.90 and not self.vehicle.rangefinder.distance >= self.target_altitude * 1.30:
                    self.vehicle.channels.overrides['3'] = 1550 # hover
                    has_hit_target = True
                    return "Reached Target Altitude"
                elif self.vehicle.rangefinder.distance >= self.target_altitude * 1.30:
                    print("TOO HIGH ALTITUDE")
                    self.lidar_failsafe_action() # throttle param not lidar - too lazy to change func name
                    return "Failed"


    def takeoff(self, rpm, target_altitude):
        self.vehicle.mode = VehicleMode("ALT_HOLD")
        self.target_altitude = target_altitude
        takeoff_throttle = rpm
        start_time = time.time()  
        reached_target_altitude = False

        while True:
            self.vehicle.channels.overrides['3'] = int(takeoff_throttle)
            time.sleep(0.2)  # wait for stability
            distance, temp, signal_strength = self.lidar_distance, self.lidar_temperature, self.lidar_signal_strength
            self.current_altitude = distance
            current_altitude = distance

            # check if altitude requirements are met
            print(f"Altitude: {current_altitude} meters")
            if current_altitude >= target_altitude * 0.90:
                if not reached_target_altitude:
                    reached_target_altitude = True
                    print(f"[QUADCOPTER] Altitude Reached\nAltitude Level: {current_altitude}m | ({current_altitude/target_altitude}% of Target Altitude ({target_altitude})) | Reached RPM: {takeoff_throttle}")


            # check if RPM exceeds 1660
            if takeoff_throttle > 1800:
                print("[FAILSAFE] RPM exceeded 1660 - Cutting power and landing.")
                self.vehicle.channels.overrides['3'] = 1000  # throttle to minimum
                self.vehicle.mode = VehicleMode("LAND")
                self.vehicle.armed = False
                return 0  # Indicate that takeoff failed

            # Check if it's been more than 5 seconds
            if time.time() - start_time > 10:
                print("[FAILSAFE] Takeoff not successful within 5 seconds - Cutting power and landing.")
                self.vehicle.channels.overrides['3'] = 1000  # throttle to minimum
                self.vehicle.mode = VehicleMode("LAND")
                self.vehicle.armed = False
                return 0  # failed takeoff

            # break the loop if altitude is within 0.4cm of the target for hovering
            if reached_target_altitude and target_altitude - 0.4 <= current_altitude <= target_altitude + 0.4:
                break

            if takeoff_throttle != 1680:
                takeoff_throttle += 20
                
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

        self.vehicle.channels.overrides['1'] = takeoff_rpm 


    


    def basic_mission(self, target_altitude):
        """
        Arms the motors, takes off to the specified altitude, rolls right for a brief moment,
        and then lands.
        """

        # takeoff_rpm = 1300
        startup_mode = "ALT_HOLD"
        self.vehicle.mode = VehicleMode(startup_mode)
        print(f"[PROGRAM STATUS]: MODE SET TO {startup_mode}") 
        self.vehicle.armed = True

        if self.vehicle.rangefinder.distance is None: # first check
            self.lidar_failsafe_action()

        loop_count = 0
        while not self.vehicle.armed:
            loop_count += 1
            if loop_count % 5 == 0: # every 5 loops (every (approx) 5s)
                print("[PROGRAM STATUS]: ARMING | WAITING FOR COMPLETION")

            time.sleep(1)

        print("[PROGRAM STATUS]: ARM SET | ARM COMPLETE")
        
        
        if self.vehicle.armed:
            takeoff_return = self.rangefinder_takeoff()
            print(f"RETURN VAL: {takeoff_return} | {self.vehicle.channels.overrides['3']}")


            if takeoff_return == "Reached Target Altitude":
                start_time = time.time()
                

                if time.time() - start_time > 5:
                    print("HIT LANDING TIME")
                    self.vehicle.mode = VehicleMode("LAND")
            else: print("FAILED CHECK LIDAR")
            
                

            

            
            
        """
        if self.vehicle.armed:
            result_of_takeoff = self.takeoff(takeoff_rpm, target_altitude)
            print(f"Vehicle is armed: {self.vehicle.armed} on takeoff!")
        elif not self.vehicle.armed:
            print(f"Vehicle is armed: {self.vehicle.armed} on takeoff!")
        
        # uncomment after development of dashboard
        if result_of_takeoff > 0: # successful takeoff since rpm is not 0 indicating no takeoff failure.
            self.vehicle.mode = VehicleMode("LAND")
            print("[Quadcopter] Landing Now.")
        """