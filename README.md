# 🍓 raspi_jmt

**건국대학교 김다연 짱**  
🍓라즈베리 파이 존맛🍓  
_신난다 재미난다 라즈베리파이 ㅎ_  
_서브웨이 라즈베리파이쿠키 JMT_  
_내가만든 라즈베리파이 쿠키_  
_너를위해 구웠지(라즈비안OS)_  

---

## 📋 프로젝트 소개

**raspi_jmt**는 라즈베리 파이 프로젝트로, 특히 맛있는 코드와 재미있는 실습을 지향합니다.  

---

## 📚 참고 자료
- [라즈베리 파이 공식 문서](https://www.raspberrypi.org/documentation/)
- [Python GPIO 제어 가이드](https://source-gpio-control.com)

---

## 👩‍💻 기여자
- 김다연 (건국대학교)
- 김준수 (건국대학교)
- 송정윤 (건국대학교)

---

1. 차량 번호 입력 기능 (/vehicle)
이벤트: 사용자가 웹 페이지에서 차량 번호를 입력하면 POST 요청 발생.
SQL 테이블: ParkingLog, ParkingPreference
작업:
입력된 차량 번호를 session에 저장.
ParkingLog와 ParkingPreference 테이블에 해당 차량 번호(id 열)를 추가. (중복 방지를 위해 INSERT IGNORE 사용)

2. 선호 자리 설정 (/settings)
이벤트: 사용자가 주차 선호 옵션(출구 근처, 입구 근처, 가까운 자리)을 선택하고 제출.
SQL 테이블: ParkingPreference
작업:
POST 요청으로 전달된 선호 옵션(near_exit, near_entrance, nearest)을 ParkingPreference 테이블의 해당 id에 업데이트.
3. 입차 및 출차 처리 (/barrier)
이벤트: 차량이 입차 또는 출차할 때 차단기 제어 이벤트 발생.
SQL 테이블: ParkingLog
작업:
입차 (entry):
ParkingLog 테이블에서 차량 번호와 entry_time 값이 있는 경우, drive 값을 1로 설정.
성공 시 {"message": "입차 기록 완료", "status": "entry"} 반환.
출차 (exit):
ParkingLog 테이블에서 차량 번호에 대해 drive 값을 NULL로 설정.
성공 시 {"message": "출차 기록 완료", "status": "exit"} 반환.
4. 추천 위치 제공 (/recommendation)
이벤트: 사용자가 추천 주차 위치를 요청.
SQL 테이블: ParkingLog, ParkingSlot, ParkingPreference
작업:
ParkingLog 테이블에서 entry_time 확인. 없으면 추천 위치 제공 불가.
ParkingPreference 테이블에서 사용자의 선호도(near_exit, near_entrance, nearest)를 가져와 자리 우선순위 설정.
ParkingSlot 테이블에서 빈 자리(occupied = 0)를 검색하여 추천.
추천된 자리를 ParkingLog의 parking_location에 업데이트.
5. 주차 위치 확인 (/parking)
이벤트: 사용자가 현재 주차 위치 확인.
SQL 테이블: ParkingLog
작업:
ParkingLog 테이블에서 차량 번호에 대한 parking_location과 drive 값을 가져옴.
parking_location과 함께 사용자에게 반환.
6. 정산 처리 (/payment)
이벤트: 사용자가 정산 버튼 클릭.
SQL 테이블: ParkingLog
작업:
ParkingLog 테이블에서 차량 번호의 entry_time을 가져와 주차 시간을 계산.
정산 완료 시 payment 값을 1로 업데이트.
7. 지도 표시 (/map)
이벤트: 사용자가 주차 위치를 지도에 표시.
SQL 테이블: ParkingLog
작업:
ParkingLog 테이블에서 차량 번호의 parking_location 값을 가져옴.
parking_location 값을 바탕으로 적절한 이미지 경로 설정.
8. 메인 페이지 (/)
이벤트: 사용자가 웹 사이트 접속.
SQL 테이블: ParkingLog
작업:
ParkingLog 테이블에서 차량 번호의 최신 parking_location, drive, entry_time 값을 가져옴.
데이터에 따라 메인 페이지를 구성.
9. 번호판 인식 이벤트 (카메라 번호판 인식 코드)
이벤트: 카메라가 차량 번호 인식.
SQL 테이블: ParkingLog
작업:
인식된 번호판이 ParkingLog 테이블의 id와 일치하는지 확인.
payment 값이 1이면 아두이노에 신호 전송. 0이면 신호를 보내지 않음.
SQL 테이블 요약
ParkingLog:

id (차량 번호)
drive (움직임 상태: 1/0)
entry_time (입차 시간)
parking_location (추천된 주차 자리)
payment (정산 상태: 1/0)
ParkingPreference:

id (차량 번호)
near_exit (출구 근처 선호 여부)
near_entrance (입구 근처 선호 여부)
nearest (가까운 자리 선호 여부)
ParkingSlot:

slot_number (주차 자리 번호)
occupied (점유 여부: 1/0)
주요 흐름 요약
차량 번호 입력 → 선호 설정 → 입차 → 추천 자리 확인 → 주차 완료 → 정산 → 출차
각 단계에서 SQL 테이블과의 상호작용이 이루어지며, 상태에 따라 웹 페이지가 동적으로 변경됩니다.
