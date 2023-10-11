import cv2
from pyzbar.pyzbar import decode
from pyzbar.pyzbar import ZBarSymbol

class Camera:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)  # Use 0 for the default camera
        self.scanned_items = []
        self.supported_symbols = [ZBarSymbol.CODE128, ZBarSymbol.QRCODE]

    def get_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return None

        decoded_objects = decode(frame, symbols=self.supported_symbols)

        if decoded_objects:
            for object_ in decoded_objects:
                returned_text = object_.data.decode('utf-8')
                object_type = object_.type

            if returned_text not in self.scanned_items:
                self.scanned_items.append(returned_text)

        return frame

    def release(self):
        self.cap.release()
