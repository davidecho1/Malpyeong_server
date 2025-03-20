# scheduler_day.py

import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3

from model_service import set_model_standby, set_model_serving, set_model_idle
from vllm_control import restart_vllm_process

DB_PATH = "models.db"

# 전역: TEAM_CONFIG만 둔다 (GPU_PORT_MAP은 main에서 인자로 받음)
TEAM_CONFIG = {
    "serving": [
        {"user_id": "KYMEKAdavide", "gpu": 0},
        {"user_id": "davidecho97",  "gpu": 1}
    ],
    "standby": [
        {"user_id": "mx5nabcd",     "gpu": 2},
        {"user_id": "jammanbooboo", "gpu": 3}
    ]
}

# GPU_PORT_MAP을 전역으로 저장할 변수 (start_scheduler에서 할당)
GPU_PORT_MAP = {}

def daily_model_switch():
    """
    매일 0시에 TEAM_CONFIG["serving"]→standby, TEAM_CONFIG["standby"]→serving
    나머지는 idle
    """
    global GPU_PORT_MAP, TEAM_CONFIG

    print("[daily_model_switch] Start:", datetime.datetime.now())

    # 1) 기존 serving -> standby
    for s in TEAM_CONFIG["serving"]:
        user_id = s["user_id"]
        gpu_id  = s["gpu"]
        port    = GPU_PORT_MAP[gpu_id]  # main에서 전달받은 매핑 사용
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

    # 3) 나머지 idle
    active_users = set()
    for s in TEAM_CONFIG["serving"]:
        active_users.add(s["user_id"])
    for st in TEAM_CONFIG["standby"]:
        active_users.add(st["user_id"])

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM model_info")
    rows = cur.fetchall()
    conn.close()

    for (uid,) in rows:
        if uid not in active_users:
            set_model_idle(uid)

    print("[daily_model_switch] End:", datetime.datetime.now())

def start_scheduler(gpu_port_map):
    """
    gpu_port_map: {0: 5021, 1: 5022, 2: 5023, 3: 5024} 등
    """
    global GPU_PORT_MAP
    GPU_PORT_MAP = gpu_port_map

    scheduler = BackgroundScheduler()

    # 매일 0시에 daily_model_switch
    scheduler.add_job(daily_model_switch, 'cron', hour=0, minute=0)

    scheduler.start()
    print(f"[start_scheduler] 스케줄러 시작 (매일 00:00), GPU_PORT_MAP={GPU_PORT_MAP}")

    return scheduler
