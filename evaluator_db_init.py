

import sqlite3

def init_evaluator_db(db_path="evaluator.db"):
    """
    evaluator 테이블:
      - id: 평가자 고유 ID (Primary Key)
      - name: 평가자 이름
      - password: 평문 비밀번호 (또는 해시값; 여기서는 평문으로 저장)
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS evaluator")
    cur.execute("""
        CREATE TABLE evaluator (
            id TEXT PRIMARY KEY,
            name TEXT,
            password TEXT
        )
    """)

    conn.commit()
    conn.close()
    print(f"[init_evaluator_db] DB 초기화 완료: {db_path}")

if __name__ == "__main__":
    init_evaluator_db()
