# web_dashboard_simple.py
from flask import Flask, jsonify, render_template_string
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import plotly.graph_objs as go
import plotly.utils
import json
import threading
import time

app = Flask(__name__)


class WebDashboard:
    def __init__(self, db_path='sensor_data.db'):
        self.db_path = db_path
        self.latest_data = {}

        # 启动数据更新线程
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()

    def _update_loop(self):
        """后台数据更新循环"""
        while True:
            try:
                conn = sqlite3.connect(self.db_path)
                query = '''
                    SELECT timestamp, temperature, humidity, pressure, voltage, signal_strength 
                    FROM sensor_data 
                    ORDER BY timestamp DESC 
                    LIMIT 100
                '''
                df = pd.read_sql_query(query, conn)
                conn.close()

                if not df.empty:
                    self.latest_data = {
                        'df': df,
                        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'count': len(df)
                    }

                time.sleep(5)  # 每5秒更新一次

            except Exception as e:
                print(f"Web数据更新错误: {e}")
                time.sleep(10)


dashboard = WebDashboard()

# HTML模板（内嵌在代码中）
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EC800X 传感器数据监控平台</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Arial', sans-serif;
        }

        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            background: rgba(255, 255, 255, 0.9);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            color: #333;
            font-size: 28px;
        }

        .status-bar {
            display: flex;
            gap: 20px;
            align-items: center;
        }

        .status-item {
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .status-label {
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }

        .status-value {
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
        }

        .status-online {
            color: #2ecc71;
        }

        .status-offline {
            color: #e74c3c;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .chart-card {
            background: rgba(255, 255, 255, 0.9);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            transition: transform 0.3s ease;
        }

        .chart-card:hover {
            transform: translateY(-5px);
        }

        .chart-title {
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 18px;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .chart-container {
            width: 100%;
            height: 400px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }

        .stat-card {
            background: rgba(255, 255, 255, 0.9);
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }

        .stat-title {
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }

        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }

        .refresh-btn {
            background: #3498db;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s ease;
        }

        .refresh-btn:hover {
            background: #2980b9;
        }

        .footer {
            text-align: center;
            color: white;
            margin-top: 30px;
            padding: 15px;
            font-size: 14px;
        }

        .device-selector {
            padding: 8px 15px;
            border-radius: 5px;
            border: 1px solid #ddd;
            font-size: 14px;
        }

        @media (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
            }
            .chart-container {
                height: 300px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>🌡️ EC800X 传感器数据监控平台</h1>
            <div class="status-bar">
                <div class="status-item">
                    <div class="status-label">最后更新</div>
                    <div class="status-value" id="last-update">--:--:--</div>
                </div>
                <div class="status-item">
                    <div class="status-label">数据点数</div>
                    <div class="status-value" id="data-count">0</div>
                </div>
                <div class="status-item">
                    <div class="status-label">设备状态</div>
                    <div class="status-value status-online" id="device-status">在线</div>
                </div>
                <button class="refresh-btn" onclick="loadData()">🔄 刷新数据</button>
            </div>
        </div>

        <!-- 统计卡片 -->
        <div class="stats-grid" id="stats-cards">
            <!-- 统计卡片将通过JavaScript动态加载 -->
        </div>

        <!-- 图表区域 -->
        <div class="dashboard-grid">
            <div class="chart-card">
                <div class="chart-title">📈 温度变化趋势</div>
                <div class="chart-container" id="temperature-chart"></div>
            </div>

            <div class="chart-card">
                <div class="chart-title">💧 湿度变化趋势</div>
                <div class="chart-container" id="humidity-chart"></div>
            </div>

            <div class="chart-card">
                <div class="chart-title">⚡ 电压变化趋势</div>
                <div class="chart-container" id="voltage-chart"></div>
            </div>

            <div class="chart-card">
                <div class="chart-title">📶 信号强度变化</div>
                <div class="chart-container" id="signal-chart"></div>
            </div>
        </div>

        <!-- 数据表格 -->
        <div class="chart-card">
            <div class="chart-title">📋 最新数据记录</div>
            <div id="data-table"></div>
        </div>
    </div>

    <!-- 页脚 -->
    <div class="footer">
        <p>EC800X 物联网监控系统 | 数据每5秒自动更新 | © 2024</p>
    </div>

    <script>
        // 全局变量
        let autoRefresh = true;
        let refreshInterval = 5000; // 5秒

        // 初始化加载数据
        document.addEventListener('DOMContentLoaded', function() {
            loadData();
            if (autoRefresh) {
                setInterval(loadData, refreshInterval);
            }
        });

        // 加载数据函数
        function loadData() {
            // 加载图表数据
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error:', data.error);
                        return;
                    }

                    // 更新状态栏
                    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                    document.getElementById('data-count').textContent = data.count;

                    // 更新图表
                    updateCharts(data.traces);

                    // 加载统计数据
                    loadStats();

                    // 加载表格数据
                    loadTableData();
                })
                .catch(error => {
                    console.error('获取数据失败:', error);
                    document.getElementById('device-status').textContent = '离线';
                    document.getElementById('device-status').className = 'status-value status-offline';
                });
        }

        // 更新图表
        function updateCharts(traces) {
            const charts = {
                'temperature-chart': traces[0] || {x: [], y: []},
                'humidity-chart': traces[1] || {x: [], y: []},
                'voltage-chart': traces[2] || {x: [], y: []}
            };

            Object.keys(charts).forEach(chartId => {
                const trace = charts[chartId];
                const layout = {
                    title: '',
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: {color: '#333'},
                    xaxis: {
                        title: '时间',
                        gridcolor: '#eee',
                        showgrid: true
                    },
                    yaxis: {
                        title: getYAxisTitle(chartId),
                        gridcolor: '#eee',
                        showgrid: true
                    },
                    margin: {l: 50, r: 30, t: 30, b: 50}
                };

                Plotly.react(chartId, [trace], layout);
            });

            // 信号强度图表（柱状图）
            if (traces.length > 0 && traces[0].x && traces[0].x.length > 0) {
                const signalTrace = {
                    x: traces[0].x,
                    y: traces[0].y.map(() => Math.floor(Math.random() * 30) + 10), // 模拟信号强度
                    type: 'bar',
                    name: '信号强度',
                    marker: {
                        color: 'rgb(158,202,225)',
                        opacity: 0.7
                    }
                };

                const layout = {
                    title: '',
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: {color: '#333'},
                    xaxis: {
                        title: '时间',
                        gridcolor: '#eee',
                        showgrid: true
                    },
                    yaxis: {
                        title: '强度',
                        gridcolor: '#eee',
                        showgrid: true,
                        range: [0, 35]
                    },
                    margin: {l: 50, r: 30, t: 30, b: 50}
                };

                Plotly.react('signal-chart', [signalTrace], layout);
            }
        }

        // 获取Y轴标题
        function getYAxisTitle(chartId) {
            const titles = {
                'temperature-chart': '温度 (°C)',
                'humidity-chart': '湿度 (%)',
                'voltage-chart': '电压 (V)'
            };
            return titles[chartId] || '数值';
        }

        // 加载统计数据
        function loadStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(stats => {
                    const statsContainer = document.getElementById('stats-cards');
                    let statsHTML = '';

                    // 温度统计
                    statsHTML += `
                        <div class="stat-card">
                            <div class="stat-title">🌡️ 温度统计</div>
                            <div class="stat-value">${stats.temperature?.avg?.toFixed(1) || '--'}°C</div>
                            <div style="font-size: 12px; color: #666; margin-top: 5px;">
                                范围: ${stats.temperature?.min?.toFixed(1) || '--'}°C ~ ${stats.temperature?.max?.toFixed(1) || '--'}°C
                            </div>
                        </div>
                    `;

                    // 湿度统计
                    statsHTML += `
                        <div class="stat-card">
                            <div class="stat-title">💧 湿度统计</div>
                            <div class="stat-value">${stats.humidity?.avg?.toFixed(1) || '--'}%</div>
                            <div style="font-size: 12px; color: #666; margin-top: 5px;">
                                范围: ${stats.humidity?.min?.toFixed(1) || '--'}% ~ ${stats.humidity?.max?.toFixed(1) || '--'}%
                            </div>
                        </div>
                    `;

                    // 电压统计
                    statsHTML += `
                        <div class="stat-card">
                            <div class="stat-title">⚡ 电压统计</div>
                            <div class="stat-value">${stats.voltage?.avg?.toFixed(2) || '--'}V</div>
                            <div style="font-size: 12px; color: #666; margin-top: 5px;">
                                范围: ${stats.voltage?.min?.toFixed(2) || '--'}V ~ ${stats.voltage?.max?.toFixed(2) || '--'}V
                            </div>
                        </div>
                    `;

                    // 数据时间范围
                    statsHTML += `
                        <div class="stat-card">
                            <div class="stat-title">⏰ 数据监控</div>
                            <div class="stat-value" id="time-range">实时</div>
                            <div style="font-size: 12px; color: #666; margin-top: 5px;">
                                数据自动更新中
                            </div>
                        </div>
                    `;

                    statsContainer.innerHTML = statsHTML;
                })
                .catch(error => {
                    console.error('获取统计失败:', error);
                });
        }

        // 加载表格数据
        function loadTableData() {
            // 这里可以添加表格数据的加载
            // 为了简单，我们先显示当前时间
            document.getElementById('data-table').innerHTML = `
                <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                    <thead>
                        <tr style="background: #f8f9fa;">
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">时间</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">温度</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">湿度</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">电压</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">${new Date().toLocaleTimeString()}</td>
                            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">-- °C</td>
                            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">-- %</td>
                            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">-- V</td>
                        </tr>
                    </tbody>
                </table>
                <p style="text-align: center; color: #666; margin-top: 10px;">
                    数据正在加载中...
                </p>
            `;
        }

        // 切换自动刷新
        function toggleAutoRefresh() {
            autoRefresh = !autoRefresh;
            const btn = document.querySelector('.refresh-btn');
            if (autoRefresh) {
                btn.innerHTML = '🔄 自动刷新中';
                btn.style.background = '#2ecc71';
            } else {
                btn.innerHTML = '▶️ 开始刷新';
                btn.style.background = '#3498db';
            }
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    """主页面 - 返回内嵌HTML"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/data')
def get_data():
    """获取最新数据API"""
    if not dashboard.latest_data:
        return jsonify({'error': 'No data available'})

    df = dashboard.latest_data['df']

    # 确保数据按时间排序
    df = df.sort_values('timestamp')

    # 创建图表数据
    traces = []

    # 温度数据
    if 'temperature' in df.columns:
        trace_temp = go.Scatter(
            x=df['timestamp'].tolist(),
            y=df['temperature'].tolist(),
            name='温度',
            mode='lines+markers',
            line=dict(color='#ff6b6b', width=2),
            marker=dict(size=6)
        )
        traces.append(trace_temp)

    # 湿度数据
    if 'humidity' in df.columns:
        trace_hum = go.Scatter(
            x=df['timestamp'].tolist(),
            y=df['humidity'].tolist(),
            name='湿度',
            mode='lines+markers',
            line=dict(color='#4ecdc4', width=2),
            marker=dict(size=6)
        )
        traces.append(trace_hum)

    # 电压数据
    if 'voltage' in df.columns:
        trace_volt = go.Scatter(
            x=df['timestamp'].tolist(),
            y=df['voltage'].tolist(),
            name='电压',
            mode='lines+markers',
            line=dict(color='#45b7d1', width=2),
            marker=dict(size=6)
        )
        traces.append(trace_volt)

    # 转换traces为JSON格式
    traces_json = []
    for trace in traces:
        trace_dict = trace.to_plotly_json()
        traces_json.append(trace_dict)

    return jsonify({
        'traces': traces_json,
        'last_update': dashboard.latest_data['last_update'],
        'count': dashboard.latest_data['count']
    })


@app.route('/api/stats')
def get_stats():
    """获取统计数据API"""
    if not dashboard.latest_data:
        return jsonify({'error': 'No data available'})

    df = dashboard.latest_data['df']

    stats = {}

    if 'temperature' in df.columns:
        stats['temperature'] = {
            'min': float(df['temperature'].min()),
            'max': float(df['temperature'].max()),
            'avg': float(df['temperature'].mean())
        }

    if 'humidity' in df.columns:
        stats['humidity'] = {
            'min': float(df['humidity'].min()),
            'max': float(df['humidity'].max()),
            'avg': float(df['humidity'].mean())
        }

    if 'voltage' in df.columns:
        stats['voltage'] = {
            'min': float(df['voltage'].min()),
            'max': float(df['voltage'].max()),
            'avg': float(df['voltage'].mean())
        }

    return jsonify(stats)


@app.route('/api/raw')
def get_raw_data():
    """获取原始数据API"""
    if not dashboard.latest_data:
        return jsonify({'error': 'No data available'})

    df = dashboard.latest_data['df']

    # 返回前10条数据
    data = df.head(10).to_dict('records')

    return jsonify({
        'data': data,
        'total': len(df),
        'last_update': dashboard.latest_data['last_update']
    })


if __name__ == '__main__':
    print("🌐 Web仪表盘启动: http://localhost:5000")
    print("📊 请打开浏览器访问: http://127.0.0.1:5000")
    print("🔄 数据每5秒自动更新")
    app.run(debug=True, host='0.0.0.0')