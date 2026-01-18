# visualize_main_enhanced.py
from data_visualizer_fixed import SensorDataVisualizer
import sys
import threading
import time


class RealTimeMonitor:
    def __init__(self, db_path='sensor_data.db'):
        self.visualizer = SensorDataVisualizer(db_path)
        self.monitoring = False
        self.monitor_thread = None

    def start_monitor(self, device_id='EC800X_Sensor_001', interval=10):
        """启动后台监控线程"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(device_id, interval),
            daemon=True
        )
        self.monitor_thread.start()
        print(f"🔍 后台监控已启动 (设备: {device_id}, 间隔: {interval}秒)")
        print("   监控数据将自动更新，可视化图表需手动刷新")

    def _monitor_loop(self, device_id, interval):
        """监控循环"""
        last_count = 0
        while self.monitoring:
            try:
                df = self.visualizer.load_sensor_data(device_id, hours=1)
                current_count = len(df)

                if current_count > last_count:
                    new_data = current_count - last_count
                    print(f"📈 发现 {new_data} 条新数据 | 总数: {current_count}")
                    last_count = current_count

                time.sleep(interval)

            except Exception as e:
                print(f"❌ 监控出错: {e}")
                time.sleep(interval)

    def stop_monitor(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("🛑 后台监控已停止")


def main():
    monitor = RealTimeMonitor('sensor_data.db')
    visualizer = monitor.visualizer

    while True:
        print("\n" + "=" * 60)
        print("📊 传感器数据可视化系统 (增强版)")
        print("=" * 60)
        print("1. 显示实时监控仪表盘 (静态)")
        print("2. 启动自动更新监控 (后台)")
        print("3. 显示简化仪表盘 (无Emoji)")
        print("4. 温湿度对比分析")
        print("5. 历史趋势分析")
        print("6. 数据统计报告")
        print("7. 自定义查询")
        print("8. 停止后台监控")
        print("0. 退出系统")

        choice = input("\n请选择操作 (0-8): ").strip()

        if choice == '1':
            device_id = input("设备ID (默认: EC800X_Sensor_001): ").strip() or 'EC800X_Sensor_001'
            visualizer.create_realtime_dashboard(device_id, auto_refresh=False)

        elif choice == '2':
            device_id = input("设备ID (默认: EC800X_Sensor_001): ").strip() or 'EC800X_Sensor_001'
            interval = input("更新间隔(秒, 默认10): ").strip() or '10'

            # 启动后台监控
            monitor.start_monitor(device_id, int(interval))

            # 同时显示图表
            print("\n📊 显示实时图表...")
            visualizer.create_realtime_dashboard(device_id, auto_refresh=True)

        elif choice == '3':
            device_id = input("设备ID (默认: EC800X_Sensor_001): ").strip() or 'EC800X_Sensor_001'
            visualizer.create_simple_dashboard(device_id)

        elif choice == '4':
            print("\n📈 温湿度对比分析...")
            # 这里调用对比分析方法（需要实现）
            df = visualizer.load_sensor_data()
            if not df.empty:
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

                # 叠加图
                color = 'tab:red'
                ax1.set_xlabel('时间')
                ax1.set_ylabel('温度 (°C)', color=color)
                ax1.plot(df.index, df['temperature'], color=color, linewidth=2)
                ax1.tick_params(axis='y', labelcolor=color)

                ax1_twin = ax1.twinx()
                color = 'tab:blue'
                ax1_twin.set_ylabel('湿度 (%)', color=color)
                ax1_twin.plot(df.index, df['humidity'], color=color, linewidth=2)
                ax1_twin.tick_params(axis='y', labelcolor=color)

                ax1.set_title('温湿度变化对比')
                ax1.grid(True, alpha=0.3)

                # 散点图
                ax2.scatter(df['temperature'], df['humidity'], alpha=0.6, s=50)
                ax2.set_xlabel('温度 (°C)')
                ax2.set_ylabel('湿度 (%)')
                ax2.set_title('温湿度相关性')
                ax2.grid(True, alpha=0.3)

                plt.tight_layout()

                # 保存
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                plt.savefig(f'temp_humidity_{timestamp}.png', dpi=150)
                print(f"✅ 对比图已保存")

                plt.show()

        elif choice == '5':
            days = input("显示天数 (默认: 7): ").strip() or '7'
            # 这里调用历史趋势方法
            print("📊 历史趋势分析功能开发中...")

        elif choice == '6':
            df = visualizer.load_sensor_data()
            if not df.empty:
                print(f"\n📊 数据统计报告:")
                print(
                    f"   数据时间范围: {df.index.min().strftime('%Y-%m-%d %H:%M')} 到 {df.index.max().strftime('%Y-%m-%d %H:%M')}")
                print(f"   总数据点数: {len(df)}")
                print(
                    f"   温度统计: {df['temperature'].min():.1f}°C ~ {df['temperature'].max():.1f}°C, 平均: {df['temperature'].mean():.1f}°C")
                print(
                    f"   湿度统计: {df['humidity'].min():.1f}% ~ {df['humidity'].max():.1f}%, 平均: {df['humidity'].mean():.1f}%")
                print(
                    f"   电压统计: {df['voltage'].min():.2f}V ~ {df['voltage'].max():.2f}V, 平均: {df['voltage'].mean():.2f}V")

                # 导出CSV
                export = input("是否导出为CSV? (y/n): ").strip().lower()
                if export == 'y':
                    filename = f'sensor_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                    df.to_csv(filename)
                    print(f"✅ 数据已导出到: {filename}")

        elif choice == '7':
            print("\n🔍 自定义数据查询:")
            device_id = input("设备ID (直接回车查看所有): ").strip() or None
            hours = input("时间范围(小时, 默认24): ").strip() or '24'

            df = visualizer.load_sensor_data(device_id, int(hours))

            if not df.empty:
                print(f"\n📋 查询结果 ({len(df)} 条数据):")
                print(df.describe())

                viz_type = input("\n选择可视化类型 (1:折线图 2:柱状图 3:散点图): ").strip()

                plt.figure(figsize=(12, 6))

                if viz_type == '1':
                    for col in df.columns:
                        plt.plot(df.index, df[col], label=col, linewidth=2)
                    plt.title(f"{device_id or '所有设备'} - 数据变化趋势")
                    plt.legend()

                elif viz_type == '2':
                    # 显示最后10个数据点的柱状图
                    df_last = df.tail(10)
                    x = range(len(df_last))
                    width = 0.2

                    for i, col in enumerate(df_last.columns):
                        plt.bar([pos + i * width for pos in x], df_last[col], width=width, label=col)

                    plt.title(f"{device_id or '所有设备'} - 最新数据")
                    plt.legend()

                elif viz_type == '3':
                    plt.scatter(df['temperature'], df['humidity'], c=df['voltage'], s=50, alpha=0.6)
                    plt.xlabel('温度 (°C)')
                    plt.ylabel('湿度 (%)')
                    plt.colorbar(label='电压 (V)')
                    plt.title('温湿度-电压关系图')

                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.show()

        elif choice == '8':
            monitor.stop_monitor()

        elif choice == '0':
            print("\n👋 正在退出系统...")
            monitor.stop_monitor()
            visualizer.close()
            break

        else:
            print("❌ 无效选择，请重试")


if __name__ == "__main__":
    try:
        import matplotlib.pyplot as plt
        from datetime import datetime
    except ImportError:
        print("❌ 需要安装依赖: pip install matplotlib pandas")
        sys.exit(1)

    main()