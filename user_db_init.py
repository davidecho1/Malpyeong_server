
import sqlite3

def init_user_db(db_path="user.db"):
    """
    user 테이블:
      - id: 사용자 고유 ID (Primary Key)
      - name: 사용자 이름
      - password: 평문 비밀번호 (또는 해시값; 여기서는 평문으로 저장)
      - email: 사용자 이메일 (선택 사항)
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS user")
    cur.execute("""
        CREATE TABLE user (
            id TEXT PRIMARY KEY,
            name TEXT,
            password TEXT,
            email TEXT
        )
    """)

    conn.commit()
    conn.close()
    print(f"[init_user_db] DB 초기화 완료: {db_path}")

if __name__ == "__main__":
    init_user_db()
