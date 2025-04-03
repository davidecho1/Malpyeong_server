

import sqlite3

def init_db(db_path="models.db"):
    """
    DB 스키마 생성:
    1) model_info: 모델 정보 (user_id, model_name, 다운로드 시각, safetensors 경로, 상태, GPU 번호)
    2) conversation_eval: 평가/대화 기록 (모델명, 질문, 답변, 평가, 타임스탬프, 세션ID, evaluator_id)
    3) evaluator: 평가자 계정 정보 (id, name, password_hash)
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # model_info 테이블 생성
    cur.execute("DROP TABLE IF EXISTS model_info")
    cur.execute("""
        CREATE TABLE model_info (
            user_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            downloaded_at DATETIME,
            safetensors_path TEXT,
            role TEXT DEFAULT 'idle',
            gpu_id INTEGER
        )
    """)

    # conversation_eval 테이블 생성 (평가 기록)
    cur.execute("DROP TABLE IF EXISTS conversation_eval")
    cur.execute("""
        CREATE TABLE conversation_eval (
            a_model_name   TEXT NOT NULL,
            b_model_name   TEXT NOT NULL,
            prompt         TEXT,
            a_model_answer TEXT,
            b_model_answer TEXT,
            evaluation     INTEGER,
            timestamp      DATETIME,
            session_id     TEXT,
            evaluator_id   TEXT
        )
    """)

    # evaluator 테이블 생성 (평가자 계정 정보)
    cur.execute("DROP TABLE IF EXISTS user")
    cur.execute("""
        CREATE TABLE user (
            id            TEXT PRIMARY KEY,
            name          TEXT,
            password      TEXT
        )
    """)

    conn.commit()
    conn.close()
    print(f"[init_db] DB 초기화 완료: {db_path}")

if __name__ == "__main__":
    init_db("models.db")
