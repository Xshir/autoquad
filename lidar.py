import serial
import time

def read_tfluna_data(serial_port):
    try:
        while True:
            counter = serial_port.in_waiting  # count the number of bytes in the serial port
            if counter > 8:
                bytes_serial = serial_port.read(9)  # read 9 bytes
                serial_port.reset_input_buffer()  # reset buffer

                if bytes_serial[0] == 0x59 and bytes_serial[1] == 0x59:  # check first two bytes
                    distance = bytes_serial[2] + bytes_serial[3] * 256  # distance in next two bytes
                    strength = bytes_serial[4] + bytes_serial[5] * 256  # signal strength in next two bytes
                    temperature = bytes_serial[6] + bytes_serial[7] * 256  # temp in next two bytes
                    temperature = (temperature / 8.0) - 256.0  # temp scaling and offset
                    return distance / 100.0, strength, temperature
    except Exception as e:
        print(f"Error in read_tfluna_data: {e}")
        raise

if __name__ == "__main__":
    try:
        # Open serial port with explicit baud rate setting
        with serial.Serial("/dev/serial0", 115200, timeout=0) as ser:
            # Explicitly set baud rate
            ser.baudrate = 115200

            # Add a delay after changing baud rate
            time.sleep(2)

            # Infinite loop to read and print data
            while True:
                print(read_tfluna_data(ser))
                time.sleep(0.1)  # Add a small delay to control loop frequency

    except KeyboardInterrupt:
        print("Serial port closed.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")