#!/usr/bin/env python
# coding: utf-8

# In[1]:


import sqlite3
import subprocess
import os

DB_PATH = "models.db"

def get_model_path_by_role(user_id: str, role: str='serving') -> (str, int):
    """
    role='serving' or 'standby' 중 하나의 모델 path + gpu_id 반환
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT safetensors_path, gpu_id
        FROM model_info
        WHERE user_id=? AND role=?
        LIMIT 1
    """, (user_id, role))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise ValueError(f"{user_id}에 role={role}인 모델이 없음")
    path, gpu = row
    if gpu is None:
        gpu = 0
    return path, gpu

def restart_vllm_process(user_id: str, role: str='serving', default_port=8100):
    """
    1) pkill -f api_server
    2) DB에서 role='serving'(또는 standby) 모델 path+gpu_id
    3) vLLM 재실행
    """
    # kill 기존 프로세스
    subprocess.run(["pkill","-f","api_server"])

    # DB 조회
    model_path, gpu_id = get_model_path_by_role(user_id, role=role)

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)

    # 포트는 user_id/role에 따라 다르게 결정 가능
    # 여기서는 간단히 default_port
    cmd = [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", model_path,
        "--port", str(default_port)
    ]
    print(f"[restart_vllm_process] CMD: {cmd}")
    subprocess.Popen(cmd, env=env)
    print(f"[restart_vllm_process] vLLM 재시작: user_id={user_id}, role={role}, gpu={gpu_id}, port={default_port}")


# In[ ]:




