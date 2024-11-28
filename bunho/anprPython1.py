from ctypes import *
import numpy as np
import cv2
import pymysql
from collections import deque
from datetime import datetime
import serial
import serial.tools.list_ports
import time

# DLL 경로 설정
def getLibPath():
    return r'C:\Users\USER\Desktop\tsanpr-KR-v2.4.2M\windows-x86_64\tsanpr.dll'

LIB_PATH = getLibPath()
lib = cdll.LoadLibrary(LIB_PATH)

lib.anpr_initialize.argtype = c_char_p
lib.anpr_initialize.restype = c_char_p
lib.anpr_read_pixels.argtypes = (c_char_p, c_int32, c_int32, c_int32, c_char_p, c_char_p, c_char_p)
lib.anpr_read_pixels.restype = c_char_p

def initialize():
    """TS ANPR 라이브러리 초기화"""
    error = lib.anpr_initialize('text')
    return error.decode('utf8') if error else error

def getPixelFormat(shape, dtype):
    """이미지의 포맷 확인"""
    if len(shape) == 2:
        if dtype == np.uint8:
            return 'GRAY'
    elif len(shape) == 3:
        channels = shape[2]
        if channels == 3 and dtype == np.uint8:
            return 'RGB'
        elif channels == 4 and dtype == np.uint8:
            return 'RGBA'
    return 'UNKNOWN'

def get_db_connection():
    """MySQL 데이터베이스 연결"""
    return pymysql.connect(
        host='localhost',
        user='root',
        password='audwlsrh1004*',
        db='ParkingDB',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def update_entry_time(vehicle_number):
    """ParkingLog의 entry_time과 drive 값을 업데이트"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # entry_time과 drive 값 설정
            sql = """
                UPDATE ParkingLog 
                SET entry_time = %s, drive = 1
                WHERE id = %s AND entry_time IS NULL
            """
            cursor.execute(sql, (datetime.now(), vehicle_number))
            if cursor.rowcount > 0:
                print(f"Entry time and drive updated for vehicle: {vehicle_number}")
            else:
                print(f"No matching vehicle found or entry_time already set for: {vehicle_number}")
            conn.commit()
    finally:
        conn.close()

def controlServo(arduino_port):
    """Arduino 제어를 통해 차단기 열기"""
    ports = serial.tools.list_ports.comports()
    port_found = any(port.device == arduino_port for port in ports)
    if not port_found:
        print(f"Port {arduino_port} not found.")
        return

    try:
        with serial.Serial(arduino_port, 9600, timeout=1) as arduino:
            time.sleep(2)
            arduino.write(b'ACTIVATE\n')
            print("Command sent: ACTIVATE")
            while arduino.in_waiting > 0:
                response = arduino.readline().decode('utf-8').strip()
                print(f"Arduino response: {response}")
    except serial.SerialException as e:
        print(f"Error communicating with Arduino: {e}")

def readPixelsFromWebcam(outputFormat, options, arduino_port):
    """웹캠을 통해 번호판 인식 및 데이터 업데이트"""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    detected_numbers = deque(maxlen=10)
    stored_numbers = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame.")
            break

        height, width = frame.shape[:2]
        pixelFormat = getPixelFormat(frame.shape, frame.dtype)
        if pixelFormat == 'UNKNOWN':
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

        detected_plate = result.decode('utf8').strip()
        print(f"Detected: {detected_plate}")

        if detected_plate:
            detected_numbers.append(detected_plate)

            # 최근 10개 모두 같은 번호판인지 확인
            if len(detected_numbers) == 10 and len(set(detected_numbers)) == 1:
                if detected_plate not in stored_numbers:
                    update_entry_time(detected_plate)  # entry_time과 drive 업데이트
                    stored_numbers.add(detected_plate)
                    controlServo(arduino_port)  # 차단기 열기

        cv2.imshow("Webcam", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def main():
    """메인 함수"""
    error = initialize()
    if error:
        print(error)
        return

    arduino_port = 'COM8'  # Arduino 포트 설정
    readPixelsFromWebcam('text', 'v', arduino_port)

if __name__ == '__main__':
    main()
