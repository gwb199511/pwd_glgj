from flask import Flask, request, jsonify, render_template, send_file
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import random
import string
import os
from flask import current_app
import pytz
from pytz import timezone
import math

app = Flask(__name__)
app.config['TIMEZONE'] = timezone('Asia/Shanghai')

MAX_ATTEMPTS = 3
LOCKOUT_TIME = timedelta(minutes=3)
attempts = 0
lockout_end_time = None
attempt_timestamps = []

def get_db_connection():
    return mysql.connector.connect(
        host="192.168.2.8",
        user="root",
        password="123456",
        database="server_management"
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/servers', methods=['GET'])
def get_servers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM servers")
    servers = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(servers)

@app.route('/servers', methods=['POST'])
def add_server():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    try:
        cursor.execute("SELECT * FROM servers WHERE ip = %s", (data['ip'],))
        if cursor.fetchone():
            return jsonify({"message": "该服务器地址已存在，无法重复添加"}), 409

        query = "INSERT INTO servers (ip, username, password, purpose) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (data['ip'], data['username'], data['password'], data['purpose']))
        server_id = cursor.lastrowid

        log_query = "INSERT INTO operation_logs (operation_type, server_id, details) VALUES (%s, %s, %s)"
        cursor.execute(log_query, ('添加', server_id, f"添加了服务器 {data['ip']}"))

        conn.commit()
        return jsonify({"message": "服务器添加成功"}), 201
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({"message": f"添加服务器时发生错误: {err}"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/servers/<int:id>', methods=['PUT'])
def update_server(id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM servers WHERE id=%s", (id,))
    old_data = cursor.fetchone()

    query = "UPDATE servers SET ip=%s, username=%s, password=%s, purpose=%s WHERE id=%s"
    cursor.execute(query, (data['ip'], data['username'], data['new_password'], data['purpose'], id))
    conn.commit()

    changes = []
    if old_data['ip'] != data['ip']:
        changes.append(f"IP地址从 {old_data['ip']} 修改为 {data['ip']}")
    if old_data['username'] != data['username']:
        changes.append(f"用户名从 {old_data['username']} 修改为 {data['username']}")
    if old_data['password'] != data['new_password']:
        changes.append(f"密码从 {old_data['password']} 变更为 {data['new_password']}")
    if old_data['purpose'] != data['purpose']:
        changes.append(f"用途从 {old_data['purpose']} 修改为 {data['purpose']}")

    log_query = "INSERT INTO operation_logs (operation_type, server_id, details) VALUES (%s, %s, %s)"
    cursor.execute(log_query, ('修改', id, "; ".join(changes)))
    conn.commit()

    cursor.close()
    conn.close()
    return jsonify({"message": "服务器信息更新成功"})

@app.route('/verify_password', methods=['POST'])
def verify_password():
    global attempts, lockout_end_time, attempt_timestamps
    data = request.json
    password = data.get('password')
    current_time = datetime.now()

    attempt_timestamps = [timestamp for timestamp in attempt_timestamps if current_time - timestamp < timedelta(minutes=1)]

    if lockout_end_time and current_time < lockout_end_time:
        log_action('验证失败', '账户已锁定')
        return jsonify({"message": "账户已锁定，请稍后再试"}), 403

    if password == '1':
        attempts = 0
        attempt_timestamps = []
        log_action('验证成功', '密码验证成功，进入编辑模式')
        return jsonify({"message": "密码验证成功"}), 200
    else:
        attempts += 1
        attempt_timestamps.append(current_time)
        log_action('验证失败', '密码验证失败')
        if len(attempt_timestamps) >= MAX_ATTEMPTS:
            lockout_end_time = current_time + LOCKOUT_TIME
            log_action('验证失败', '密码错误次数过多，账户已锁定')
            return jsonify({"message": "密码错误次数过多，账户已锁定"}), 403
        return jsonify({"message": "密码错误"}), 401

@app.route('/check_ip', methods=['POST'])
def check_ip():
    data = request.json
    ip_address = data.get('ip_address')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id FROM servers WHERE ip=%s", (ip_address,))
    server = cursor.fetchone()

    cursor.close()
    conn.close()

    return jsonify({"exists": bool(server)}), 200 if server else 404

@app.route('/operation_logs', methods=['GET'])
def get_operation_logs():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT COUNT(*) as total FROM operation_logs")
        total = cursor.fetchone()['total']

        cursor.execute("SELECT * FROM operation_logs ORDER BY timestamp DESC LIMIT %s OFFSET %s", (per_page, offset))
        logs = cursor.fetchall()

        shanghai_tz = pytz.timezone('Asia/Shanghai')
        for log in logs:
            naive_time = log['timestamp']
            local_time = shanghai_tz.localize(naive_time)
            log['timestamp'] = local_time.strftime('%Y-%m-%d %H:%M:%S')

        response_data = {
            "logs": logs,
            "total": total,
            "current_page": page,
            "total_pages": math.ceil(total / per_page),
            "per_page": per_page
        }
        return jsonify(response_data)
    except Exception as e:
        return jsonify({"error": f"An error occurred while fetching logs: {str(e)}"}), 500
    finally:
        cursor.close()
        conn.close()

def log_action(operation_type, details):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO operation_logs (operation_type, details) VALUES (%s, %s)", (operation_type, details))
    conn.commit()
    cursor.close()
    conn.close()

def generate_random_password(length=32):
    characters = string.ascii_letters + string.digits + string.punctuation.replace('"', '')
    return ''.join(random.choice(characters) for _ in range(length))

@app.route('/generate_password', methods=['GET'])
def generate_password():
    return jsonify({"password": generate_random_password()})

@app.route('/random_background')
def random_background():
    image_dir = os.path.join(current_app.root_path, 'images')
    images = [f for f in os.listdir(image_dir) if f.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    if images:
        return send_file(os.path.join(image_dir, random.choice(images)), mimetype='image/png')
    return '', 404

if __name__ == '__main__':
    app.run(debug=False)