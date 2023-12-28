from dronekit import connect, VehicleMode
import time
from lidar import read_tfluna_data
from dronekit import Vehicle

class RawIMU(object):
    """
    The RAW IMU readings for the usual 9DOF sensor setup. 
    This contains the true raw values without any scaling to allow data capture and system debugging.
    
    The message definition is here: https://mavlink.io/en/messages/common.html#RAW_IMU
    
    :param time_boot_us: Timestamp (microseconds since system boot). #Note, not milliseconds as per spec
    :param xacc: X acceleration (mg)
    :param yacc: Y acceleration (mg)
    :param zacc: Z acceleration (mg)
    :param xgyro: Angular speed around X axis (millirad /sec)
    :param ygyro: Angular speed around Y axis (millirad /sec)
    :param zgyro: Angular speed around Z axis (millirad /sec)
    :param xmag: X Magnetic field (milli tesla)
    :param ymag: Y Magnetic field (milli tesla)
    :param zmag: Z Magnetic field (milli tesla)    
    """
    def __init__(self, time_boot_us=None, xacc=None, yacc=None, zacc=None, xygro=None, ygyro=None, zgyro=None, xmag=None, ymag=None, zmag=None):
        """
        RawIMU object constructor.
        """
        self.time_boot_us = time_boot_us
        self.xacc = xacc
        self.yacc = yacc
        self.zacc = zacc
        self.xgyro = zgyro
        self.ygyro = ygyro
        self.zgyro = zgyro
        self.xmag = xmag        
        self.ymag = ymag
        self.zmag = zmag      
        
    def __str__(self):
        """
        String representation used to print the RawIMU object. 
        """
        return "RAW_IMU: time_boot_us={},xacc={},yacc={},zacc={},xgyro={},ygyro={},zgyro={},xmag={},ymag={},zmag={}".format(self.time_boot_us, self.xacc, self.yacc,self.zacc,self.xgyro,self.ygyro,self.zgyro,self.xmag,self.ymag,self.zmag)


class AutonomousQuadcopter(Vehicle):

    def __init__(self, *args):
        serial_port = '/dev/ttyACM0'; baud_rate = 9600
        super(AutonomousQuadcopter, self).__init__(*args)
        self.vehicle = connect(serial_port, baud=baud_rate)
        self.current_altitude = 0
        self._raw_imu = RawIMU()

        @self.on_message('RAW_IMU')
        def listener(self, name, message):
            """
            The listener is called for messages that contain the string specified in the decorator,
            passing the vehicle, message name, and the message.
            
            The listener writes the message to the (newly attached) ``vehicle.raw_imu`` object 
            and notifies observers.
            """
            self._raw_imu.time_boot_us=message.time_usec
            self._raw_imu.xacc=message.xacc
            self._raw_imu.yacc=message.yacc
            self._raw_imu.zacc=message.zacc
            self._raw_imu.xgyro=message.xgyro
            self._raw_imu.ygyro=message.ygyro
            self._raw_imu.zgyro=message.zgyro
            self._raw_imu.xmag=message.xmag
            self._raw_imu.ymag=message.ymag
            self._raw_imu.zmag=message.zmag
            
            # Notify all observers of new message (with new value)
            #   Note that argument `cache=False` by default so listeners
            #   are updated with every new message
            self.notify_attribute_listeners('raw_imu', self._raw_imu) 
    
    @property
    def raw_imu(self):
        return self._raw_imu

    def takeoff(self, rpm, target_altitude):
        self.vehicle.mode = VehicleMode("ALT_HOLD")
        self.target_altitude = target_altitude
        takeoff_throttle = rpm
        start_time = time.time()  # Record the start time
        reached_target_altitude = False

        while True:
            self.vehicle.channels.overrides['3'] = int(takeoff_throttle)
            time.sleep(0.2)  # Wait for stability
            distance, temp, signal_strength = read_tfluna_data(self.lidar_serial_object)
            self.current_altitude = distance
            current_altitude = distance

            # Check if altitude requirements are met
            print(f"Altitude: {current_altitude} meters")
            if current_altitude >= target_altitude * 0.90:
                if not reached_target_altitude:
                    reached_target_altitude = True
                    print(f"[QUADCOPTER] Altitude Reached\nAltitude Level: {current_altitude}m | ({current_altitude/target_altitude}% of Target Altitude ({target_altitude})) | Reached RPM: {takeoff_throttle}")


            # Check if RPM exceeds 1660
            if takeoff_throttle > 1800:
                print("[FAILSAFE] RPM exceeded 1660 - Cutting power and landing.")
                self.vehicle.channels.overrides['3'] = 1000  # Set throttle to minimum
                # self.vehicle.mode = VehicleMode("LAND")
                self.vehicle.armed = False
                return 0  # Indicate that takeoff failed

            # Check if it's been more than 5 seconds
            if time.time() - start_time > 10:
                print("[FAILSAFE] Takeoff not successful within 5 seconds - Cutting power and landing.")
                self.vehicle.channels.overrides['3'] = 1000  # Set throttle to minimum
                # self.vehicle.mode = VehicleMode("LAND")
                self.vehicle.armed = False
                return 0  # Indicate that takeoff failed

            # Break the loop if altitude is within 0.4cm of the target for hovering
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

        self.vehicle.channels.overrides['1'] = takeoff_rpm # Docs say value can be


    def altitude_control(self, takeoff_throttle):
        """
        Adjusts the throttle to maintain the target altitude and hovers for 3 seconds.
        """
        hover_duration = 3  # seconds
        start_hover_time = time.time()

        while self.vehicle.armed:
            distance, temp, signal_strength = read_tfluna_data(self.lidar_serial_object)
            self.current_altitude = distance

            if self.current_altitude > self.target_altitude * 0.95:
                takeoff_throttle -= 20
                print(f"ALTITUDE LOGGER: MINUS 20 -> NOW {takeoff_throttle}")
            else:
                takeoff_throttle += 20
                print(f"ALTITUDE LOGGER: PLUS 20 -> NOW {takeoff_throttle}")

            takeoff_throttle = max(1000, min(1900, takeoff_throttle))  # Ensure throttle is within valid range
            self.vehicle.channels.overrides['3'] = int(takeoff_throttle)
            print(f"[ALTITUDE CONTROL] Adjusting throttle to maintain altitude: {self.current_altitude} meters")

            time.sleep(0.05) # was 0.25

            # Check if the hover duration has been reached
            if time.time() - start_hover_time >= hover_duration:
                print("[ALTITUDE CONTROL] Hover duration reached. Exiting altitude control.")
                break

        print("[ALTITUDE CONTROL] Exiting altitude control.")


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
            result_of_takeoff = self.takeoff(takeoff_rpm, target_altitude)
            print(f"Vehicle is armed: {self.vehicle.armed} on takeoff!")
        elif not self.vehicle.armed:
            print(f"Vehicle is armed: {self.vehicle.armed} on takeoff!")
        
        # uncomment after development of dashboard
        if result_of_takeoff > 0: # successful takeoff since rpm is not 0 indicating no takeoff failure.
            self.altitude_control(result_of_takeoff)
            #self.roll(takeoff_rpm, 'right', 1, 50)
            # Landing phase
            self.vehicle.mode = VehicleMode("LAND")
            print("[Quadcopter] Landing Now.")