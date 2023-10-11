import cv2

class Camera:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)  # Use 0 for the default camera

    def get_frame(self):
        ret, frame = self.cap.read()
        _, buffer = cv2.imencode('.jpg', frame)
        return buffer.tobytes()
