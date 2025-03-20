import sqlite3
import subprocess
import os
import time
import sys

DB_PATH = "models.db"

def get_model_path_by_role(user_id: str, role: str='serving'):
    """
    DB에서 user_id + role인 레코드를 찾아
    (safetensors_path, gpu_id)를 반환
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
        raise ValueError(f"No {role} model for user_id={user_id} in DB.")
    path, gpu = row
    if gpu is None:
        gpu = 0
    return path, gpu

def restart_vllm_process(user_id: str, role: str='serving', default_port=5022):
    # 1) 기존 프로세스 kill
    subprocess.run(["pkill","-f","api_server"])

    # 2) DB에서 model_path, gpu_id 조회
    model_path, gpu_id = get_model_path_by_role(user_id, role=role)

    # 3) 현재 파이썬 실행파일 (sys.executable)
    python_exe = sys.executable

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)

    cmd = [
        python_exe,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model", model_path,
        "--port", str(default_port)
    ]
    print(f"[restart_vllm_process] CMD: {cmd}")

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # # 첫 번째 검사 (2초 뒤)
    # time.sleep(2)
    # rc = proc.poll()
    # if rc is not None:
    #     out, err = proc.communicate()
    #     print(f"[restart_vllm_process] vLLM crashed (early). Return code={rc}")
    #     print("stdout:", out)
    #     print("stderr:", err)
    # else:
    #     print(f"[restart_vllm_process] vLLM is running (pid={proc.pid}) on port={default_port} (after 2s)")