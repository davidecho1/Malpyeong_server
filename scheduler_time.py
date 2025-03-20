# scheduler.py

import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3

from model_service import set_model_standby, set_model_serving, set_model_idle
from vllm_control import restart_vllm_process

DB_PATH = "models.db"

# GPU→포트 매핑 (전역)
GPU_PORT_MAP = {}

# TEAM_CONFIG (전역) - daily_model_switch에서 참조
TEAM_CONFIG = {
    "serving": [],
    "standby": []
}

def daily_model_switch():
    """
    TEAM_CONFIG["serving"], TEAM_CONFIG["standby"]의 user/gpu대로
    1) serving->standby
    2) standby->serving
    3) 나머지 idle
    """
    global GPU_PORT_MAP, TEAM_CONFIG

    print("[daily_model_switch] Start:", datetime.datetime.now())

    # 1) 기존 serving -> standby
    for s in TEAM_CONFIG["serving"]:
        user_id = s["user_id"]
        gpu_id  = s["gpu"]
        port    = GPU_PORT_MAP[gpu_id]  # 매핑
        set_model_standby(user_id, gpu_id=gpu_id)
        restart_vllm_process(user_id, role='standby', default_port=port)
        print(f"[daily_model_switch] {user_id} => standby(gpu={gpu_id}, port={port})")

    # 2) 기존 standby -> serving
    for st in TEAM_CONFIG["standby"]:
        user_id = st["user_id"]
        gpu_id  = st["gpu"]
        port    = GPU_PORT_MAP[gpu_id]
        set_model_serving(user_id, gpu_id=gpu_id)
        restart_vllm_process(user_id, role='serving', default_port=port)
        print(f"[daily_model_switch] {user_id} => serving(gpu={gpu_id}, port={port})")

    # (만약 다음번 교체 때 swap을 쓸 거라면 여기서 swap 해도 됨
    # TEAM_CONFIG["serving"], TEAM_CONFIG["standby"] = TEAM_CONFIG["standby"], TEAM_CONFIG["serving"]
    # )

    # 3) 나머지 idle
    new_active_users = set()
    for s in TEAM_CONFIG["serving"]:
        new_active_users.add(s["user_id"])
    for st in TEAM_CONFIG["standby"]:
        new_active_users.add(st["user_id"])

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM model_info")
    rows = cur.fetchall()
    conn.close()

    for (uid,) in rows:
        if uid not in new_active_users:
            set_model_idle(uid)

    print("[daily_model_switch] End:", datetime.datetime.now())

def set_team_config_from_csv_row(row):
    """
    row: {
      'time_offset': '1',
      's1_user': 'KYMEKAdavide', 's1_gpu': '0',
      's2_user': 'davidecho97',  's2_gpu': '1',
      'st1_user': 'mx5nabcd',    'st1_gpu': '2',
      'st2_user': 'jammanbooboo','st2_gpu': '3'
    }
    """
    global TEAM_CONFIG
    s1_user = row["s1_user"]
    s1_gpu  = int(row["s1_gpu"])
    s2_user = row["s2_user"]
    s2_gpu  = int(row["s2_gpu"])
    st1_user = row["st1_user"]
    st1_gpu  = int(row["st1_gpu"])
    st2_user = row["st2_user"]
    st2_gpu  = int(row["st2_gpu"])

    TEAM_CONFIG = {
        "serving": [
            {"user_id": s1_user, "gpu": s1_gpu},
            {"user_id": s2_user, "gpu": s2_gpu}
        ],
        "standby": [
            {"user_id": st1_user, "gpu": st1_gpu},
            {"user_id": st2_user, "gpu": st2_gpu}
        ]
    }
    print(f"[set_team_config_from_csv_row] TEAM_CONFIG updated => {TEAM_CONFIG}")

def schedule_csv_row(row, run_time, scheduler):
    """
    row: csv 한줄
    run_time: 실행 시점
    scheduler: BackgroundScheduler
    """
    def job_func(r=row):
        # 1) TEAM_CONFIG 갱신
        set_team_config_from_csv_row(r)
        # 2) daily_model_switch
        daily_model_switch()

    scheduler.add_job(job_func, 'date', run_date=run_time)
    print(f"[schedule_csv_row] row={row}, run_time={run_time}")

def start_scheduler(gpu_port_map):
    """
    gpu_port_map 예: {0:5022,1:5023,2:5024,3:5025}
    """
    global GPU_PORT_MAP
    GPU_PORT_MAP = gpu_port_map

    sched = BackgroundScheduler()
    sched.start()

    print(f"[start_scheduler] GPU_PORT_MAP={GPU_PORT_MAP}")
    return sched
