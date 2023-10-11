import cv2
from flask import Flask, render_template, Response
from pyzbar.pyzbar import decode
from pyzbar.pyzbar import ZBarSymbol

app = Flask(__name__)
scanned_items = []

def generate_frames():
    cap = cv2.VideoCapture(0)  # Use 0 for the default camera
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

            if returned_text not in scanned_items:
                scanned_items.append(returned_text)
                print(scanned_items)

        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()

@app.route('/')
def index():
    return render_template('index.html', scanned_items=scanned_items)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
