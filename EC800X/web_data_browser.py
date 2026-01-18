# web_data_browser.py - Web数据浏览器
from flask import Flask, render_template_string, jsonify, request
import sqlite3
import pandas as pd
import json
from datetime import datetime, timedelta

app = Flask(__name__)

# HTML模板（内嵌）
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>数据库三层结构浏览器</title>
    <style>
        body { font-family: Arial; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .section { background: white; padding: 20px; margin-bottom: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h2 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
        .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: #e8f5e9; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #2e7d32; }
        .stat-label { font-size: 14px; color: #666; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th { background: #4CAF50; color: white; padding: 10px; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #ddd; }
        tr:hover { background: #f5f5f5; }
        .tab-container { display: flex; border-bottom: 2px solid #4CAF50; margin-bottom: 20px; }
        .tab { padding: 10px 20px; cursor: pointer; border: 1px solid #ddd; border-bottom: none; border-radius: 8px 8px 0 0; }
        .tab.active { background: #4CAF50; color: white; }
        .query-box { background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .query-btn { background: #2196F3; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; }
        .query-btn:hover { background: #0b7dda; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 三层表结构数据浏览器</h1>

        <div class="stats-grid" id="stats">
            <!-- 统计卡片动态加载 -->
        </div>

        <div class="tab-container">
            <div class="tab active" onclick="showTab('devices')">📱 设备表</div>
            <div class="tab" onclick="showTab('sensor_data')">📈 传感器数据</div>
            <div class="tab" onclick="showTab('commands')">🎯 设备命令</div>
            <div class="tab" onclick="showTab('queries')">🔍 高级查询</div>
        </div>

        <div class="section" id="devices-tab">
            <h2>设备信息表 (devices)</h2>
            <div id="devices-table">加载中...</div>
        </div>

        <div class="section" id="sensor_data-tab" style="display:none;">
            <h2>传感器数据表 (sensor_data)</h2>
            <div>
                <button onclick="loadSensorData('recent')">最近数据</button>
                <button onclick="loadSensorData('stats')">数据统计</button>
                <button onclick="loadSensorData('chart')">图表视图</button>
            </div>
            <div id="sensor-table">加载中...</div>
            <div id="sensor-chart" style="height: 300px;"></div>
        </div>

        <div class="section" id="commands-tab" style="display:none;">
            <h2>设备命令表 (device_commands)</h2>
            <div id="commands-table">加载中...</div>
        </div>

        <div class="section" id="queries-tab" style="display:none;">
            <h2>高级查询</h2>
            <div class="query-box">
                <h3>预定义查询</h3>
                <button onclick="runQuery('device_status')">设备状态查询</button>
                <button onclick="runQuery('temperature_range')">温度范围查询</button>
                <button onclick="runQuery('low_voltage')">低电压告警</button>
                <button onclick="runQuery('hourly_stats')">小时统计</button>
            </div>
            <div id="query-result"></div>
        </div>
    </div>

    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script>
        // 页面加载时获取统计数据
        fetch('/api/stats')
            .then(r => r.json())
            .then(stats => {
                document.getElementById('stats').innerHTML = `
                    <div class="stat-card">
                        <div class="stat-value">${stats.device_count}</div>
                        <div class="stat-label">总设备数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.data_count}</div>
                        <div class="stat-label">数据记录数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${stats.command_count}</div>
                        <div class="stat-label">总命令数</div>
                    </div>
                `;
            });

        // 加载设备表数据
        fetch('/api/devices')
            .then(r => r.json())
            .then(data => {
                let html = '<table>';
                html += '<tr><th>设备ID</th><th>设备名称</th><th>位置</th><th>状态</th><th>最后在线</th></tr>';
                data.forEach(device => {
                    const statusColor = device.status === 'online' ? 'green' : 'red';
                    html += `
                        <tr>
                            <td>${device.device_id}</td>
                            <td>${device.device_name}</td>
                            <td>${device.location}</td>
                            <td style="color:${statusColor}">${device.status}</td>
                            <td>${device.last_seen}</td>
                        </tr>
                    `;
                });
                html += '</table>';
                document.getElementById('devices-table').innerHTML = html;
            });

        function showTab(tabName) {
            // 更新标签
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            event.target.classList.add('active');

            // 显示对应内容
            ['devices', 'sensor_data', 'commands', 'queries'].forEach(name => {
                document.getElementById(name + '-tab').style.display = 
                    name === tabName ? 'block' : 'none';
            });
        }

        function loadSensorData(type) {
            fetch('/api/sensor_data?type=' + type)
                .then(r => r.json())
                .then(data => {
                    if (type === 'recent') {
                        let html = '<table>';
                        html += '<tr><th>时间</th><th>设备</th><th>温度</th><th>湿度</th><th>电压</th></tr>';
                        data.forEach(row => {
                            html += `
                                <tr>
                                    <td>${row.timestamp}</td>
                                    <td>${row.device_id}</td>
                                    <td>${row.temperature}</td>
                                    <td>${row.humidity}</td>
                                    <td>${row.voltage}</td>
                                </tr>
                            `;
                        });
                        html += '</table>';
                        document.getElementById('sensor-table').innerHTML = html;
                    } else if (type === 'chart') {
                        // 绘制图表
                        const trace = {
                            x: data.map(d => d.timestamp),
                            y: data.map(d => d.temperature),
                            type: 'scatter',
                            mode: 'lines+markers',
                            name: '温度'
                        };
                        Plotly.newPlot('sensor-chart', [trace]);
                    }
                });
        }

        function runQuery(queryType) {
            fetch('/api/query?type=' + queryType)
                .then(r => r.json())
                .then(data => {
                    document.getElementById('query-result').innerHTML = 
                        `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                });
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/stats')
def get_stats():
    conn = sqlite3.connect('sensor_data.db')
    cursor = conn.cursor()

    # 设备数
    cursor.execute("SELECT COUNT(*) FROM devices")
    device_count = cursor.fetchone()[0]

    # 数据记录数
    cursor.execute("SELECT COUNT(*) FROM sensor_data")
    data_count = cursor.fetchone()[0]

    # 命令数
    cursor.execute("SELECT COUNT(*) FROM device_commands")
    command_count = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        'device_count': device_count,
        'data_count': data_count,
        'command_count': command_count
    })


@app.route('/api/devices')
def get_devices():
    conn = sqlite3.connect('sensor_data.db')
    df = pd.read_sql_query("SELECT * FROM devices", conn)
    conn.close()
    return jsonify(df.to_dict('records'))


@app.route('/api/sensor_data')
def get_sensor_data():
    conn = sqlite3.connect('sensor_data.db')
    query_type = request.args.get('type', 'recent')

    if query_type == 'recent':
        df = pd.read_sql_query(
            "SELECT timestamp, device_id, temperature, humidity, voltage FROM sensor_data ORDER BY timestamp DESC LIMIT 20",
            conn
        )
    elif query_type == 'stats':
        df = pd.read_sql_query(
            "SELECT device_id, COUNT(*) as count, AVG(temperature) as avg_temp FROM sensor_data GROUP BY device_id",
            conn
        )

    conn.close()
    return jsonify(df.to_dict('records'))


@app.route('/api/commands')
def get_commands():
    conn = sqlite3.connect('sensor_data.db')
    df = pd.read_sql_query("SELECT * FROM device_commands ORDER BY created_at DESC", conn)
    conn.close()
    return jsonify(df.to_dict('records'))


@app.route('/api/query')
def run_query():
    conn = sqlite3.connect('sensor_data.db')
    query_type = request.args.get('type', 'device_status')

    queries = {
        'device_status': "SELECT device_id, status, last_seen FROM devices",
        'temperature_range': "SELECT * FROM sensor_data WHERE temperature > 25 OR temperature < 15",
        'low_voltage': "SELECT * FROM sensor_data WHERE voltage < 3.5",
        'hourly_stats': """
            SELECT 
                strftime('%Y-%m-%d %H:00', timestamp) as hour,
                COUNT(*) as count,
                AVG(temperature) as avg_temp
            FROM sensor_data 
            GROUP BY hour 
            ORDER BY hour DESC
            LIMIT 10
        """
    }

    df = pd.read_sql_query(queries.get(query_type, queries['device_status']), conn)
    conn.close()
    return jsonify(df.to_dict('records'))


if __name__ == '__main__':
    print("🌐 数据浏览器启动: http://localhost:5001")
    app.run(debug=True, port=5001)