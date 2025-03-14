#!/usr/bin/env python
# coding: utf-8

# In[1]:


from flask import Flask, request, jsonify
import sqlite3
import datetime

from model_service import (
    download_repo_and_save_safetensors,
    set_model_idle, set_model_standby, set_model_serving
)
from vllm_control import restart_vllm_process

app = Flask(__name__)

@app.route("/models/download", methods=["POST"])
def models_download():
    data = request.json
    user_id = data["user_id"]
    try:
        download_repo_and_save_safetensors(user_id)  # role='idle'
        return jsonify({"msg": f"Downloaded & set idle for user_id={user_id}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/models/standby", methods=["POST"])
def models_standby():
    """
    Body:
    {
      "user_id":"TeamA/testcnn",
      "gpu_id":0,
      "port":8100
    }
    -> set role='standby', then restart vLLM with role='standby'
    """
    data = request.json
    user_id = data["user_id"]
    gpu_id = data.get("gpu_id", 0)
    port = data.get("port", 8100)
    try:
        set_model_standby(user_id, gpu_id=gpu_id)
        restart_vllm_process(user_id, role='standby', default_port=port)
        return jsonify({"msg":f"{user_id} -> standby(gpu={gpu_id}), port={port}"}), 200
    except Exception as e:
        return jsonify({"error":str(e)}), 400

@app.route("/models/serve", methods=["POST"])
def models_serve():
    """
    Body:
    {
      "user_id":"TeamA/testcnn",
      "gpu_id":1,
      "port":8101
    }
    -> set role='serving', then restart vLLM with role='serving'
    """
    data = request.json
    user_id = data["user_id"]
    gpu_id = data.get("gpu_id", 0)
    port = data.get("port", 8100)
    try:
        set_model_serving(user_id, gpu_id=gpu_id)
        restart_vllm_process(user_id, role='serving', default_port=port)
        return jsonify({"msg":f"{user_id} -> serving(gpu={gpu_id}), port={port}"}), 200
    except Exception as e:
        return jsonify({"error":str(e)}), 400

@app.route("/models/idle", methods=["POST"])
def models_idle():
    """
    Body:
    {
      "user_id":"TeamA/testcnn"
    }
    -> set role='idle', gpu_id=NULL, no vLLM process
    """
    data = request.json
    user_id = data["user_id"]
    try:
        set_model_idle(user_id)
        return jsonify({"msg":f"{user_id} -> idle"}), 200
    except Exception as e:
        return jsonify({"error":str(e)}), 400

@app.route("/models/list", methods=["GET"])
def models_list():
    """
    GET /models/list
    -> DB 모든 모델 (role, gpu_id)
    """
    conn = sqlite3.connect("models.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, model_name, role, gpu_id, safetensors_path, downloaded_at
        FROM model_info
    """)
    rows = cur.fetchall()
    conn.close()

    results=[]
    for r in rows:
        results.append({
            "user_id":r[0],
            "model_name":r[1],
            "role":r[2],
            "gpu_id":r[3],
            "path":r[4],
            "downloaded_at":r[5]
        })
    return jsonify(results), 200

# 대화/평가 API 동일 (생략)...

if __name__=="__main__":
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)


# In[ ]:




