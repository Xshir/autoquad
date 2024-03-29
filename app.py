import cv2, csv, os
from flask import Flask, render_template, Response, send_from_directory, jsonify, request
import zxingcpp
from wings import AutonomousQuadcopter
import traceback
import socket
from lidar import read_tfluna_data
import serial
import time
import platform

import struct
import pyttsx3
import pywifi
from pywifi import const
from dronekit import VehicleMode


app = Flask(__name__)
known_barcodes = {
    # label : # desc
    "350A": 'inventory_item_800',
    "380": 'inventory_item_800',
    "777": 'inventory_item_300er',
    "787DL": 'inventory_item_900'
}

scanned_items = []
cap = cv2.VideoCapture(0)
barcode_standalone_bool = True
use_raspberrypi_connected_lidar = True
vehicle = AutonomousQuadcopter(barcode_standalone=barcode_standalone_bool)
if barcode_standalone_bool is False:
    import fcntl, pyroute2

if use_raspberrypi_connected_lidar is True:
    if platform.system() == 'Windows':
        ser = serial.Serial(port='COM6', baudrate=115200)
    elif platform.system() == 'Linux':
        ser = serial.Serial(port='/dev/ttyUSB0', baudrate=115200)


#vehicle.lidar_serial_object = ser
#time.sleep(2)
def configure_audio_output(card, device):
    # Set the default audio output device using amixer
    command = f"amixer -c {card} cset numid=3 {device}"  # Assuming card 1 (USB Audio) is used
    os.system(command)

def text_to_speech(text, rate=140, volume=1, card=1, device=0):
    # Initialize the text-to-speech engine
    engine = pyttsx3.init(driverName='espeak', debug=True)
    engine.setProperty('rate', rate)
    engine.setProperty('volume', volume)

    # Configure the audio output
    configure_audio_output(card, device)

    # Convert text to speech and auto-play
    engine.say(text)
    engine.runAndWait()



def get_ip_and_ssid(interface='wlan0'):
    try:

        if barcode_standalone_bool is True:
            return "127.0.0.1", None
        # Create a socket object to get the local machine's IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Get the IP address of the specified network interface (e.g., wlan0)
        ip_address = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', bytes(interface[:15], 'utf-8')))[20:24])

        # Get the current connected Wi-Fi SSID
        wifi = pywifi.PyWiFi()
        iface = wifi.interfaces()[0]  # Assuming there is only one Wi-Fi interface

        # Use pyroute2 to get the connected Wi-Fi SSID
        ipr = pyroute2.IPRoute()
        idx = ipr.link_lookup(ifname=interface)[0]
        wireless_attr = ipr.get_links(idx)[0].get_attr('IFLA_WIRELESS')

        # Check if IFLA_WIRELESS attribute exists and is not None
        ssid = wireless_attr.get('ssid').decode('utf-8') if wireless_attr and wireless_attr.get('ssid') else None

        return ip_address, ssid
    except Exception as e:
        print(f"Error: {e}")
        return None, None
    

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
                    description = known_barcodes[str(label)]

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
    csv_data = "No.,LABEL,Description\n"
    for i, item in enumerate(scanned_items, 1):
        csv_data += f"{i},{item['label']},{item['description']}\n"

    response_headers = {
        'Content-Disposition': 'attachment; filename=scanned_items.csv',
        'Content-Type': 'text/csv',
    }

    return csv_data, 200, response_headers

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
        #print(traceback.extract_tb())
        return jsonify({"status": "error", "message": f"Failed to initiate takeoff: {str(e)}"})

@app.route('/get_lidar_data')
def get_lidar_data():
    try:
    
      
        if barcode_standalone_bool is True and use_raspberrypi_connected_lidar is False:
            return jsonify({"distance": 0.0, "pitch": round(0.00, 2), "roll": round(0.00, 2), "yaw": round(0.00, 2)})

        else:
            if use_raspberrypi_connected_lidar is False:
                distance, signal_strength, temperature = round(vehicle.vehicle.rangefinder.distance, 2), "unavailable", "unavailable"
            elif use_raspberrypi_connected_lidar is True:
                if ser is not None:

                    distance, signal_strength, temperature = round(read_tfluna_data(ser)[0], 2), "unavailable", "unavailable"
                else:
                    distance = '0.0'
            vehicle.lidar_distance = distance
            vehicle.lidar_signal_strength = signal_strength
            vehicle.lidar_temperature = temperature
            try:
                return jsonify({"distance": distance, "pitch": round(vehicle.vehicle.attitude.pitch, 2), "roll": round(vehicle.vehicle.attitude.roll, 2), "yaw": round(vehicle.vehicle.attitude.yaw, 2)})
            except:
                return jsonify({"distance": distance, "pitch": round(0, 2), "roll": round(0, 2), "yaw": round(0, 2)})
    except Exception as e:
        print(f"Error in get_lidar_data: {e}")
        return jsonify({"error": "Failed to get lidar data"})

@app.route('/get_armed_status')
def get_armed_status():
    if barcode_standalone_bool:
        return jsonify({"armed": "Yes"})
    else:
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


@app.route('/emergency_landing', methods=['POST'])
def emergency_landing():
    vehicle.vehicle.mode = VehicleMode("LAND")
    print("Emergency landing initiated!")
    
    # You can return a response if needed
    return jsonify({"message": "Emergency landing initiated!"})


if __name__ == '__main__':
    wlan_ip, ssid = get_ip_and_ssid()
    try:
       # text_to_speech(f"Connected to WiFi at {ssid} with ip {wlan_ip}")
        print("tts done")
        app.run(host=wlan_ip, port=5000)
    except: pass
        #text_to_speech(f"Failed to run app, please debug and look into logs.")