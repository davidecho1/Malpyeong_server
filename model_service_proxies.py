#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sqlite3
import datetime
from typing import Optional, Dict
from huggingface_hub import snapshot_download

DB_PATH = "models.db"

def download_repo_and_save_safetensors(hf_repo_id: str, proxies: Optional[Dict[str, str]] = None):
    """
    hf_repo_id 예: "KYMEKAdavide/mnist_safetensors"
    1) 입력값 "/" 기준으로 분리하여 team_name와 model_part 추출.
    2) snapshot_download(repo_id=hf_repo_id, proxies=proxies)로 모델 다운로드.
    3) 다운로드한 리포에서 첫 번째 .safetensors 파일 경로 추출.
    4) models 테이블에 (team_name, model_name, safetensors_path, model_state='idle', gpu_id=NULL)을 저장.
    """
    if "/" not in hf_repo_id:
        raise ValueError(f"hf_repo_id='{hf_repo_id}' must be in 'team/model' format.")
    team_name, model_part = hf_repo_id.split("/", 1)

    local_repo_path = snapshot_download(repo_id=hf_repo_id, proxies=proxies)
    print(f"[download_repo_and_save_safetensors] Downloaded '{hf_repo_id}' => {local_repo_path}")

    safetensors_files = []
    for root, dirs, files in os.walk(local_repo_path):
        for f in files:
            if f.endswith(".safetensors"):
                safetensors_files.append(os.path.join(root, f))
    if not safetensors_files:
        raise FileNotFoundError(f"리포 '{hf_repo_id}' 내에 .safetensors 파일이 없습니다.")
    safetensors_path = safetensors_files[0]
    file_name = os.path.basename(safetensors_path)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # 팀별로 기존 레코드 삭제
    cur.execute("DELETE FROM models WHERE team_name=?", (team_name,))
    downloaded_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO models (team_name, model_name, safetensors_path, model_state, gpu_id, downloaded_at, updated_at)
        VALUES (?, ?, ?, 'idle', NULL, ?, ?)
    """, (team_name, model_part, safetensors_path, downloaded_at, downloaded_at))
    conn.commit()
    conn.close()
    print(f"[download_repo_and_save_safetensors] DB updated => team_name={team_name}, model_name={model_part}, file={file_name}, model_state=idle")

def set_model_standby(team_name: str, gpu_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT model_id FROM models WHERE team_name=? LIMIT 1", (team_name,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"{team_name} 모델이 DB에 없음")
    model_id = row[0]
    cur.execute("""
        UPDATE models
        SET model_state='standby', gpu_id=?
        WHERE model_id=?
    """, (gpu_id, model_id))
    conn.commit()
    conn.close()
    print(f"[set_model_standby] team_name={team_name}, gpu={gpu_id}, model_state=standby")

def set_model_serving(team_name: str, gpu_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT model_id FROM models WHERE team_name=? LIMIT 1", (team_name,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"{team_name} 모델이 DB에 없음")
    model_id = row[0]
    cur.execute("""
        UPDATE models
        SET model_state='serving', gpu_id=?
        WHERE model_id=?
    """, (gpu_id, model_id))
    conn.commit()
    conn.close()
    print(f"[set_model_serving] team_name={team_name}, gpu={gpu_id}, model_state=serving")

def set_model_idle(team_name: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT model_id FROM models WHERE team_name=? LIMIT 1", (team_name,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"{team_name} 모델이 DB에 없음")
    model_id = row[0]
    cur.execute("""
        UPDATE models
        SET model_state='idle', gpu_id=NULL, updated_at=CURRENT_TIMESTAMP
        WHERE model_id=?
    """, (model_id,))
    conn.commit()
    conn.close()
    print(f"[set_model_idle] team_name={team_name}, model_state=idle")
