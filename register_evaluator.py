
import sqlite3

DB_PATH = "evaluator.db"

def register_evaluator(evaluator_id: str, name: str, password: str):
    """
    평가자를 등록합니다.
    - evaluator_id: 평가자 고유 ID (예: "evaluser1")
    - name: 평가자 이름 (예: "Evaluator One")
    - password: 평문 비밀번호 (예: "secret123")
    평문으로 비밀번호를 저장합니다.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 이미 등록되어 있는지 확인
    cur.execute("SELECT * FROM evaluator WHERE id=?", (evaluator_id,))
    if cur.fetchone():
        print(f"평가자 '{evaluator_id}'는 이미 등록되어 있습니다.")
        conn.close()
        return
    
    # 비밀번호 저장
    cur.execute("INSERT INTO evaluator (id, name, password_hash) VALUES (?, ?, ?)",
                (evaluator_id, name, password))
    conn.commit()
    conn.close()
    print(f"평가자 '{evaluator_id}'가 성공적으로 등록되었습니다.")

if __name__ == "__main__":
    # 예시: evaluator_id: "evaluser1", password: "secret123"
    register_evaluator("evaluser1", "Evaluator One", "secret123")
