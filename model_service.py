#!/usr/bin/env python
# coding: utf-8

# In[17]:


import os
import sqlite3
import datetime
from huggingface_hub import snapshot_download

DB_PATH = "models.db"

def download_repo_and_save_safetensors(user_id: str):
    """
    1) 전체 리포 다운로드
    2) 첫 번째 .safetensors 찾아서 DB에 저장 (유저당 1개)
    3) 초기 role='idle', gpu_id=NULL
    """
    local_repo_path = snapshot_download(repo_id=user_id)
    print(f"[download_repo_and_save_safetensors] Downloaded repo => {local_repo_path}")

    # safetensors 찾기
    safetensors_files = []
    for root, dirs, files in os.walk(local_repo_path):
        for f in files:
            if f.endswith(".safetensors"):
                safetensors_files.append(os.path.join(root, f))

    if not safetensors_files:
        raise FileNotFoundError(f"{user_id} 리포에 .safetensors 파일이 없음")

    safetensors_path = safetensors_files[0]
    file_name = os.path.basename(safetensors_path)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 유저당 1개만 => 기존 레코드 삭제
    cur.execute("DELETE FROM model_info WHERE user_id=?", (user_id,))

    downloaded_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO model_info
        (user_id, model_name, downloaded_at, safetensors_path, role, gpu_id)
        VALUES (?, ?, ?, ?, 'idle', NULL)
    """, (user_id, file_name, downloaded_at, safetensors_path))
    conn.commit()
    conn.close()

    print(f"[download_repo_and_save_safetensors] user_id={user_id}, file={file_name}, role=idle")


def set_model_standby(user_id: str, gpu_id: int):
    """
    user_id 모델 -> role='standby', gpu_id=...
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 유저당 1개 => rowid 찾기
    cur.execute("SELECT rowid FROM model_info WHERE user_id=? LIMIT 1", (user_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"{user_id} 모델이 DB에 없음")

    model_rowid = row[0]
    # role='standby', gpu_id
    cur.execute("""
        UPDATE model_info
        SET role='standby', gpu_id=?
        WHERE rowid=?
    """, (gpu_id, model_rowid))
    conn.commit()
    conn.close()

    print(f"[set_model_standby] user_id={user_id}, role=standby, gpu_id={gpu_id}")


def set_model_serving(user_id: str, gpu_id: int):
    """
    user_id 모델 -> role='serving', gpu_id=...
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 유저당 1개 => rowid 찾기
    cur.execute("SELECT rowid FROM model_info WHERE user_id=? LIMIT 1", (user_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"{user_id} 모델이 DB에 없음")

    model_rowid = row[0]
    # role='serving', gpu_id
    cur.execute("""
        UPDATE model_info
        SET role='serving', gpu_id=?
        WHERE rowid=?
    """, (gpu_id, model_rowid))
    conn.commit()
    conn.close()

    print(f"[set_model_serving] user_id={user_id}, role=serving, gpu_id={gpu_id}")


def set_model_idle(user_id: str):
    """
    user_id 모델 -> role='idle', gpu_id=NULL
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 유저당 1개 => rowid 찾기
    cur.execute("SELECT rowid FROM model_info WHERE user_id=? LIMIT 1", (user_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"{user_id} 모델이 DB에 없음")

    model_rowid = row[0]
    cur.execute("""
        UPDATE model_info
        SET role='idle', gpu_id=NULL
        WHERE rowid=?
    """, (model_rowid,))
    conn.commit()
    conn.close()

    print(f"[set_model_idle] user_id={user_id}, role=idle")


# In[ ]:




