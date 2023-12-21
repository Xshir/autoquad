import cv2, csv
from flask import Flask, render_template, Response, send_from_directory, jsonify
import zxingcpp
from wings import AutonomousQuadcopter
import traceback
import socket
from lidar import read_tfluna_data
import serial
import time

app = Flask(__name__)

scanned_items = []
cap = cv2.VideoCapture(0)
vehicle = AutonomousQuadcopter()

def get_ip_address():
    try:
        # Create a socket object to get the local machine's IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to a known external server (Google's public DNS)

        # Get the local IP address
        ip_address = s.getsockname()[0]

        # Close the socket
        s.close()

        return ip_address
    except Exception as e:
        print(f"Error: {e}")
        return None

def generate_frames():
    while True:
        ret, frame = cap.read()

        if not ret:
            break

        # Convert the frame to grayscale for zxingcpp
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Perform barcode scanning
        results = zxingcpp.read_barcodes(gray_frame)

        if results:
            for result in results:
                returned_text = result.text

                # Check if the scanned text is in "LABEL:DESCRIPTION" format
                if ':' in returned_text:
                    label, description = returned_text.split(':', 1)
                else:
                    label = returned_text
                    description = "NIL"

                if label not in [item['label'] for item in scanned_items]:
                    scanned_items.append({'label': label, 'description': description})
                    print(f"Scanned data: {label}, Type: {description}")  # Print the type of data to the terminal

        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')



@app.route('/')
def index():
    return render_template('index.html', scanned_items=scanned_items)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/download_csv')
def download_csv():
    with open('scanned_items.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["No.", "LABEL", "Description"])
        for i, item in enumerate(scanned_items, 1):
            writer.writerow([i, item['label'], item['description']])
    return send_from_directory('', 'scanned_items.csv', as_attachment=True)

@app.route('/get_scanned_items')
def get_scanned_items():
    return jsonify(scanned_items)

@app.route('/takeoff', methods=['POST'])
def takeoff():
    try:
        target_altitude = 0.3
        vehicle.basic_mission(target_altitude)
        return jsonify({"status": "success", "message": "Takeoff initiated."})
    except Exception as e:
        print(f"An error occurred in the mission: {e}")
        print(traceback.extract_tb())
        return jsonify({"status": "error", "message": f"Failed to initiate takeoff: {str(e)}"})
    # finally:
    #     print("Closing the connection.")
    #     vehicle.vehicle.close()

ser = serial.Serial("/dev/serial0", 115200, timeout=0)
ser.baudrate = 115200  # Set baud rate explicitly
time.sleep(2)

@app.route('/get_lidar_data')
def get_lidar_data():
    try:
        # Pass the instantiated serial port to read_tfluna_data
        distance, temperature, signal_strength = read_tfluna_data(ser)
        return jsonify({"distance": distance, "temperature": temperature, "signal_strength": signal_strength})
    except Exception as e:
        print(f"Error in get_lidar_data: {e}")
        return jsonify({"error": "Failed to get lidar data"})

@app.route('/get_armed_status')
def get_armed_status():
    return jsonify({"armed": vehicle.vehicle.armed})


if __name__ == '__main__':
    wlan_ip = get_ip_address()
    app.run(host=wlan_ip, port=5000)