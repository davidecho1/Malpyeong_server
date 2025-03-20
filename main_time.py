# main.py

import csv
import datetime
from datetime import timedelta

from AI_API import app
from scheduler_time import start_scheduler, schedule_csv_row

def main():
    # 1) GPU->포트 매핑
    GPU_PORT_MAP = {0:5021, 1:5022, 2:5023, 3:5024}

    # 2) 스케줄러 시작
    sched = start_scheduler(GPU_PORT_MAP)

    # 3) CSV 파싱
    with open("schedule(time).csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)  # time_offset,s1_user,s1_gpu,s2_user,s2_gpu,st1_user,st1_gpu,st2_user,st2_gpu
        rows = list(reader)

    now = datetime.datetime.now()

    # 4) 각 row를 'date' 트리거로 등록
    for row in rows:
        offset = int(row["time_offset"])
        run_time = now + timedelta(minutes=offset)
        schedule_csv_row(row, run_time, sched)

    # 5) Flask API (port=5020)
    print("[main] Flask API starting on port=5020...")
    app.run(host="0.0.0.0", port=5020, debug=False, use_reloader=False)

if __name__ == "__main__":
    main()
