import subprocess
import time
import psycopg2

# PostgreSQL 접속 정보 (실제 환경에 맞게 수정하세요)
# 여기서는 호스트, 포트, 사용자, 비밀번호를 사용하여 'postgres' 데이터베이스에 연결합니다.
PG_HOST = "192.168.242.203"
PG_PORT = "5100"
PG_USER = "TeddySum"
PG_PASSWORD = "!TeddySum"

def is_postgresql_running():
    """PostgreSQL 서버에 접속이 가능한지 확인합니다."""
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=PG_USER,
            password=PG_PASSWORD,
            host=PG_HOST,
            port=PG_PORT
        )
        conn.close()
        return True
    except psycopg2.OperationalError:
        return False

def start_postgresql():
    """
    PostgreSQL 서비스를 systemctl을 통해 시작합니다.
    이 함수는 sudo 권한이 필요하며, 환경에 따라 서비스명이 다를 수 있습니다.
    """
    try:
        print("PostgreSQL 서버를 시작합니다...")
        subprocess.run(["sudo", "systemctl", "start", "postgresql"], check=True)
        # 서비스가 완전히 기동될 수 있도록 잠시 대기합니다.
        time.sleep(5)
    except Exception as e:
        print("PostgreSQL 서비스 시작에 실패했습니다:", e)

def create_database(dbname):
    """
    기본 'postgres' 데이터베이스에 연결하여 원하는 데이터베이스(dbname)를 생성합니다.
    이미 존재하면 메시지만 출력합니다.
    """
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=PG_USER,
            password=PG_PASSWORD,
            host=PG_HOST,
            port=PG_PORT
        )
        conn.autocommit = True  # 데이터베이스 생성은 autocommit 모드에서 처리해야 합니다.
        cur = conn.cursor()
        # 데이터베이스 존재 여부 확인
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
        if cur.fetchone():
            print(f"'{dbname}' 데이터베이스는 이미 존재합니다.")
        else:
            cur.execute(f"CREATE DATABASE {dbname};")
            print(f"'{dbname}' 데이터베이스가 성공적으로 생성되었습니다.")
        cur.close()
        conn.close()
    except Exception as e:
        print("데이터베이스 생성 중 오류 발생:", e)

if __name__ == "__main__":
    # PostgreSQL 실행 여부 확인
    if not is_postgresql_running():
        print("PostgreSQL 서버가 실행 중이 아닙니다. 시작을 시도합니다.")
        start_postgresql()

    # 다시 실행 여부 확인
    if is_postgresql_running():
        # 예시: 'malpyeong' 이름의 데이터베이스를 생성합니다.
        create_database("malpyeong")
    else:
        print("PostgreSQL 서버에 연결할 수 없습니다. DB 생성을 진행할 수 없습니다.")
