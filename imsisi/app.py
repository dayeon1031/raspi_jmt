from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import pymysql
from datetime import datetime
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)
app.secret_key = 'supersecretkey'  # 세션을 사용하기 위한 키 설정

# Flask 로그 설정
logging.basicConfig(level=logging.DEBUG)  # 로그 레벨 설정
app.logger.setLevel(logging.DEBUG)  # Flask 내부 로그 활성화

# 데이터베이스 연결 함수
def get_db_connection():
    return pymysql.connect(
        host='192.168.0.176',
        user='root',
        password='audwlsrh1004*',  # 실제 MySQL 비밀번호 입력
        db='ParkingDB',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
@app.route('/vehicle', methods=['GET', 'POST'])
def vehicle():
    if request.method == 'POST':
        vehicle_number = request.form['vehicle_number']
        session['vehicle_number'] = vehicle_number  # 세션에 차량 번호 저장

        # ParkingLog와 ParkingPreference 테이블에 id 삽입
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # ParkingLog의 id 컬럼에만 차량 번호 삽입
                cursor.execute("""
                    INSERT IGNORE INTO ParkingLog (id)
                    VALUES (%s)
                """, (vehicle_number,))
                # ParkingPreference의 id 컬럼에 차량 번호 삽입
                cursor.execute("""
                    INSERT IGNORE INTO ParkingPreference (id)
                    VALUES (%s)
                """, (vehicle_number,))
            conn.commit()
        finally:
            conn.close()

        return redirect(url_for('settings'))  # 선호 자리 설정 페이지로 이동

    return render_template('vehicle.html')

# 선호 자리 설정 페이지
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        near_exit = 1 if 'near_exit' in request.form else 0
        near_entrance = 1 if 'near_entrance' in request.form else 0
        nearest = 1 if 'nearest' in request.form else 0
        vehicle_number = session.get('vehicle_number', '')

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE ParkingPreference
                    SET near_exit = %s, near_entrance = %s, nearest = %s
                    WHERE id = %s
                """, (near_exit, near_entrance, nearest, vehicle_number))
            conn.commit()
        finally:
            conn.close()

        # 설정 저장 후 추천 페이지로 이동
        return redirect(url_for('recommendation'))

    return render_template('settings.html')

@app.route('/barrier', methods=['POST'])
def barrier():
    barrier_type = request.args.get('type')  # 'entry' 또는 'exit'
    vehicle_number = session.get('vehicle_number', None)  # 세션에서 차량 번호 가져오기

    if not vehicle_number:
        return jsonify({'message': '차량 번호가 필요합니다.'}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if barrier_type == 'entry':
                # id와 entry_time이 NULL이 아닌 경우 drive 값을 1로 설정
                sql = """
                UPDATE ParkingLog
                SET drive = 1
                WHERE id = %s AND entry_time IS NOT NULL
                """
                cursor.execute(sql, (vehicle_number,))
                conn.commit()

                if cursor.rowcount > 0:
                    return jsonify({'message': '입차 기록 완료', 'status': 'entry'})
                else:
                    return jsonify({'message': '입차 기록 실패. 차량 번호가 일치하지 않거나 entry_time이 없습니다.', 'status': 'error'})

            elif barrier_type == 'exit':
                # 출차 시 drive 값을 NULL로 설정
                sql = """
                UPDATE ParkingLog
                SET drive = NULL
                WHERE id = %s
                """
                cursor.execute(sql, (vehicle_number,))
                conn.commit()

                if cursor.rowcount > 0:
                    return jsonify({'message': '출차 기록 완료', 'status': 'exit'})
                else:
                    return jsonify({'message': '출차 기록 실패. 차량 번호가 일치하지 않습니다.', 'status': 'error'})
    finally:
        conn.close()

    return jsonify({'message': '잘못된 요청입니다.'}), 400
# 추천 위치 페이지
# 추천 위치 페이지
@app.route('/recommendation', methods=['GET'])
def recommendation():
    vehicle_number = session.get('vehicle_number', None)

    if not vehicle_number:
        return redirect(url_for('vehicle'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # entry_time 확인
            cursor.execute("""
                SELECT entry_time
                FROM ParkingLog
                WHERE id = %s
                LIMIT 1
            """, (vehicle_number,))
            log = cursor.fetchone()

            # entry_time이 없으면 추천 위치 표시하지 않음
            if not log or not log['entry_time']:
                app.logger.debug(f"No entry_time for vehicle {vehicle_number}")
                return render_template(
                    'recommendation.html',
                    parking_location=None,
                    parking_spot="추천 가능한 자리가 없습니다."
                )

            # 선호도 가져오기
            cursor.execute("""
                SELECT near_exit, near_entrance, nearest
                FROM ParkingPreference
                WHERE id = %s
            """, (vehicle_number,))
            preference = cursor.fetchone()

            if not preference:
                app.logger.debug(f"No preference found for vehicle: {vehicle_number}")
                return render_template(
                    'recommendation.html',
                    parking_location=None,
                    parking_spot="추천 가능한 자리가 없습니다."
                )

            # 우선순위 설정
            if preference['nearest'] == 1:
                priority = [1, 6, 2, 7, 3, 8, 4, 5]
            elif preference['near_exit'] == 1:
                priority = [8, 5, 4, 7, 3, 2, 6, 1]
            elif preference['near_entrance'] == 1:
                priority = [6, 1, 7, 2, 3, 8, 4, 5]
            else:
                priority = []

            app.logger.debug(f"Priority list for vehicle {vehicle_number}: {priority}")

            # 추천 가능한 자리 찾기
            recommended_slot = None
            for slot in priority:
                cursor.execute("""
                    SELECT slot_number
                    FROM ParkingSlot
                    WHERE slot_number = %s AND occupied = 0
                """, (slot,))
                available_slot = cursor.fetchone()
                app.logger.debug(f"Checking slot {slot}: Result {available_slot}")
                if available_slot:
                    recommended_slot = f"P{available_slot['slot_number']}"  # "P"로 포맷팅
                    break

            if recommended_slot is not None:
                app.logger.debug(f"Recommended slot for vehicle {vehicle_number}: {recommended_slot}")
                cursor.execute("""
                    UPDATE ParkingLog
                    SET parking_location = %s, drive = 1
                    WHERE id = %s AND entry_time IS NOT NULL
                """, (recommended_slot, vehicle_number))
                conn.commit()
            else:
                app.logger.debug(f"No available slots for vehicle {vehicle_number}")
    finally:
        conn.close()

    parking_location = "현대백화점"
    parking_spot = recommended_slot if recommended_slot else "추천 가능한 자리가 없습니다."
    return render_template('recommendation.html', parking_location=parking_location, parking_spot=parking_spot)
@app.route('/check_drive', methods=['GET'])
def check_drive():
    vehicle_number = session.get('vehicle_number', None)

    if not vehicle_number:
        app.logger.debug("No vehicle_number in session.")
        return jsonify({'status': 'error', 'message': '차량 번호가 필요합니다.'}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT drive
                FROM ParkingLog
                WHERE id = %s
                LIMIT 1
            """, (vehicle_number,))
            result = cursor.fetchone()

            if result and result['drive'] is not None:
                app.logger.debug(f"Drive value for vehicle {vehicle_number}: {result['drive']}")
                return jsonify({'status': 'success', 'drive': result['drive']})
            else:
                app.logger.debug(f"No drive value for vehicle {vehicle_number}.")
                return jsonify({'status': 'error', 'message': 'drive 값이 없습니다.'})
    finally:
        conn.close()



@app.route('/parking', methods=['GET'])
def parking():
    vehicle_number = session.get('vehicle_number', None)

    if not vehicle_number:
        return redirect(url_for('vehicle'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 주차 위치 및 상태 확인
            cursor.execute("""
                SELECT parking_location, drive
                FROM ParkingLog
                WHERE id = %s
                ORDER BY entry_time DESC
                LIMIT 1
            """, (vehicle_number,))
            record = cursor.fetchone()

            if record:
                parking_location = "현대백화점"
                parking_spot = record['parking_location'] if record['parking_location'] else None
                app.logger.debug(f"Parking location for vehicle {vehicle_number}: {parking_spot}")
            else:
                parking_location = None
                parking_spot = None
    finally:
        conn.close()

    return render_template('parking.html', parking_location=parking_location, parking_spot=parking_spot)


# 정산 페이지
@app.route('/payment', methods=['GET', 'POST'])
def payment():
    vehicle_number = session.get('vehicle_number', None)

    if not vehicle_number:
        return redirect(url_for('vehicle'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 정산 정보 가져오기
            cursor.execute("""
                SELECT entry_time, id, payment
                FROM ParkingLog
                WHERE id = %s AND entry_time IS NOT NULL
                ORDER BY entry_time DESC
                LIMIT 1
            """, (vehicle_number,))
            record = cursor.fetchone()

            if record:
                entry_time = record['entry_time']
                vehicle_id = record['id']
                payment_status = record['payment']
                current_time = datetime.now()

                # 요금 계산 (1분당 3000 원)
                total_minutes = (current_time - entry_time).total_seconds() / 60
                parking_fee = int(total_minutes) * 3000
            else:
                entry_time = None
                vehicle_id = None
                parking_fee = 0
                payment_status = 0
    finally:
        conn.close()

    if request.method == 'POST':
        # POST 요청 시 payment 값 업데이트
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE ParkingLog
                    SET payment = 1
                    WHERE id = %s AND entry_time IS NOT NULL
                """, (vehicle_number,))
                conn.commit()
            flash("정산 완료!", "success")
        finally:
            conn.close()

        return redirect(url_for('vehicle'))

    return render_template('payment.html', entry_time=entry_time, vehicle_id=vehicle_id, parking_fee=parking_fee, payment_status=payment_status)

# 지도 페이지
@app.route('/map', methods=['GET'])
def map_view():
    vehicle_number = session.get('vehicle_number', None)

    if not vehicle_number:
        return redirect(url_for('vehicle'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ParkingLog에서 주차 위치 확인
            cursor.execute("""
                SELECT parking_location
                FROM ParkingLog
                WHERE id = %s
                ORDER BY entry_time DESC
                LIMIT 1
            """, (vehicle_number,))
            record = cursor.fetchone()

            if record and record['parking_location']:
                parking_location = record['parking_location']
                app.logger.debug(f"Parking location for map: {parking_location}")
                # 주차 위치에 따라 이미지 경로 설정
                map_image = f"/static/park_p{parking_location[-1]}.png"
            else:
                parking_location = None
                map_image = "/static/park_image.png"  # 기본 이미지
    finally:
        conn.close()

    return render_template('map.html', map_image=map_image, parking_location=parking_location)

# 메인 페이지
@app.route('/')
def home():
    vehicle_number = session.get('vehicle_number', None)

    if not vehicle_number:
        return redirect(url_for('vehicle'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # ParkingLog에서 데이터 가져오기
            cursor.execute("""
                SELECT parking_location, drive, entry_time
                FROM ParkingLog
                WHERE id = %s
                ORDER BY entry_time DESC
                LIMIT 1
            """, (vehicle_number,))
            record = cursor.fetchone()

            if record:
                app.logger.debug(f"Record for vehicle {vehicle_number}: {record}")
            else:
                app.logger.debug(f"No record found for vehicle {vehicle_number}.")
    finally:
        conn.close()

    return render_template('index.html', record=record)



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
