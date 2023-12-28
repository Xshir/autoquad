import cv2
import csv
from flask import Flask, render_template, Response, send_from_directory, jsonify, request
import zxingcpp
from wings import AutonomousQuadcopter
import traceback
import socket
from lidar import read_tfluna_data
import serial
import time
import fcntl
import struct
import pyttsx3

app = Flask(__name__)
known_barcodes = {
    "350A": 'Airbus A350 XWB "Flying Raccoon"',
    "380": 'Airbus A380 "SuperJumbo"',
    "777": 'Boeing 777 "Cripple Seven"',
    "787DL": 'Boeing 787 DreamLiner "TupperJet"'
}

scanned_items = []
cap = cv2.VideoCapture(0)
vehicle = AutonomousQuadcopter()

def raw_imu_callback(self, attr_name, value):
    # attr_name == 'raw_imu'
    # value == vehicle.raw_imu
    print(value)

vehicle.add_attribute_listener('raw_imu', raw_imu_callback)

ser = serial.Serial("/dev/ttyUSB0", 115200, timeout=0)
ser.baudrate = 115200
vehicle.lidar_serial_object = ser
time.sleep(2)

def text_to_speech(text, rate=100):
    engine = pyttsx3.init()
    engine.setProperty('rate', rate)
    engine.say(text)
    engine.runAndWait()

def get_ip_address(interface='wlan0'):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip_address = socket.inet_ntoa(
            fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', bytes(interface[:15], 'utf-8')))[20:24])
        return ip_address
    except Exception as e:
        print(f"Error: {e}")
        return None

def generate_frames():
    while True:
        ret, frame = cap.read()

        if not ret:
            break

        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        results = zxingcpp.read_barcodes(gray_frame)

        if results:
            for result in results:
                returned_text = result.text

                if ':' in returned_text:
                    label, description = returned_text.split(':', 1)
                else:
                    label = returned_text
                    description = known_barcodes.get(str(label), "Unknown")

                if label not in [item['label'] for item in scanned_items]:
                    scanned_items.append({'label': label, 'description': description})
                    print(f"Scanned data: {label}, Type: {description}")

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

@app.route('/get_armed_status')
def get_armed_status():
    return jsonify({"armed": vehicle.vehicle.armed})

@app.route('/remove_scanned_item', methods=['POST'])
def remove_scanned_item():
    try:
        data = request.get_json()
        index = data.get('index')

        if index is not None and 0 <= index < len(scanned_items):
            removed_item = scanned_items.pop(index)
            print(f"Removed item: {removed_item}")
            return jsonify({"status": "success", "message": "Scanned item removed successfully."})
        else:
            return jsonify({"status": "error", "message": "Invalid index for removal."})

    except Exception as e:
        print(f"Error in remove_scanned_item: {e}")
        return jsonify({"status": "error", "message": "Failed to remove scanned item."})

@app.route('/get_drone_statistics')
def get_drone_statistics():
    try:
        distance, temperature, signal_strength = read_tfluna_data(ser)
        magnetic_field = vehicle.raw_imu  # Implement this method in AutonomousQuadcopter
        battery_voltage = vehicle.battery.voltage  # Implement this method in AutonomousQuadcopter
        return jsonify({"magnetic_field": magnetic_field, "battery_voltage": battery_voltage, "distance": distance, "temperature": temperature, "signal_strength": signal_strength})
    except Exception as e:
        print(f"Error in get_drone_statistics: {e}")
        return jsonify({"error": "Failed to get drone statistics"})

if __name__ == '__main__':
    wlan_ip = get_ip_address()
    app.run(host=wlan_ip, port=5000)
