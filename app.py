import pymysql
from flask import Flask
import os
import pymysql

app = Flask(__name__)


def get_db_connection():
    return pymysql.connect(
        host=os.getenv('FROSTEL_MYSQL_HOST', 'mysql'),
        port=int(os.getenv('FROSTEL_MYSQL_PORT', 3306)),
        user=os.getenv('FROSTEL_MYSQL_USER'),
        password=os.getenv('FROSTEL_MYSQL_PASSWORD'),
        database=os.getenv('FROSTEL_MYSQL_DATABASE')
    )


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'



@app.route('/login')
def login():
    return 'login'


@app.route('/db-health')
def db_health():
    try:
        conn = get_db_connection()
        conn.close()
        return {"status": "health", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 500



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5555, debug=True)

