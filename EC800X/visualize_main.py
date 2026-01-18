# visualize_main.py
import matplotlib.pyplot as plt
from data_visualizer import SensorDataVisualizer
import sys


def main():
    visualizer = SensorDataVisualizer('sensor_data.db')

    while True:
        print("\n" + "=" * 60)
        print("📊 传感器数据可视化系统")
        print("=" * 60)
        print("1.显示实时监控仪表盘")
        print("2. 显示温湿度对比分析")
        print("3. 显示历史趋势图（7天）")
        print("4. 生成数据报告（HTML/PDF）")
        print("5. 自定义查询并可视化")
        print("0. 退出")

        choice = input("\n请选择可视化类型 (0-5): ").strip()

        if choice == '1':
            device_id = input("设备ID (默认: EC800X_Sensor_001): ").strip() or 'EC800X_Sensor_001'
            visualizer.create_realtime_dashboard(device_id)

        elif choice == '2':
            visualizer.create_temperature_humidity_comparison()

        elif choice == '3':
            days = input("显示天数 (默认: 7): ").strip() or '7'
            try:
                visualizer.create_historical_trend(int(days))
            except:
                visualizer.create_historical_trend()

        elif choice == '4':
            device_id = input("设备ID (默认: EC800X_Sensor_001): ").strip() or 'EC800X_Sensor_001'
            visualizer.create_export_report(device_id)

        elif choice == '5':
            # 自定义查询
            print("\n🔍 自定义数据查询:")
            device_id = input("设备ID (直接回车查看所有): ").strip() or None
            hours = input("时间范围(小时, 默认24): ").strip() or '24'

            df = visualizer.load_sensor_data(device_id, int(hours))

            if not df.empty:
                print(f"\n📋 查询到 {len(df)} 条数据:")
                print(df.head())

                # 选择可视化类型
                print("\n📈 选择可视化方式:")
                print("  1. 折线图")
                print("  2. 柱状图")
                print("  3. 散点图")
                viz_choice = input("选择: ").strip()

                if viz_choice == '1':
                    columns = df.columns.tolist()
                    print(f"可用列: {', '.join(columns)}")
                    selected = input("选择要绘制的列(用逗号分隔): ").strip().split(',')

                    plt.figure(figsize=(12, 6))
                    for col in selected:
                        if col.strip() in df.columns:
                            plt.plot(df.index, df[col.strip()], label=col.strip(), linewidth=2)

                    plt.title(f"{device_id or '所有设备'} - 数据变化趋势", fontsize=14)
                    plt.xlabel('时间')
                    plt.ylabel('数值')
                    plt.legend()
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()
                    plt.show()

        elif choice == '0':
            print("👋 再见!")
            visualizer.close()
            break

        else:
            print("❌ 无效选择，请重试")


if __name__ == "__main__":
    # 检查是否安装matplotlib
    try:
        import matplotlib
    except ImportError:
        print("❌ 需要安装matplotlib: pip install matplotlib pandas")
        sys.exit(1)

    main()