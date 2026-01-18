# data_viewer.py - 独立的数据查看工具
from database_manager import DatabaseViewer
import sys


def main():
    viewer = DatabaseViewer('sensor_data.db')

    while True:
        print("\n" + "=" * 50)
        print("📱 传感器数据管理系统")
        print("=" * 50)
        print("1. 查看数据仪表盘")
        print("2. 查询最新数据")
        print("3. 按时间范围查询")
        print("4. 数据统计信息")
        print("5. 导出数据为CSV")
        print("6. 添加设备命令")
        print("7. 查看待执行命令")
        print("0. 退出")

        choice = input("\n请选择操作 (0-7): ").strip()

        if choice == '1':
            viewer.show_dashboard()
        elif choice == '2':
            device_id = input("设备ID (直接回车查看所有): ").strip() or None
            limit = input("显示条数 (默认10): ").strip() or '10'
            data = viewer.db.get_recent_data(device_id, int(limit))

            print(f"\n📋 最近 {len(data)} 条数据:")
            for record in data:
                print(f"   [{record['timestamp']}] {record['device_id']}")
                print(f"      温度: {record.get('temperature')}°C | "
                      f"湿度: {record.get('humidity')}% | "
                      f"电压: {record.get('voltage')}V")
        elif choice == '3':
            start = input("开始时间 (格式: 2025-12-09 22:00:00): ").strip()
            end = input("结束时间 (直接回车查询之后所有): ").strip() or None
            viewer.query_data_by_time(start, end)
        elif choice == '4':
            device_id = input("设备ID (直接回车查看所有): ").strip() or None
            stats = viewer.db.get_statistics(device_id)

            print(f"\n📈 统计信息:")
            for key, value in stats.items():
                print(f"   {key}: {value}")
        elif choice == '5':
            filename = input("导出文件名 (默认: sensor_data_export.csv): ").strip() or 'sensor_data_export.csv'
            viewer.export_to_csv(filename)
        elif choice == '6':
            device_id = input("设备ID: ").strip()
            cmd_type = input("命令类型 (如: set_frequency, set_threshold): ").strip()
            cmd_value = input("命令值: ").strip()
            viewer.db.add_device_command(device_id, cmd_type, cmd_value)
        elif choice == '7':
            device_id = input("设备ID: ").strip()
            commands = viewer.db.get_pending_commands(device_id)

            if commands:
                print(f"\n📝 待执行命令 ({len(commands)} 条):")
                for cmd in commands:
                    print(f"   ID:{cmd['id']} {cmd['command_type']}={cmd['command_value']}")
            else:
                print("   ✅ 没有待执行命令")
        elif choice == '0':
            print("👋 再见!")
            break
        else:
            print("❌ 无效选择，请重试")


if __name__ == "__main__":
    main()