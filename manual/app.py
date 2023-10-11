from flask import Flask, render_template, Response
from camera import Camera

app = Flask(__name__)

camera = Camera()

@app.route('/')
def index():
    return render_template('index.html', scanned_items=camera.scanned_items)

def generate_frames():
    while True:
        frame = camera.get_frame()
        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


