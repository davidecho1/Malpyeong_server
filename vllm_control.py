#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psycopg2
import subprocess
import os
import sys
import time

DB_CONN_INFO = "dbname=malpyeong user=TeddySum password=!TeddySum host=192.168.242.203 port=5100"

def get_model_path_by_role(team_name: str, role: str='serving'):
    conn = psycopg2.connect(DB_CONN_INFO)
    cur = conn.cursor()
    cur.execute("""
        SELECT safetensors_path, gpu_id
        FROM models
        WHERE team_name = %s AND model_state = %s
        LIMIT 1
    """, (team_name, role))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise ValueError(f"No {role} model for team {team_name}.")
    path, gpu = row
    if gpu is None:
        gpu = 0
    return path, gpu

def restart_vllm_process(team_name: str, role: str='serving', default_port=5022):
    # 기존 vLLM 프로세스 종료
    subprocess.run(["pkill", "-f", "api_server"])
    # DB에서 모델 정보 조회
    model_path, gpu_id = get_model_path_by_role(team_name, role=role)
    python_exe = sys.executable
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
    cmd = [
        python_exe,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model", model_path,
        "--port", str(default_port),
        "--gpu-memory-utilization", "0.95"
    ]
    print(f"[restart_vllm_process] CMD: {cmd}")
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    time.sleep(2)
    rc = proc.poll()
    if rc is not None:
        out, err = proc.communicate()
        print(f"[restart_vllm_process] vLLM crashed. Return code={rc}")
        print("stdout:", out)
        print("stderr:", err)
    else:
        print(f"[restart_vllm_process] vLLM is running (pid={proc.pid}) on port {default_port}")
