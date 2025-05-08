#!/usr/bin/env python3

from flask import Flask, send_from_directory, render_template, request
import threading
import serial
import time
import json
import mariadb

ser = serial.Serial('/dev/ttyACM0', 9600, timeout=3)

app = Flask(__name__)


# For debug environment, in prod use actual user with password and ENV
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '1234',
    'database': 'GARDENDB'
}

try:
    conn = mariadb.connect(**db_config)
    cursor = conn.cursor()
except Exception as e:
    print(e)
    exit(1)


def handle_serial():
    time.sleep(2)
    try:
        while True:
            line = ser.readline().decode('utf-8').strip()
            try:
                data = json.loads(line)
                m_type = data['type']
                if m_type == 2:
                    handle_data(data)
                elif m_type == 3 or m_type == 4:
                    print(data['message'])
            except Exception as e:
                print(f"error={e} data={line}")
                time.sleep(1)
    except Exception as e:
        print(e)
    finally:
        ser.close()


state = [False, False]
latest_water = "waiting for data"
latest_moistness = "waiting for data"


water_threshold = 15
moist_min_threshold = 30
moist_max_threshold = 60


def handle_data(data):
    print(f"\x1b[32m{data}\x1b[0m")

    # if soil than 30% moist, turn on water
    if data['data'][0] <= moist_min_threshold and not state[0]:
        state[0] = True
        ser.write("{\"type\": 0, \"state\": true }\n".encode('utf-8'))
    elif data['data'][0] >= moist_max_threshold and state[0]:
        state[0] = False
        ser.write("{\"type\": 0, \"state\": false }\n".encode('utf-8'))

    # if less than 15% water, turn on light
    if data['data'][1] <= water_threshold and not state[1]:
        state[1] = True
        ser.write("{\"type\": 1, \"state\": true }\n".encode('utf-8'))
    elif data['data'][1] >= water_threshold and state[1]:
        state[1] = False
        ser.write("{\"type\": 1, \"state\": false }\n".encode('utf-8'))

    global latest_water
    latest_water = data['data'][1]

    global latest_moistness
    latest_moistness = data['data'][0]
    insert_data(latest_moistness, latest_water)


counter = 60


def insert_data(moistness, water_level):
    # only store every minute
    global counter
    if counter >= 60:
        counter = 0
    else:
        counter += 1
        return
    cursor.execute(
        "INSERT INTO status (moistness, water_level) VALUES (?,?)",
        (moistness, water_level))
    conn.commit()


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/water_level', methods=['GET', 'POST'])
def api_water_level():
    global water_threshold
    if request.method == "POST":
        val = request.form.get('value')
        water_threshold = int(val)
        print(f"\x1b[33mNew Water Threshold {water_threshold}\x1b[0m")
        return str(latest_water)
    else:
        return str(latest_water)


@app.route('/api/moistness', methods=['GET', 'POST'])
def api_moistness():
    global moist_min_threshold
    global moist_max_threshold
    if request.method == "POST":
        val = request.form.get('value')
        if val is not None:
            moist_min_threshold = int(val)

        val = request.form.get('max-value')
        if val is not None:
            moist_max_threshold = int(val)

        print(f"\x1b[33mNew Moist Threshold [{
              moist_max_threshold}, {moist_min_threshold}]\x1b[0m")

        return str(latest_moistness)
    else:
        return str(latest_moistness)


@app.route('/api/table')
def api_table():
    cursor.execute(
        "SELECT time_stamp, moistness, water_level FROM status ORDER BY row_id DESC LIMIT 150")
    results = cursor.fetchall()

    return render_template('table.html', results=results)


def run_app():
    app.run(debug=True, host='0.0.0.0', port=8080)


if __name__ == '__main__':
    serial_thread = threading.Thread(target=handle_serial, daemon=True)
    serial_thread.start()

    app.run(debug=True)
