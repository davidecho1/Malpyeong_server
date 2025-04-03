
from AI_API import app
from scheduler_day import start_scheduler

def main():
    # GPU → 포트 매핑 (예: gpu 0->5021, 1->5022, 2->5023, 3->5024)
    GPU_PORT_MAP = {
        0: 5021,
        1: 5022,
        2: 5023,
        3: 5024
    }
    # 스케줄러 시작 (매일 0시에 실행)
    sched = start_scheduler(GPU_PORT_MAP)
    # Flask API 서버 실행 (포트 5020)
    print("[main] Starting Flask on port=5020...")
    app.run(host="0.0.0.0", port=5020, debug=False, use_reloader=False)

if __name__ == "__main__":
    main()
