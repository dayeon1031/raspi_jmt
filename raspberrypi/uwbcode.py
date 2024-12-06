import mysql.connector
import time
import serial
import re
import numpy as np
import RPi.GPIO as GPIO
import pymysql
 
GPIO.setmode(GPIO.BCM)
green_pin = 3
button = 2
GPIO.setup(green_pin,GPIO.OUT, initial=GPIO.HIGH)
GPIO.setup(button,GPIO.IN)

# Serial 통신으로부터 데이터 읽기
def read_serial_data(ser):
    try:
        data = ser.read(100).decode('utf-8')  # 데이터 길이를 상황에 맞게 수정
        return data
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        return ""
       
# AT 명령어 전송 및 응답 확인 함수
def send_at_command(ser, command, expected_response="OK"):
    try:
        ser.write(command.encode())
        response = ser.read(100).decode('utf-8').strip()
        print(f"Sent: {command.strip()}, Received: {response}")
       
        if expected_response not in response:
            print(f"Error: Expected '{expected_response}', but got '{response}'")
            return False
        return True
    except serial.SerialException as e:
        print(f"Serial error while sending {command.strip()}: {e}")
        return False

       

# 거리값 추출 및 저장
def extract_distances(data):
    distance0 = None
    distance1 = None
    distance2 = None
    distance3 = None

    pattern0 = r"distance0:(\d+\.\d+)m"
    pattern1 = r"distance1:(\d+\.\d+)m"
    pattern2 = r"distance2:(\d+\.\d+)m"
    pattern3 = r"distance3:(\d+\.\d+)m"

    match0 = re.search(pattern0, data)
    match1 = re.search(pattern1, data)
    match2 = re.search(pattern2, data)
    match3 = re.search(pattern3, data)

    if match0:
        distance0 = float(match0.group(1))
    if match1:
        distance1 = float(match1.group(1))
    if match2:
        distance2 = float(match2.group(1))
    if match3:
        distance3 = float(match3.group(1))

    return distance0, distance1, distance2, distance3

# 4개의 앵커를 사용하여 위치 계산
def trilateration(distances, anchors):
    if None in distances:
        print("Error: Some distances are missing.")
        return None, None

    x1, y1 = anchors[0]
    x2, y2 = anchors[1]
    x3, y3 = anchors[2]
    x4, y4 = anchors[3]

    d1, d2, d3, d4 = distances

    # 삼변측량을 위한 방정식 설정
    A = np.array([
        [2 * (x2 - x1), 2 * (y2 - y1)],
        [2 * (x3 - x2), 2 * (y3 - y2)],
        [2 * (x4 - x3), 2 * (y4 - y3)]
    ])
   
    b = np.array([
        d1**2 - d2**2 - x1**2 + x2**2 - y1**2 + y2**2,
        d2**2 - d3**2 - x2**2 + x3**2 - y2**2 + y3**2,
        d3**2 - d4**2 - x3**2 + x4**2 - y3**2 + y4**2
    ])

    try:
        # 최소 제곱법으로 위치 계산
        pos, residuals, rank, s = np.linalg.lstsq(A, b, rcond=None)
    except Exception as e:
        print(f"Error during trilateration: {e}")
        return None, None

    return pos[0], pos[1]


# MySQL 데이터베이스 연결
def connect_to_mysql():
    try:
        connection = mysql.connector.connect(
            host="192.168.0.176",       # MySQL 서버 주소 (예: localhost 또는 IP)
            user="root",       # MySQL 사용자 이름
            password="audwlsrh1004*",  # MySQL 비밀번호
            database="ParkingDB",    # 사용할 데이터베이스 이름
            charset='utf8mb4'
            # cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

# 주차 위치 정보 업데이트
def update_parking_location_in_db(car_number, parking_location):
    connection = connect_to_mysql()
    if connection is None:
        return  # MySQL 연결 실패시 종료

    cursor = connection.cursor()
   
    update_parking_location = f"P{parking_location}"
   
    try:
        # 주차넘버에 해당하는 id 값의 parking_location을 업데이트
        cursor.execute("""
            UPDATE parkingLog
            SET parking_location = %s
            WHERE id = %s
        """, (update_parking_location, car_number))

        connection.commit()
        print(f"parking location for ID {car_number} updated to {update_parking_location}.")
    except mysql.connector.Error as err:
        print(f"Error updating parking location in DB: {err}")
    finally:
        cursor.close()
        connection.close()
       
def update_drive_in_db(car_number, drive):
    connection = connect_to_mysql()
    if connection is None:
        return  # MySQL 연결 실패시 종료

    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE parkingLog
            SET drive = %s
            WHERE id = %s
        """, (drive, car_number))

        connection.commit()
        print(f"drive for ID {car_number} updated to {drive}.")
    except mysql.connector.Error as err:
        print(f"Error updating drive in DB: {err}")
    finally:
        cursor.close()
        connection.close()
   

# 연속된 동일 값 체크
def check_for_stable_parking_location(parking_location, last_parking_location, same_count):
    if parking_location == last_parking_location:
        same_count += 1
    else:
        same_count = 0  # 값이 다르면 카운트 초기화

    if same_count >= 5:  # 5번 연속 같은 값이면 업데이트
        return True, same_count
    else:
        return False, same_count

# 주차 공간 체크 함수
def check_parking_zone(x, y, parking_zones):
    for idx, zone in enumerate(parking_zones):
        xmin, xmax, ymin, ymax = zone
        if xmin <= x <= xmax and ymin <= y <= ymax:
            print(f"Position ({x:.2f}, {y:.2f}) is inside Parking Zone {idx+1}.")
            return idx+1  # 주차공간 번호
    print(f"Position ({x:.2f}, {y:.2f}) is not in any parking zone.")
    return None


# 주차 위치 확인 및 업데이트 함수
def update_parking_if_stable(parking_location, last_parking_location, same_count, car_number):
    # 위치가 안정되었을 때만 업데이트
    is_stable = False
    is_stable, same_count = check_for_stable_parking_location(parking_location, last_parking_location, same_count)
    if is_stable:
        # 주차 위치 업데이트
        update_parking_location_in_db(car_number, parking_location)
    last_parking_location = parking_location  # 마지막 주차 위치 갱신
    return last_parking_location, same_count


# 주차 공간에 대한 연속 값을 추적
def main():
    serial_port = '/dev/ttyUSB0'  # 자신의 환경에 맞게 수정
    last_parking_location = None
    parking_location = None
    same_count = 0  # 연속된 값의 수를 세는 변수
    car_number = '12가3456'  # 주차 넘버 (가령, '1'은 ID가 1인 차량)
    drive = 1
    #update_parking_location_in_db(car_number,'P8')
    #update_drive_in_db(car_number,0)
   
    try:
        ser = serial.Serial(serial_port, baudrate=115200, timeout=5)
       
        if not send_at_command(ser, "AT+switchdis=1\r\n"):
            print("Failed to receive 'OK' after 'AT+switchdis=1' command. Exiting.")
            return
        anchors = [(0, 0), (120, 0), (0, 90), (120, 90)]  # 4개의 앵커 좌표 추가
        parking_zones = [
            (20, 40, -10, 40),   # Parking Zone 1: 좌표 범위 (xmin, xmax, ymin, ymax)
            (40, 60, -10, 40),    # Parking Zone 2
            (60, 80, -10, 40),    # Parking Zone 3
            (80, 100, -10, 40),   # Parking Zone 4
            (100, 120, -10, 40),
            (30, 50, 50, 100),
            (50, 70, 50, 100),
            (70, 90, 50, 100),
            # 추가적인 주차 공간이 있다면 이곳에 추가
        ]

        # 데이터 읽기 및 처리
        while True:
            if GPIO.input(button) == GPIO.LOW:
                while GPIO.input(button) == GPIO.LOW:
                    time.sleep(0.01)
                if drive == 1:
                    GPIO.output(green_pin, GPIO.LOW)
                    drive = 0
                    is_stable = False
                    same_count = 0
                    # 주차 상태가 활성화된 경우
                    ser.flushInput()
                     # 주차 위치 계산 및 검사
                    while same_count < 5:
                        data = read_serial_data(ser)
                        print(data)
                        if data:
                            distance0, distance1, distance2, distance3 = extract_distances(data)
                            distances = [distance0*100, distance1*100, distance2*100, distance3*100]  # 거리 리스트 업데이트
                            if None not in distances:
                                x, y = trilateration(distances, anchors)  # 삼변측량
                                parking_location = check_parking_zone(x, y, parking_zones)  # 주차공간 확인
                               
                                if parking_location is not None:
                                    # 위치가 안정되었을 때만 DB 업데이트
                                    last_parking_location, same_count = update_parking_if_stable(parking_location, last_parking_location, same_count, car_number)
                        time.sleep(0.01)  # 체크 주기
                    update_drive_in_db(car_number,drive)
                else:
                    GPIO.output(green_pin, GPIO.HIGH)
                    drive = 1
                    update_drive_in_db(car_number,drive)

    except serial.SerialException as e:
        print(f"Serial error: {e}")

    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    main()
