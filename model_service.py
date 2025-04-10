#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import datetime
import psycopg2
from huggingface_hub import snapshot_download

DB_CONN_INFO = "dbname=malpyeong user=TeddySum password=!TeddySum host=192.168.242.203 port=5100"

def download_repo_and_save_safetensors(hf_repo_id: str):
    """
    hf_repo_id 예: "KYMEKAdavide/mnist_safetensors"
    1) 입력값을 "/" 기준으로 분리하여 team_name와 model_name 추출
    2) snapshot_download()로 Hugging Face 리포 다운로드
    3) 다운로드한 리포에서 첫 번째 .safetensors 파일 경로 탐색
    4) models 테이블에 (team_name, model_name, safetensors_path 등) 삽입
       → 동일 team_name의 기존 레코드는 삭제하여 최신 모델만 유지
    """
    if "/" not in hf_repo_id:
        raise ValueError(f"hf_repo_id='{hf_repo_id}'는 'user/model' 형식이어야 합니다.")
    team_name, model_name = hf_repo_id.split("/", 1)

    local_repo_path = snapshot_download(repo_id=hf_repo_id)
    print(f"[download_repo_and_save_safetensors] Downloaded '{hf_repo_id}' → {local_repo_path}")

    safetensors_files = []
    for root, dirs, files in os.walk(local_repo_path):
        for f in files:
            if f.endswith(".safetensors"):
                safetensors_files.append(os.path.join(root, f))
    if not safetensors_files:
        raise FileNotFoundError(f"리포 '{hf_repo_id}' 내에 .safetensors 파일이 없습니다.")
    safetensors_path = safetensors_files[0]
    file_name = os.path.basename(safetensors_path)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = psycopg2.connect(DB_CONN_INFO)
        cur = conn.cursor()
        # 기존 team_name의 모델 삭제 (항상 최신 모델만 유지)
        cur.execute("DELETE FROM models WHERE team_name = %s", (team_name,))
        cur.execute("""
            INSERT INTO models (team_name, model_name, safetensors_path, model_state, downloaded_at, updated_at)
            VALUES (%s, %s, %s, 'idle', %s, %s)
        """, (team_name, model_name, safetensors_path, now_str, now_str))
        conn.commit()
        cur.close()
        conn.close()
        print(f"[download_repo_and_save_safetensors] DB updated → team_name={team_name}, model_name={model_name}, file={file_name}, state=idle")
    except Exception as e:
        raise RuntimeError(f"DB 저장 오류: {e}")

def set_model_standby(team_name: str, gpu_id: int):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = psycopg2.connect(DB_CONN_INFO)
        cur = conn.cursor()
        cur.execute("""
            UPDATE models
            SET model_state = 'standby', gpu_id = %s, updated_at = %s
            WHERE team_name = %s
        """, (gpu_id, now_str, team_name))
        conn.commit()
        cur.close()
        conn.close()
        print(f"[set_model_standby] team_name={team_name}, gpu={gpu_id}, state=standby")
    except Exception as e:
        raise RuntimeError(f"set_model_standby 오류: {e}")

def set_model_serving(team_name: str, gpu_id: int):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = psycopg2.connect(DB_CONN_INFO)
        cur = conn.cursor()
        cur.execute("""
            UPDATE models
            SET model_state = 'serving', gpu_id = %s, updated_at = %s
            WHERE team_name = %s
        """, (gpu_id, now_str, team_name))
        conn.commit()
        cur.close()
        conn.close()
        print(f"[set_model_serving] team_name={team_name}, gpu={gpu_id}, state=serving")
    except Exception as e:
        raise RuntimeError(f"set_model_serving 오류: {e}")

def set_model_idle(team_name: str):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = psycopg2.connect(DB_CONN_INFO)
        cur = conn.cursor()
        cur.execute("""
            UPDATE models
            SET model_state = 'idle', gpu_id = NULL, updated_at = %s
            WHERE team_name = %s
        """, (now_str, team_name))
        conn.commit()
        cur.close()
        conn.close()
        print(f"[set_model_idle] team_name={team_name}, state=idle")
    except Exception as e:
        raise RuntimeError(f"set_model_idle 오류: {e}")

if __name__ == "__main__":
    # 테스트: 모델 카드 예시 (Hugging Face repo 형식)
    test_repo = "KYMEKAdavide/mnist_safetensors"
    download_repo_and_save_safetensors(test_repo)
