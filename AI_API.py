#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
import datetime
import psycopg2

from model_service import (
    download_repo_and_save_safetensors,
    set_model_idle,
    set_model_standby,
    set_model_serving
)
from vllm_control import restart_vllm_process

app = Flask(__name__)

# PostgreSQL 접속 정보 (DB 연결 함수로 관리)
DB_CONN_INFO = "dbname=malpyeong user=postgres password=!TeddySum host=127.0.0.1 port=5432"

def get_db_connection():
    return psycopg2.connect(DB_CONN_INFO)

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"msg": "pong"}), 200

# 모델 다운로드
@app.route("/models/download", methods=["POST"])
def models_download():
    data = request.json
    repo_id = data["user_id"]  # 예: "TeamA/testcnn"
    try:
        download_repo_and_save_safetensors(repo_id)
        return jsonify({"msg": f"Downloaded & idle: {repo_id}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 모델 스탠바이
@app.route("/models/standby", methods=["POST"])
def models_standby():
    data = request.json
    team_name = data["user_id"]  # 여기에 팀명을 사용 (예: "TeamA/testcnn")
    gpu_id = data.get("gpu_id", 0)
    port = data.get("port", 5021)
    try:
        set_model_standby(team_name, gpu_id=gpu_id)
        restart_vllm_process(team_name, role='standby', default_port=port)
        return jsonify({"msg": f"{team_name} → standby (gpu={gpu_id}, port={port})"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 모델 서빙
@app.route("/models/serve", methods=["POST"])
def models_serve():
    data = request.json
    team_name = data["user_id"]
    gpu_id = data.get("gpu_id", 0)
    port = data.get("port", 5022)
    try:
        set_model_serving(team_name, gpu_id=gpu_id)
        restart_vllm_process(team_name, role='serving', default_port=port)
        return jsonify({"msg": f"{team_name} → serving (gpu={gpu_id}, port={port})"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 모델 idle
@app.route("/models/idle", methods=["POST"])
def models_idle():
    data = request.json
    team_name = data["user_id"]
    try:
        set_model_idle(team_name)
        return jsonify({"msg": f"{team_name} → idle"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 모델 목록 조회
@app.route("/models/list", methods=["GET"])
def models_list():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT team_name, model_name, model_state, gpu_id, safetensors_path, downloaded_at, updated_at
            FROM models
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        results = []
        for r in rows:
            results.append({
                "team_name": r[0],
                "model_name": r[1],
                "state": r[2],
                "gpu_id": r[3],
                "safetensors_path": r[4],
                "downloaded_at": r[5].strftime("%Y-%m-%d %H:%M:%S") if r[5] else None,
                "updated_at": r[6].strftime("%Y-%m-%d %H:%M:%S") if r[6] else None
            })
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 현재 서빙 모델 조회
@app.route("/models/current", methods=["GET"])
def models_current():
    team_name = request.args.get("user_id", None)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if team_name:
            cur.execute("""
                SELECT model_name, safetensors_path, gpu_id
                FROM models
                WHERE team_name = %s AND model_state = 'serving'
                LIMIT 1
            """, (team_name,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if not row:
                return jsonify({"msg": f"No serving model for {team_name}"}), 200
            return jsonify({
                "team_name": team_name,
                "model_name": row[0],
                "safetensors_path": row[1],
                "gpu_id": row[2]
            }), 200
        else:
            cur.execute("""
                SELECT team_name, model_name, safetensors_path, gpu_id
                FROM models
                WHERE model_state = 'serving'
            """)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            results = []
            for r in rows:
                results.append({
                    "team_name": r[0],
                    "model_name": r[1],
                    "safetensors_path": r[2],
                    "gpu_id": r[3]
                })
            return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 모델 스위치: 기존 serving → idle, 새 모델 → serving
@app.route("/models/switch", methods=["POST"])
def models_switch():
    data = request.json
    old_team = data["old_user_id"]
    new_team = data["new_user_id"]
    new_gpu_id = data.get("new_gpu_id", 0)
    new_port = data.get("new_port", 5021)
    try:
        set_model_idle(old_team)
        set_model_serving(new_team, gpu_id=new_gpu_id)
        restart_vllm_process(new_team, role='serving', default_port=new_port)
        return jsonify({"msg": f"Switched from {old_team} to {new_team}. {old_team} → idle, {new_team} → serving (gpu={new_gpu_id}, port={new_port})"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# 평과 데이터 제출 및 조회
@app.route("/eval/submit", methods=["POST"])
def eval_submit():
    """
    POST /eval/submit
    요청 예시:
    {
      "evaluator_id": "evaluser1",
      "a_model_name": "some_model.safetensors",
      "b_model_name": "other_model.safetensors",
      "prompt": "질문(프롬프트)",
      "a_model_answer": "A 모델 답변",
      "b_model_answer": "B 모델 답변",
      "evaluation": 1,    // 예: 1: A 우수, 2: B 우수, 3: 둘 다 좋음, 4: 둘 다 별로
      "session_id": "abcd1234"  // 선택사항
    }
    - 평가 데이터를 evaluations 테이블에 저장 (evaluator_id 포함)
    """
    data = request.json
    evaluator_id = data.get("evaluator_id")
    if not evaluator_id:
        return jsonify({"error": "evaluator_id가 필요합니다."}), 400

    a_model_name = data.get("a_model_name", "")
    b_model_name = data.get("b_model_name", "")
    prompt = data.get("prompt", "")
    a_model_answer = data.get("a_model_answer", "")
    b_model_answer = data.get("b_model_answer", "")
    evaluation = data.get("evaluation", 0)
    session_id = data.get("session_id", "")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # 하위 쿼리로 models 테이블에서 해당 모델명에 대한 model_id를 조회
        cur.execute("""
            INSERT INTO evaluations
            (a_model_id, b_model_id, prompt, a_model_answer, b_model_answer,
             evaluation, timestamp, session_id, evaluator_id)
            VALUES (
                (SELECT model_id FROM models WHERE model_name = %s LIMIT 1),
                (SELECT model_id FROM models WHERE model_name = %s LIMIT 1),
                %s, %s, %s, %s, %s, %s, %s
            )
        """, (a_model_name, b_model_name, prompt, a_model_answer, b_model_answer,
              evaluation, timestamp, session_id, evaluator_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"msg": "evaluation saved"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/eval/list", methods=["GET"])
def eval_list():
    session_id = request.args.get("session_id", None)
    model_name = request.args.get("model_name", None)
    query = """
        SELECT a_model_name, b_model_name, prompt,
               a_model_answer, b_model_answer,
               evaluation, timestamp, session_id, evaluator_id
        FROM evaluations
    """
    conditions = []
    params = []
    if session_id:
        conditions.append("session_id = %s")
        params.append(session_id)
    if model_name:
        conditions.append("(a_model_name = %s OR b_model_name = %s)")
        params.extend([model_name, model_name])
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        cur.close()
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
                "timestamp": r[6].strftime("%Y-%m-%d %H:%M:%S") if r[6] else None,
                "session_id": r[7],
                "evaluator_id": r[8]
            })
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5020, debug=False, use_reloader=False)
