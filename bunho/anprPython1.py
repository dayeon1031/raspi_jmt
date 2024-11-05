from ctypes import *
import numpy as np
import cv2
from PIL import Image
import sys, os, platform


def getLibPath():
    # 절대 경로로 DLL 경로를 직접 지정합니다.
    return r'C:\Users\USER\Desktop\tsanpr-KR-v2.4.2M\windows-x86_64\tsanpr.dll'

LIB_PATH = getLibPath()
print('LIB_PATH=', LIB_PATH)
lib = cdll.LoadLibrary(LIB_PATH)

lib.anpr_initialize.argtype = c_char_p
lib.anpr_initialize.restype = c_char_p

lib.anpr_read_pixels.argtypes = (c_char_p, c_int32, c_int32, c_int32, c_char_p, c_char_p, c_char_p)
lib.anpr_read_pixels.restype = c_char_p


def initialize():
    error = lib.anpr_initialize('text')
    return error.decode('utf8') if error else error

def getPixelFormat(shape, dtype):
    if len(shape) == 2:
        if dtype == np.uint8:
            return 'GRAY'
    elif len(shape) == 3:
        channels = shape[2]
        if channels == 3:
            if dtype == np.uint8:
                return 'RGB'
        elif channels == 4:
            if dtype == np.uint8:
                return 'RGBA'
    return 'UNKNOWN'

def readPixelsFromWebcam(outputFormat, options):
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame.")
            break
        
        height, width = frame.shape[:2]
        pixelFormat = getPixelFormat(frame.shape, frame.dtype)
        
        if pixelFormat == 'UNKNOWN':
            print("Error: Unsupported pixel format.")
            continue
        
        result = lib.anpr_read_pixels(
            frame.tobytes(), 
            width, 
            height, 
            frame.strides[0], 
            pixelFormat.encode('utf-8'), 
            outputFormat.encode('utf-8'), 
            options.encode('utf-8')
        )

        print(result.decode('utf8'))
        
        cv2.imshow("Webcam", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def main():
    error = initialize()
    if error:
        print(error)
        sys.exit(1)

    # Capture from webcam
    readPixelsFromWebcam('text', 'v')
    readPixelsFromWebcam('json', 'v')


if __name__ == '__main__':
    main()
