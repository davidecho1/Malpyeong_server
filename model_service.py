import os
import sqlite3
import datetime
from huggingface_hub import snapshot_download

DB_PATH = "models.db"

def download_repo_and_save_safetensors(hf_repo_id: str):
    """
    hf_repo_id 예: "KYMEKAdavide/mnist_safetensors"
    1) split -> user_part="KYMEKAdavide", model_part="mnist_safetensors"
    2) snapshot_download(hf_repo_id)
    3) safetensors 파일 찾기
    4) DB에 (user_id=user_part, model_name=model_part) 저장
    """

    # 1) 파라미터 split
    if "/" not in hf_repo_id:
        raise ValueError(f"hf_repo_id='{hf_repo_id}' must be 'user/model' format.")
    user_part, model_part = hf_repo_id.split("/", 1)  # "KYMEKAdavide", "mnist_safetensors"

    # 2) 모델 다운로드
    local_repo_path = snapshot_download(repo_id=hf_repo_id)
    print(f"[download_repo_and_save_safetensors] Downloaded '{hf_repo_id}' => {local_repo_path}")

    # 3) safetensors 파일 찾기
    safetensors_files = []
    for root, dirs, files in os.walk(local_repo_path):
        for f in files:
            if f.endswith(".safetensors"):
                safetensors_files.append(os.path.join(root, f))
    if not safetensors_files:
        raise FileNotFoundError(f"리포 '{hf_repo_id}' 내에 .safetensors 파일이 없습니다.")

    safetensors_path = safetensors_files[0]
    file_name = os.path.basename(safetensors_path)

    # 4) DB 저장
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # user_part별로 1개만 유지
    cur.execute("DELETE FROM model_info WHERE user_id=?", (user_part,))

    downloaded_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO model_info
        (user_id, model_name, downloaded_at, safetensors_path, role, gpu_id)
        VALUES (?, ?, ?, ?, 'idle', NULL)
    """, (user_part, model_part, downloaded_at, safetensors_path))
    conn.commit()
    conn.close()

    print(f"[download_repo_and_save_safetensors] DB updated => user_id={user_part}, model_name={model_part}, file={file_name}, role=idle")
    
def set_model_standby(user_id: str, gpu_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT rowid FROM model_info WHERE user_id=? LIMIT 1", (user_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"{user_id} 모델이 DB에 없음")

    model_rowid = row[0]
    cur.execute("""
        UPDATE model_info
        SET role='standby', gpu_id=?
        WHERE rowid=?
    """, (gpu_id, model_rowid))
    conn.commit()
    conn.close()
    print(f"[set_model_standby] user_id={user_id}, gpu={gpu_id}, role=standby")

def set_model_serving(user_id: str, gpu_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT rowid FROM model_info WHERE user_id=? LIMIT 1", (user_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"{user_id} 모델이 DB에 없음")

    model_rowid = row[0]
    cur.execute("""
        UPDATE model_info
        SET role='serving', gpu_id=?
        WHERE rowid=?
    """, (gpu_id, model_rowid))
    conn.commit()
    conn.close()
    print(f"[set_model_serving] user_id={user_id}, gpu={gpu_id}, role=serving")

def set_model_idle(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
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
