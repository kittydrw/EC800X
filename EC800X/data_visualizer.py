# data_visualizer.py
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import numpy as np
from matplotlib.font_manager import FontProperties


class SensorDataVisualizer:
    def __init__(self, db_path='sensor_data.db'):
        """初始化可视化工具"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)

        # 设置中文字体（如果需要）
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

    def load_sensor_data(self, device_id=None, hours=24):
        """加载传感器数据"""
        try:
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)

            query = '''
                SELECT 
                    timestamp,
                    temperature,
                    humidity,
                    pressure,
                    voltage,
                    signal_strength
                FROM sensor_data
                WHERE timestamp >= ?
            '''
            params = [start_time.isoformat()]

            if device_id:
                query += ' AND device_id = ?'
                params.append(device_id)

            query += ' ORDER BY timestamp'

            df = pd.read_sql_query(query, self.conn, params=params)

            # 转换时间格式
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)

            return df

        except Exception as e:
            print(f"❌ 加载数据失败: {e}")
            return pd.DataFrame()

    def create_realtime_dashboard(self, device_id='EC800X_Sensor_001'):
        """创建实时监控仪表盘"""
        df = self.load_sensor_data(device_id, hours=6)

        if df.empty:
            print("📭 没有找到数据")
            return

        # 创建子图
        fig, axes = plt.subplots(3, 2, figsize=(15, 12))
        fig.suptitle(f'📊 传感器实时监控 - {device_id}', fontsize=16, fontweight='bold')

        # 1. 温度曲线
        ax1 = axes[0, 0]
        ax1.plot(df.index, df['temperature'], 'r-', linewidth=2, marker='o', markersize=4)
        ax1.fill_between(df.index, df['temperature'], alpha=0.3, color='red')
        ax1.set_title('🌡️ 温度变化趋势', fontsize=12, fontweight='bold')
        ax1.set_ylabel('温度 (°C)')
        ax1.grid(True, alpha=0.3)

        # 添加温度统计信息
        avg_temp = df['temperature'].mean()
        max_temp = df['temperature'].max()
        min_temp = df['temperature'].min()
        ax1.text(0.02, 0.95, f'平均: {avg_temp:.1f}°C\n最高: {max_temp:.1f}°C\n最低: {min_temp:.1f}°C',
                 transform=ax1.transAxes, verticalalignment='top',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        # 2. 湿度曲线
        ax2 = axes[0, 1]
        ax2.plot(df.index, df['humidity'], 'b-', linewidth=2, marker='s', markersize=4)
        ax2.fill_between(df.index, df['humidity'], alpha=0.3, color='blue')
        ax2.set_title('💧 湿度变化趋势', fontsize=12, fontweight='bold')
        ax2.set_ylabel('湿度 (%)')
        ax2.grid(True, alpha=0.3)

        # 3. 气压曲线
        ax3 = axes[1, 0]
        ax3.plot(df.index, df['pressure'], 'g-', linewidth=2, marker='^', markersize=4)
        ax3.set_title('📈 气压变化趋势', fontsize=12, fontweight='bold')
        ax3.set_ylabel('气压 (hPa)')
        ax3.grid(True, alpha=0.3)

        # 4. 电压曲线
        ax4 = axes[1, 1]
        ax4.plot(df.index, df['voltage'], 'orange', linewidth=2, marker='d', markersize=4)
        ax4.set_title('🔋 电压变化趋势', fontsize=12, fontweight='bold')
        ax4.set_ylabel('电压 (V)')
        ax4.grid(True, alpha=0.3)

        # 添加电压警告线
        ax4.axhline(y=3.3, color='red', linestyle='--', alpha=0.5, label='低电压警告')
        ax4.legend()

        # 5. 信号强度
        ax5 = axes[2, 0]
        bars = ax5.bar(df.index, df['signal_strength'], color='purple', alpha=0.7)
        ax5.set_title('📡 信号强度', fontsize=12, fontweight='bold')
        ax5.set_ylabel('信号强度')
        ax5.set_xlabel('时间')
        ax5.grid(True, alpha=0.3)

        # 6. 数据统计面板
        ax6 = axes[2, 1]
        ax6.axis('off')

        # 计算统计数据
        stats_text = f"""
        设备ID: {device_id}
        数据时间范围: {df.index.min().strftime('%Y-%m-%d %H:%M')} 到 {df.index.max().strftime('%Y-%m-%d %H:%M')}
        数据点数: {len(df)}

        📊 统计信息:
        • 平均温度: {df['temperature'].mean():.2f}°C
        • 温度范围: {df['temperature'].min():.1f}°C ~ {df['temperature'].max():.1f}°C
        • 平均湿度: {df['humidity'].mean():.2f}%
        • 平均气压: {df['pressure'].mean():.2f}hPa
        • 平均电压: {df['voltage'].mean():.2f}V
        • 平均信号: {df['signal_strength'].mean():.1f}

        ⚡ 设备状态:
        • 最后更新: {df.index.max().strftime('%H:%M:%S')}
        • 数据间隔: {(df.index[-1] - df.index[-2]).seconds if len(df) > 1 else 0}秒
        """

        ax6.text(0.05, 0.95, stats_text, transform=ax6.transAxes,
                 verticalalignment='top', fontsize=10,
                 bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.5))

        # 调整布局
        plt.tight_layout()
        plt.subplots_adjust(top=0.93)

        # 保存图片
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"sensor_dashboard_{device_id}_{timestamp}.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"✅ 仪表盘已保存: {filename}")

        plt.show()

    def create_temperature_humidity_comparison(self):
        """创建温湿度对比图"""
        df = self.load_sensor_data()

        if df.empty:
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

        # 温湿度叠加图
        ax1.plot(df.index, df['temperature'], 'r-', label='温度', linewidth=2)
        ax1.set_ylabel('温度 (°C)', color='red')
        ax1.tick_params(axis='y', labelcolor='red')
        ax1.grid(True, alpha=0.3)

        ax1_twin = ax1.twinx()
        ax1_twin.plot(df.index, df['humidity'], 'b-', label='湿度', linewidth=2)
        ax1_twin.set_ylabel('湿度 (%)', color='blue')
        ax1_twin.tick_params(axis='y', labelcolor='blue')

        ax1.set_title('🌡️💧 温湿度变化对比', fontsize=14, fontweight='bold')
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax1_twin.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

        # 温湿度散点图
        ax2.scatter(df['temperature'], df['humidity'], c=df['temperature'],
                    cmap='coolwarm', s=50, alpha=0.6, edgecolors='black')
        ax2.set_xlabel('温度 (°C)')
        ax2.set_ylabel('湿度 (%)')
        ax2.set_title('温湿度相关性分析', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        # 添加趋势线
        z = np.polyfit(df['temperature'], df['humidity'], 1)
        p = np.poly1d(z)
        ax2.plot(df['temperature'], p(df['temperature']), "r--", alpha=0.8,
                 label=f'趋势线: y={z[0]:.2f}x+{z[1]:.2f}')
        ax2.legend()

        plt.tight_layout()
        plt.show()

    def create_historical_trend(self, days=7):
        """创建历史趋势图"""
        df = self.load_sensor_data(hours=days * 24)

        if df.empty:
            return

        # 按天重采样
        daily_df = df.resample('D').agg({
            'temperature': ['mean', 'max', 'min'],
            'humidity': 'mean',
            'pressure': 'mean'
        })

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # 1. 日均温度
        axes[0, 0].plot(daily_df.index, daily_df[('temperature', 'mean')],
                        'ro-', linewidth=2, label='日均温度')
        axes[0, 0].fill_between(daily_df.index,
                                daily_df[('temperature', 'min')],
                                daily_df[('temperature', 'max')],
                                alpha=0.2, color='red', label='温度范围')
        axes[0, 0].set_title('🌡️ 日平均温度变化', fontsize=12, fontweight='bold')
        axes[0, 0].set_ylabel('温度 (°C)')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # 2. 日均湿度
        axes[0, 1].bar(daily_df.index, daily_df[('humidity', 'mean')],
                       color='skyblue', alpha=0.7, width=0.5)
        axes[0, 1].set_title('💧 日平均湿度变化', fontsize=12, fontweight='bold')
        axes[0, 1].set_ylabel('湿度 (%)')
        axes[0, 1].grid(True, alpha=0.3)

        # 3. 气压变化
        axes[1, 0].plot(daily_df.index, daily_df[('pressure', 'mean')],
                        'g^-', linewidth=2)
        axes[1, 0].set_title('📈 日平均气压变化', fontsize=12, fontweight='bold')
        axes[1, 0].set_ylabel('气压 (hPa)')
        axes[1, 0].grid(True, alpha=0.3)

        # 4. 温湿度热力图（相关性矩阵）
        corr_matrix = df[['temperature', 'humidity', 'pressure', 'voltage']].corr()
        im = axes[1, 1].imshow(corr_matrix, cmap='coolwarm', vmin=-1, vmax=1)
        axes[1, 1].set_title('📊 参数相关性热力图', fontsize=12, fontweight='bold')

        # 设置刻度标签
        params = ['温度', '湿度', '气压', '电压']
        axes[1, 1].set_xticks(range(len(params)))
        axes[1, 1].set_yticks(range(len(params)))
        axes[1, 1].set_xticklabels(params)
        axes[1, 1].set_yticklabels(params)

        # 添加数值标签
        for i in range(len(params)):
            for j in range(len(params)):
                text = axes[1, 1].text(j, i, f'{corr_matrix.iloc[i, j]:.2f}',
                                       ha="center", va="center", color="black", fontsize=10)

        plt.colorbar(im, ax=axes[1, 1], fraction=0.046, pad=0.04)

        plt.tight_layout()
        plt.show()

    def create_export_report(self, device_id='EC800X_Sensor_001'):
        """生成数据报告（PDF或HTML）"""
        try:
            import jinja2
            from weasyprint import HTML

            df = self.load_sensor_data(device_id, hours=24)

            if df.empty:
                print("📭 没有数据可生成报告")
                return

            # 计算统计数据
            stats = {
                'device_id': device_id,
                'time_range': f"{df.index.min().strftime('%Y-%m-%d %H:%M')} 到 {df.index.max().strftime('%Y-%m-%d %H:%M')}",
                'total_points': len(df),
                'avg_temperature': f"{df['temperature'].mean():.2f}",
                'avg_humidity': f"{df['humidity'].mean():.2f}",
                'avg_pressure': f"{df['pressure'].mean():.2f}",
                'avg_voltage': f"{df['voltage'].mean():.2f}",
                'generated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # HTML模板
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>传感器数据报告 - {{ device_id }}</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
                    .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                    .stats-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                    .stats-table th, .stats-table td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                    .stats-table th { background-color: #f2f2f2; }
                    .footer { margin-top: 40px; text-align: center; color: #666; font-size: 12px; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>📊 传感器数据监测报告</h1>
                    <h2>设备: {{ device_id }}</h2>
                </div>

                <div class="section">
                    <h3>📅 报告概览</h3>
                    <table class="stats-table">
                        <tr><th>项目</th><th>数值</th></tr>
                        <tr><td>设备ID</td><td>{{ device_id }}</td></tr>
                        <tr><td>时间范围</td><td>{{ time_range }}</td></tr>
                        <tr><td>数据点数</td><td>{{ total_points }}</td></tr>
                        <tr><td>报告生成时间</td><td>{{ generated_time }}</td></tr>
                    </table>
                </div>

                <div class="section">
                    <h3>📈 统计数据</h3>
                    <table class="stats-table">
                        <tr><th>参数</th><th>平均值</th></tr>
                        <tr><td>温度</td><td>{{ avg_temperature }} °C</td></tr>
                        <tr><td>湿度</td><td>{{ avg_humidity }} %</td></tr>
                        <tr><td>气压</td><td>{{ avg_pressure }} hPa</td></tr>
                        <tr><td>电压</td><td>{{ avg_voltage }} V</td></tr>
                    </table>
                </div>

                <div class="section">
                    <h3>📋 最新数据示例</h3>
                    <table class="stats-table">
                        <tr>
                            <th>时间</th>
                            <th>温度(°C)</th>
                            <th>湿度(%)</th>
                            <th>气压(hPa)</th>
                            <th>电压(V)</th>
                        </tr>
                        {% for row in sample_data %}
                        <tr>
                            <td>{{ row.time }}</td>
                            <td>{{ row.temp }}</td>
                            <td>{{ row.hum }}</td>
                            <td>{{ row.press }}</td>
                            <td>{{ row.volt }}</td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>

                <div class="footer">
                    <p>报告由EC800X物联网监控系统自动生成</p>
                    <p>生成时间: {{ generated_time }}</p>
                </div>
            </body>
            </html>
            """

            # 准备数据
            sample_data = []
            for idx, row in df.head(10).iterrows():
                sample_data.append({
                    'time': idx.strftime('%H:%M:%S'),
                    'temp': f"{row['temperature']:.1f}",
                    'hum': f"{row['humidity']:.1f}",
                    'press': f"{row['pressure']:.1f}",
                    'volt': f"{row['voltage']:.2f}"
                })

            # 渲染HTML
            template = jinja2.Template(html_template)
            html_content = template.render(stats=stats, sample_data=sample_data)

            # 保存为HTML
            html_filename = f"sensor_report_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # 可选：转换为PDF（需要weasyprint）
            # pdf_filename = html_filename.replace('.html', '.pdf')
            # HTML(string=html_content).write_pdf(pdf_filename)

            print(f"✅ 报告已生成: {html_filename}")

        except ImportError as e:
            print(f"⚠️  需要安装额外库: pip install jinja2 weasyprint")
            print(f"   或使用简化版本")
        except Exception as e:
            print(f"❌ 生成报告失败: {e}")

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()