# data_visualizer_fixed.py
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import numpy as np
import os


class SensorDataVisualizer:
    def __init__(self, db_path='sensor_data.db'):
        """初始化可视化工具"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)

        # 修复字体问题：移除Emoji使用文本标签
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

    def load_sensor_data(self, device_id=None, hours=24, limit=1000):
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

            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)

            df = pd.read_sql_query(query, self.conn, params=params)

            # 转换时间格式并排序
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.sort_values('timestamp', inplace=True)
                df.set_index('timestamp', inplace=True)

            return df

        except Exception as e:
            print(f"❌ 加载数据失败: {e}")
            return pd.DataFrame()

    def create_realtime_dashboard(self, device_id='EC800X_Sensor_001', auto_refresh=False):
        """创建实时监控仪表盘"""
        # 设置交互模式
        plt.ion() if auto_refresh else plt.ioff()

        while True:
            try:
                df = self.load_sensor_data(device_id, hours=6, limit=100)

                if df.empty:
                    print("📭 没有找到数据")
                    if auto_refresh:
                        plt.pause(5)  # 等待5秒后重试
                        continue
                    else:
                        return

                # 清除之前的图表（如果存在）
                if hasattr(self, 'dashboard_fig'):
                    plt.close(self.dashboard_fig)

                # 创建新的图表
                self.dashboard_fig, axes = plt.subplots(3, 2, figsize=(15, 12))
                self.dashboard_fig.suptitle(f'传感器实时监控 - {device_id}', fontsize=16, fontweight='bold')

                # 1. 温度曲线
                ax1 = axes[0, 0]
                ax1.clear()
                ax1.plot(df.index, df['temperature'], 'r-', linewidth=2, marker='o', markersize=4, label='温度')
                ax1.fill_between(df.index, df['temperature'], alpha=0.3, color='red')
                ax1.set_title('温度变化趋势', fontsize=12, fontweight='bold')
                ax1.set_ylabel('温度 (°C)')
                ax1.grid(True, alpha=0.3)
                ax1.legend()

                # 添加温度统计信息
                if len(df) > 0:
                    avg_temp = df['temperature'].mean()
                    max_temp = df['temperature'].max()
                    min_temp = df['temperature'].min()
                    ax1.text(0.02, 0.95, f'平均: {avg_temp:.1f}°C\n最高: {max_temp:.1f}°C\n最低: {min_temp:.1f}°C',
                             transform=ax1.transAxes, verticalalignment='top',
                             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

                # 2. 湿度曲线
                ax2 = axes[0, 1]
                ax2.clear()
                ax2.plot(df.index, df['humidity'], 'b-', linewidth=2, marker='s', markersize=4, label='湿度')
                ax2.fill_between(df.index, df['humidity'], alpha=0.3, color='blue')
                ax2.set_title('湿度变化趋势', fontsize=12, fontweight='bold')
                ax2.set_ylabel('湿度 (%)')
                ax2.grid(True, alpha=0.3)
                ax2.legend()

                # 3. 气压曲线
                ax3 = axes[1, 0]
                ax3.clear()
                ax3.plot(df.index, df['pressure'], 'g-', linewidth=2, marker='^', markersize=4, label='气压')
                ax3.set_title('气压变化趋势', fontsize=12, fontweight='bold')
                ax3.set_ylabel('气压 (hPa)')
                ax3.grid(True, alpha=0.3)
                ax3.legend()

                # 4. 电压曲线
                ax4 = axes[1, 1]
                ax4.clear()
                ax4.plot(df.index, df['voltage'], 'orange', linewidth=2, marker='d', markersize=4, label='电压')
                ax4.set_title('电压变化趋势', fontsize=12, fontweight='bold')
                ax4.set_ylabel('电压 (V)')
                ax4.grid(True, alpha=0.3)
                ax4.legend()

                # 添加电压警告线
                ax4.axhline(y=3.3, color='red', linestyle='--', alpha=0.5, label='低电压警告')
                ax4.legend()

                # 5. 信号强度
                ax5 = axes[2, 0]
                ax5.clear()
                bars = ax5.bar(df.index, df['signal_strength'], color='purple', alpha=0.7)
                ax5.set_title('信号强度', fontsize=12, fontweight='bold')
                ax5.set_ylabel('信号强度')
                ax5.set_xlabel('时间')
                ax5.grid(True, alpha=0.3)

                # 6. 数据统计面板
                ax6 = axes[2, 1]
                ax6.clear()
                ax6.axis('off')

                # 计算统计数据
                if len(df) > 0:
                    stats_text = f"""
                    设备ID: {device_id}
                    数据时间范围: {df.index.min().strftime('%m-%d %H:%M')} 到 {df.index.max().strftime('%m-%d %H:%M')}
                    数据点数: {len(df)}

                    统计信息:
                    • 平均温度: {df['temperature'].mean():.2f}°C
                    • 温度范围: {df['temperature'].min():.1f}°C ~ {df['temperature'].max():.1f}°C
                    • 平均湿度: {df['humidity'].mean():.2f}%
                    • 平均气压: {df['pressure'].mean():.2f}hPa
                    • 平均电压: {df['voltage'].mean():.2f}V
                    • 平均信号: {df['signal_strength'].mean():.1f}

                    设备状态:
                    • 最后更新: {df.index.max().strftime('%H:%M:%S')}
                    • 更新间隔: {(datetime.now() - df.index.max()).seconds if len(df) > 0 else 0}秒前
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

                print(f"✅ 仪表盘更新: {filename} | 数据点: {len(df)} | 最后更新: {datetime.now().strftime('%H:%M:%S')}")

                if auto_refresh:
                    plt.pause(10)  # 10秒后刷新
                    continue
                else:
                    plt.show(block=True)
                    break

            except KeyboardInterrupt:
                print("\n🛑 停止实时更新")
                break
            except Exception as e:
                print(f"❌ 更新图表出错: {e}")
                if auto_refresh:
                    plt.pause(10)
                else:
                    break

    def create_live_monitor(self, device_id='EC800X_Sensor_001', update_interval=10):
        """创建自动更新的实时监控"""
        print(f"\n🚀 启动实时监控 (每{update_interval}秒更新)")
        print("按 Ctrl+C 停止监控")

        self.create_realtime_dashboard(device_id, auto_refresh=True)

    def create_simple_dashboard(self, device_id='EC800X_Sensor_001'):
        """创建简化的仪表盘（无Emoji）"""
        df = self.load_sensor_data(device_id, hours=6)

        if df.empty:
            print("📭 没有找到数据")
            return

        # 创建图表
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle(f'传感器数据监控 - {device_id}', fontsize=14)

        # 温度图表
        axes[0, 0].plot(df.index, df['temperature'], 'r-', linewidth=2)
        axes[0, 0].set_title('温度')
        axes[0, 0].set_ylabel('°C')
        axes[0, 0].grid(True, alpha=0.3)

        # 湿度图表
        axes[0, 1].plot(df.index, df['humidity'], 'b-', linewidth=2)
        axes[0, 1].set_title('湿度')
        axes[0, 1].set_ylabel('%')
        axes[0, 1].grid(True, alpha=0.3)

        # 电压图表
        axes[1, 0].plot(df.index, df['voltage'], 'g-', linewidth=2)
        axes[1, 0].set_title('电压')
        axes[1, 0].set_ylabel('V')
        axes[1, 0].grid(True, alpha=0.3)

        # 信号强度图表
        axes[1, 1].bar(df.index, df['signal_strength'], color='purple', alpha=0.7)
        axes[1, 1].set_title('信号强度')
        axes[1, 1].set_ylabel('强度')
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()

        # 保存图片
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"sensor_simple_{device_id}_{timestamp}.png"
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"✅ 图表已保存: {filename}")

        plt.show()

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
        plt.close('all')