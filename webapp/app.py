import cv2
from flask import Flask, render_template, Response, send_from_directory, jsonify
from pyzbar.pyzbar import decode
from pyzbar.pyzbar import ZBarSymbol
import csv

app = Flask(__name__)

scanned_items = []

cap = cv2.VideoCapture(0)

def generate_frames():
    supported_symbols = [ZBarSymbol.CODE128, ZBarSymbol.QRCODE]

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        decoded_objects = decode(frame, symbols=supported_symbols)

        if decoded_objects:
            for object_ in decoded_objects:
                returned_text = object_.data.decode('utf-8')
                object_type = object_.type

                try:
                    # Split the scanned data into LABEL and DESCRIPTION
                    parts = returned_text.split(':')
                    if len(parts) == 2:
                        label = parts[0]
                        description = parts[1]
                    else:
                        label = returned_text
                        description = "NIL"  # Set to NIL if not in the format "LABEL:DESCRIPTION"
                except ValueError:
                    label = "Non-text Data"
                    description = "Unknown Type"

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

def run_webapp(): 
    app.run(host='192.168.0.46', port=5000) # change host to hostname -I output for rpi linux distros

run_webapp()