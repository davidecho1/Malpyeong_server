#!/usr/bin/env python
# coding: utf-8

# In[4]:


import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from model_service import (
    download_repo_and_save_safetensors,
    set_model_idle, set_model_standby, set_model_serving
)
from vllm_control import restart_vllm_process

# 예: user_id -> { "standby_gpu":0, "serving_gpu":1, "standby_port":8100, "serving_port":8101 }
TEAM_CONFIG = {
    "TeamA/testcnn": {
        "standby_gpu": 0, "standby_port": 8100,
        "serving_gpu": 1, "serving_port": 8101
    },
    # ...
}

def daily_model_update():
    print("[daily_model_update] Start:", datetime.datetime.now())
    for user_id, conf in TEAM_CONFIG.items():
        try:
            # 1) 새 모델 다운로드 -> idle
            download_repo_and_save_safetensors(user_id)
            # 2) standby에 로드
            set_model_standby(user_id, gpu_id=conf["standby_gpu"])
            # 3) vLLM 재시작(standby role)
            restart_vllm_process(user_id, role='standby', default_port=conf["standby_port"])
            print(f"  - {user_id} 새 모델 standby(gpu={conf['standby_gpu']})")

            # 예: 이전 serving -> idle
            set_model_idle(user_id)  # or set_model_standby -> idle, if we only have 1 model
            # or skip if we want 2 models, etc.

            # 4) serving -> standby 교체, etc. (원하는 로직)
            # set_model_serving(user_id, gpu_id=conf["serving_gpu"])
            # restart_vllm_process(user_id, role='serving', default_port=conf["serving_port"])

        except Exception as e:
            print(f"  - {user_id} 실패: {e}")
    print("[daily_model_update] End:", datetime.datetime.now())

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(daily_model_update, 'cron', hour=0, minute=0)
    scheduler.start()
    print("[start_scheduler] 스케줄러 시작 (매일 00:00)")


# In[ ]:




