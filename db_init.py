#!/usr/bin/env python
# coding: utf-8

# In[28]:


import sqlite3

def init_db(db_path="models.db"):
    """
    model_info 테이블:
      - user_id, model_name, downloaded_at, safetensors_path
      - role: 'idle' / 'standby' / 'serving'
      - gpu_id: 할당된 GPU 번호 (NULL이면 GPU 미할당)

    conversation_eval 테이블:
      - 평가/대화 기록
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1) model_info
    cur.execute("DROP TABLE IF EXISTS model_info")
    cur.execute("""
        CREATE TABLE model_info (
            user_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            downloaded_at DATETIME,
            safetensors_path TEXT,
            role TEXT DEFAULT 'idle',        -- 'idle' / 'standby' / 'serving'
            gpu_id INTEGER
        )
    """)

    # 2) conversation_eval
    cur.execute("DROP TABLE IF EXISTS conversation_eval")
    cur.execute("""
        CREATE TABLE conversation_eval (
            a_model_name TEXT NOT NULL,
            b_model_name TEXT NOT NULL,
            prompt TEXT,
            a_model_answer TEXT,
            b_model_answer TEXT,
            evaluation INTEGER,
            timestamp DATETIME,
            session_id TEXT
        )
    """)

    conn.commit()
    conn.close()
    print(f"[init_db] DB 초기화 완료: {db_path}")

if __name__ == "__main__":
    init_db("models.db")


# In[ ]:




