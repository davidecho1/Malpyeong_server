# main (1).py
from AI_API import app
from scheduler_day import start_scheduler

def main():
    # GPU → 포트 매핑: 예) gpu 0→5021, 1→5022, 2→5023, 3→5024
    GPU_PORT_MAP = {0: 5021, 1: 5022, 2: 5023, 3: 5024}
    
    # 팀 구성 CSV 파일 경로
    csv_config_path = "team_config.csv"
    
    # 스케줄러 시작 (실제 운영은 매일 자정 실행; 테스트 시에는 CSV의 날짜와 time_offset에 따라 JOB이 등록됨)
    start_scheduler(GPU_PORT_MAP, csv_config_path)
    
    # Flask API 서버 실행 (포트 5020)
    print("[main] Starting Flask API on port=5020...")
    app.run(host="0.0.0.0", port=5020, debug=False, use_reloader=False)

if __name__ == "__main__":
    main()
