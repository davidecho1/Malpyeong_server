from flask import Flask, request, jsonify
import sqlite3
import datetime

# model_service.py functions
from model_service import (
    download_repo_and_save_safetensors,
    set_model_idle,
    set_model_standby,
    set_model_serving
)

# vllm_control.py function
from vllm_control import restart_vllm_process

app = Flask(__name__)
DB_PATH = "models.db"

@app.route("/ping", methods=["GET"])
def ping():
    return {"msg":"pong"}, 200

# ---------------------------
# (1) 모델 다운로드
# ---------------------------
@app.route("/models/download", methods=["POST"])
def models_download():
    """
    POST /models/download
    Body: {"user_id":"TeamA/testcnn"}
    - Hugging Face 리포에서 safetensors 다운로드 -> DB에 role='idle' 기록
    """
    data = request.json
    user_id = data["user_id"]
    try:
        download_repo_and_save_safetensors(user_id)
        return jsonify({"msg": f"Downloaded & idle: {user_id}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------------------------
# (2) 모델 스탠바이 (단일)
# ---------------------------
@app.route("/models/standby", methods=["POST"])
def models_standby():
    """
    POST /models/standby
    Body:
    {
      "user_id":"TeamA/testcnn",
      "gpu_id":0,
      "port":5021
    }
    - role='standby'
    - vLLM 재시작 (standby)
    """
    data = request.json
    user_id = data["user_id"]
    gpu_id = data.get("gpu_id", 0)
    port = data.get("port", 5021)
    try:
        set_model_standby(user_id, gpu_id=gpu_id)
        restart_vllm_process(user_id, role='standby', default_port=port)
        return jsonify({"msg": f"{user_id} => standby(gpu={gpu_id}, port={port})"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------------------------
# (3) 모델 서빙 (단일)
# ---------------------------
@app.route("/models/serve", methods=["POST"])
def models_serve():
    """
    POST /models/serve
    Body:
    {
      "user_id":"TeamA/testcnn",
      "gpu_id":1,
      "port":5022
    }
    - role='serving'
    - vLLM 재시작 (serving)
    """
    data = request.json
    user_id = data["user_id"]
    gpu_id = data.get("gpu_id", 0)
    port = data.get("port", 5022)
    try:
        set_model_serving(user_id, gpu_id=gpu_id)
        restart_vllm_process(user_id, role='serving', default_port=port)
        return jsonify({"msg": f"{user_id} => serving(gpu={gpu_id}, port={port})"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------------------------
# (4) 모델 idle (단일)
# ---------------------------
@app.route("/models/idle", methods=["POST"])
def models_idle():
    """
    POST /models/idle
    Body: {"user_id":"TeamA/testcnn"}
    - role='idle'
    - GPU 해제(gpu_id=NULL)
    - vLLM 프로세스는 pkill (restart_vllm_process 내 pkill)
    """
    data = request.json
    user_id = data["user_id"]
    try:
        set_model_idle(user_id)
        return jsonify({"msg": f"{user_id} => idle"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------------------------
# (5) 모델 목록 조회
# ---------------------------
@app.route("/models/list", methods=["GET"])
def models_list():
    """
    GET /models/list
    - DB에 저장된 model_info 전체
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, model_name, role, gpu_id, safetensors_path, downloaded_at
        FROM model_info
    """)
    rows = cur.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "user_id": r[0],
            "model_name": r[1],
            "role": r[2],
            "gpu_id": r[3],
            "path": r[4],
            "downloaded_at": r[5]
        })
    return jsonify(results), 200


# ---------------------------
# (6) 현재 서빙 모델 조회
# ---------------------------
@app.route("/models/current", methods=["GET"])
def models_current():
    """
    GET /models/current?user_id=TeamA/testcnn
    - user_id가 있으면 해당 user_id + role='serving' 조회
    - 없으면 전체 role='serving' 조회
    """
    user_id = request.args.get("user_id", None)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if user_id:
        cur.execute("""
            SELECT model_name, safetensors_path, gpu_id
            FROM model_info
            WHERE user_id=? AND role='serving'
            LIMIT 1
        """, (user_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return jsonify({"msg": f"No serving model for {user_id}"}), 200
        return jsonify({
            "user_id": user_id,
            "model_name": row[0],
            "path": row[1],
            "gpu_id": row[2]
        }), 200
    else:
        cur.execute("""
            SELECT user_id, model_name, safetensors_path, gpu_id
            FROM model_info
            WHERE role='serving'
        """)
        rows = cur.fetchall()
        conn.close()
        results = []
        for r in rows:
            results.append({
                "user_id": r[0],
                "model_name": r[1],
                "path": r[2],
                "gpu_id": r[3]
            })
        return jsonify(results), 200


# ---------------------------
# (7) models/switch (이전 serving->idle, 새->serving)
# ---------------------------
@app.route("/models/switch", methods=["POST"])
def models_switch():
    """
    Body:
    {
      "old_user_id": "TeamA/testcnn_v1",
      "new_user_id": "TeamA/testcnn_v2",
      "new_gpu_id": 0,
      "new_port": 5021
    }
    - old_user_id => idle
    - new_user_id => serving
    - restart vLLM (serving)
    """
    data = request.json
    old_user_id = data["old_user_id"]
    new_user_id = data["new_user_id"]
    new_gpu_id = data.get("new_gpu_id", 0)
    new_port = data.get("new_port", 5021)

    try:
        # 1) 이전 serving -> idle
        set_model_idle(old_user_id)

        # 2) 새 모델 -> serving
        set_model_serving(new_user_id, gpu_id=new_gpu_id)

        # 3) vLLM 재시작
        restart_vllm_process(new_user_id, role='serving', default_port=new_port)

        return jsonify({
            "msg": f"Switched from {old_user_id} to {new_user_id}. "
                   f"{old_user_id} => idle, {new_user_id} => serving(gpu={new_gpu_id}, port={new_port})"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------------------------
# (8) models/standby_bulk (2개 이상 standby)
# ---------------------------
@app.route("/models/standby_bulk", methods=["POST"])
def models_standby_bulk():
    """
    Body:
    {
      "user_ids": ["TeamA/testcnn_v3", "TeamB/testcnn_v1"],
      "gpu_id": 0,
      "port": 5021
    }
    -> 여러 모델을 한 번에 standby
    -> 각각 vLLM 재시작(standby)
    """
    data = request.json
    user_ids = data["user_ids"]
    gpu_id = data.get("gpu_id", 0)
    port = data.get("port", 5021)

    results = []
    for uid in user_ids:
        try:
            set_model_standby(uid, gpu_id=gpu_id)
            restart_vllm_process(uid, role='standby', default_port=port)
            results.append(f"{uid} => standby(gpu={gpu_id}, port={port})")
        except Exception as e:
            results.append(f"Error for {uid}: {str(e)}")

    return jsonify({"results": results}), 200


@app.route("/eval/submit", methods=["POST"])
def eval_submit():
    """
    POST /eval/submit  
    Body 예시:
    {
      "evaluator_id": "evaluser1",
      "password": "secret123",
      "a_model_name": "some_model.safetensors",
      "b_model_name": "other_model.safetensors",
      "prompt": "질문(프롬프트)",
      "a_model_answer": "A 모델 답변",
      "b_model_answer": "B 모델 답변",
      "evaluation": 1,    // 1: A 우수, 2: B 우수, 3: 둘 다 좋음, 4: 둘 다 별로
      "session_id": "abcd1234"  // 선택사항
    }
    - evaluator 인증 후, 평가 데이터를 DB의 conversation_eval 테이블에 저장 (evaluator_id 포함)
    """
    data = request.json
    evaluator_id = data.get("evaluator_id")
    password = data.get("password")
    if not evaluator_id or not password:
        return jsonify({"error": "evaluator_id와 password가 필요합니다."}), 400

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM evaluator WHERE id=?", (evaluator_id,))
    row = cur.fetchone()
    if not row or not bcrypt.checkpw(password.encode('utf-8'), row[0].encode('utf-8')):
        conn.close()
        return jsonify({"error": "평가자 인증 실패"}), 401

    a_model_name   = data.get("a_model_name", "")
    b_model_name   = data.get("b_model_name", "")
    prompt         = data.get("prompt", "")
    a_model_answer = data.get("a_model_answer", "")
    b_model_answer = data.get("b_model_answer", "")
    evaluation     = data.get("evaluation", 0)
    session_id     = data.get("session_id", "")
    timestamp      = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cur.execute("""
        INSERT INTO conversation_eval
        (a_model_name, b_model_name, prompt, a_model_answer, b_model_answer,
         evaluation, timestamp, session_id, evaluator_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (a_model_name, b_model_name, prompt, a_model_answer, b_model_answer,
          evaluation, timestamp, session_id, evaluator_id))
    conn.commit()
    conn.close()
    return jsonify({"msg": "evaluation saved"}), 200


@app.route("/eval/list", methods=["GET"])
def eval_list():
    """
    GET /eval/list  
    Query Parameters:
      - session_id (선택)
      - model_name (선택; a_model_name 또는 b_model_name)
    - 조건에 맞는 평가 및 대화 기록을 반환함.
    """
    session_id = request.args.get("session_id", None)
    model_name = request.args.get("model_name", None)
    query = """
        SELECT a_model_name, b_model_name, prompt,
               a_model_answer, b_model_answer,
               evaluation, timestamp, session_id, evaluator_id
        FROM conversation_eval
    """
    conditions = []
    params = []
    if session_id:
        conditions.append("session_id = ?")
        params.append(session_id)
    if model_name:
        conditions.append("(a_model_name = ? OR b_model_name = ?)")
        params.append(model_name)
        params.append(model_name)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        results.append({
            "a_model_name": r[0],
            "b_model_name": r[1],
            "prompt": r[2],
            "a_model_answer": r[3],
            "b_model_answer": r[4],
            "evaluation": r[5],
            "timestamp": r[6],
            "session_id": r[7],
            "evaluator_id": r[8]
        })
    return jsonify(results), 200


# ---------------------------
# Flask 실행 (port=5020)
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5020, debug=False, use_reloader=False)
