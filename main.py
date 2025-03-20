# main.py

from AI_API import app
from scheduler_day import start_scheduler

def main():
    # 1) GPU->포트 매핑 (원하는 대로 설정)
    GPU_PORT_MAP = {
        0: 5021,
        1: 5022,
        2: 5023,
        3: 5024
    }

    # 2) 스케줄러 시작, 매일 0시에 교체
    sched = start_scheduler(GPU_PORT_MAP)

    # 3) Flask API on port=5020
    print("[main] Starting Flask on port=5020...")
    app.run(host="0.0.0.0", port=5020, debug=False, use_reloader=False)

if __name__ == "__main__":
    main()
