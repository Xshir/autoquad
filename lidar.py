import serial
import time

ser = serial.Serial("/dev/ttyAMA0", 115200, timeout=0)

def read_tfluna_data():
    while True:
        try:
            counter = ser.in_waiting

            if counter > 8:
                bytes_serial = ser.read(9)
                ser.reset_input_buffer()

                # Check if bytes_serial has enough elements before accessing them
                if len(bytes_serial) >= 8 and bytes_serial[0] == 0x59 and bytes_serial[1] == 0x59:
                    distance = bytes_serial[2] + bytes_serial[3] * 256
                    signal_strength = bytes_serial[4] + bytes_serial[5] * 256  # Extract signal strength
                    temperature = bytes_serial[6] + bytes_serial[7] * 256
                    temperature = (temperature / 8.0) - 256.0
                    return distance / 100.0, temperature, signal_strength  # Return signal strength
        except OSError as e:
            print(f"Error reading Lidar data: {e}")
            # Close the serial port
            ser.close()
            # Reopen the serial port
            ser.open()
            time.sleep(1)  # Add a delay to ensure the port is fully reopened
            
if __name__ == "__main__":
    while 1:
        print(read_tfluna_data())