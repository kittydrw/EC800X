# database_manager.py
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any


class SensorDatabase:
    def __init__(self, db_path='sensor_data.db'):
        """初始化SQLite数据库"""
        self.db_path = db_path
        self.conn = None
        self.init_database()

    def init_database(self):
        """创建数据库表结构"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()

            # 创建设备表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT UNIQUE NOT NULL,
                    device_name TEXT,
                    location TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP,
                    status TEXT DEFAULT 'online'
                )
            ''')

            # 创建传感器数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sensor_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    temperature REAL,
                    humidity REAL,
                    pressure REAL,
                    voltage REAL,
                    signal_strength INTEGER,
                    raw_values TEXT,  -- 存储为JSON字符串
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices (device_id)
                )
            ''')

            # 创建设备命令表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS device_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    command_type TEXT,
                    command_value TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    executed_at TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices (device_id)
                )
            ''')

            # 创建索引以提高查询速度
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_device_time ON sensor_data(device_id, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_timestamp ON sensor_data(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_commands_status ON device_commands(device_id, status)')

            self.conn.commit()
            print(f"✅ 数据库初始化完成: {self.db_path}")

        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")

    def save_sensor_data(self, sensor_data: Dict[str, Any]) -> bool:
        """保存传感器数据到数据库"""
        try:
            cursor = self.conn.cursor()

            # 1. 更新或插入设备信息
            cursor.execute('''
                INSERT OR REPLACE INTO devices (device_id, device_name, location, last_seen, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                sensor_data['device_id'],
                sensor_data.get('device_name', sensor_data['device_id']),
                sensor_data.get('location', 'Unknown'),
                sensor_data['timestamp'],
                sensor_data.get('status', 'normal')
            ))

            # 2. 插入传感器数据
            raw_values_json = json.dumps(sensor_data.get('raw_values', {}))

            cursor.execute('''
                INSERT INTO sensor_data 
                (device_id, timestamp, temperature, humidity, pressure, voltage, 
                 signal_strength, raw_values)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sensor_data['device_id'],
                sensor_data['timestamp'],
                sensor_data.get('temperature'),
                sensor_data.get('humidity'),
                sensor_data.get('pressure'),
                sensor_data.get('voltage'),
                sensor_data.get('signal_strength'),
                raw_values_json
            ))

            record_id = cursor.lastrowid
            self.conn.commit()

            print(f"💾 数据保存成功! 记录ID: {record_id}")
            return True

        except Exception as e:
            print(f"❌ 数据保存失败: {e}")
            return False

    def get_recent_data(self, device_id: str = None, limit: int = 10) -> List[Dict]:
        """获取最近的传感器数据"""
        try:
            cursor = self.conn.cursor()

            if device_id:
                cursor.execute('''
                    SELECT * FROM sensor_data 
                    WHERE device_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (device_id, limit))
            else:
                cursor.execute('''
                    SELECT * FROM sensor_data 
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))

            columns = [description[0] for description in cursor.description]
            results = []

            for row in cursor.fetchall():
                record = dict(zip(columns, row))
                # 解析raw_values JSON
                if record.get('raw_values'):
                    record['raw_values'] = json.loads(record['raw_values'])
                results.append(record)

            return results

        except Exception as e:
            print(f"❌ 查询数据失败: {e}")
            return []

    def get_statistics(self, device_id: str = None) -> Dict:
        """获取数据统计信息"""
        try:
            cursor = self.conn.cursor()

            if device_id:
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_records,
                        MIN(timestamp) as first_record,
                        MAX(timestamp) as last_record,
                        AVG(temperature) as avg_temperature,
                        AVG(humidity) as avg_humidity,
                        AVG(pressure) as avg_pressure
                    FROM sensor_data 
                    WHERE device_id = ?
                ''', (device_id,))
            else:
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_records,
                        MIN(timestamp) as first_record,
                        MAX(timestamp) as last_record,
                        AVG(temperature) as avg_temperature,
                        AVG(humidity) as avg_humidity,
                        AVG(pressure) as avg_pressure
                    FROM sensor_data
                ''')

            stats = dict(zip(
                ['total_records', 'first_record', 'last_record',
                 'avg_temperature', 'avg_humidity', 'avg_pressure'],
                cursor.fetchone()
            ))

            return stats

        except Exception as e:
            print(f"❌ 获取统计信息失败: {e}")
            return {}

    def add_device_command(self, device_id: str, command_type: str, command_value: str) -> bool:
        """添加设备命令"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO device_commands (device_id, command_type, command_value, status)
                VALUES (?, ?, ?, 'pending')
            ''', (device_id, command_type, command_value))

            self.conn.commit()
            print(f"📝 命令已添加: {command_type}={command_value} (设备: {device_id})")
            return True

        except Exception as e:
            print(f"❌ 添加命令失败: {e}")
            return False

    def get_pending_commands(self, device_id: str) -> List[Dict]:
        """获取待执行的命令"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, command_type, command_value 
                FROM device_commands 
                WHERE device_id = ? AND status = 'pending'
                ORDER BY created_at
            ''', (device_id,))

            commands = []
            for row in cursor.fetchall():
                commands.append({
                    'id': row[0],
                    'command_type': row[1],
                    'command_value': row[2]
                })

            return commands

        except Exception as e:
            print(f"❌ 获取命令失败: {e}")
            return []

    def mark_command_executed(self, command_id: int) -> bool:
        """标记命令为已执行"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE device_commands 
                SET status = 'executed', executed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (command_id,))

            self.conn.commit()
            return True

        except Exception as e:
            print(f"❌ 更新命令状态失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            print("🔌 数据库连接已关闭")


# 数据库查询工具类
class DatabaseViewer:
    def __init__(self, db_path='sensor_data.db'):
        self.db = SensorDatabase(db_path)

    def show_dashboard(self):
        """显示数据仪表盘"""
        print("\n" + "=" * 70)
        print("📊 传感器数据监控仪表盘")
        print("=" * 70)

        # 1. 显示设备列表
        print("\n📱 设备列表:")
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT device_id, location, status, last_seen FROM devices ORDER BY last_seen DESC')
            devices = cursor.fetchall()

            for device in devices:
                device_id, location, status, last_seen = device
                status_icon = "🟢" if status == 'online' else "🔴"
                print(f"   {status_icon} {device_id} | {location} | 最后在线: {last_seen}")
        except:
            print("   暂无设备数据")

        # 2. 显示数据统计
        print("\n📈 数据统计:")
        stats = self.db.get_statistics()
        if stats:
            print(f"   总记录数: {stats.get('total_records', 0)} 条")
            print(f"   时间范围: {stats.get('first_record', 'N/A')} 到 {stats.get('last_record', 'N/A')}")
            print(f"   平均温度: {stats.get('avg_temperature', 0):.2f}°C")
            print(f"   平均湿度: {stats.get('avg_humidity', 0):.2f}%")
            print(f"   平均气压: {stats.get('avg_pressure', 0):.2f}hPa")
        else:
            print("   暂无统计数据")

        # 3. 显示最新数据
        print("\n📋 最新数据记录:")
        recent_data = self.db.get_recent_data(limit=5)
        for data in recent_data:
            timestamp = data['timestamp'].split('T')[1].split('.')[0] if 'T' in str(data['timestamp']) else data[
                'timestamp']
            print(f"   [{timestamp}] {data['device_id']}: "
                  f"🌡️{data.get('temperature', 'N/A')}°C "
                  f"💧{data.get('humidity', 'N/A')}% "
                  f"📡信号:{data.get('signal_strength', 'N/A')}")

    def query_data_by_time(self, start_time: str, end_time: str = None):
        """按时间范围查询数据"""
        try:
            cursor = self.db.conn.cursor()

            if end_time:
                cursor.execute('''
                    SELECT * FROM sensor_data 
                    WHERE timestamp BETWEEN ? AND ?
                    ORDER BY timestamp
                ''', (start_time, end_time))
            else:
                cursor.execute('''
                    SELECT * FROM sensor_data 
                    WHERE timestamp >= ?
                    ORDER BY timestamp
                ''', (start_time,))

            columns = [description[0] for description in cursor.description]
            results = cursor.fetchall()

            print(f"\n🔍 查询结果 ({len(results)} 条记录):")
            for row in results:
                record = dict(zip(columns, row))
                print(f"   [{record['timestamp']}] {record['device_id']}: "
                      f"温度:{record.get('temperature')}°C "
                      f"湿度:{record.get('humidity')}%")

        except Exception as e:
            print(f"❌ 查询失败: {e}")

    def export_to_csv(self, filename='sensor_data_export.csv'):
        """导出数据为CSV文件"""
        try:
            import csv

            cursor = self.db.conn.cursor()
            cursor.execute('SELECT * FROM sensor_data ORDER BY timestamp')

            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)

                # 写入表头
                writer.writerow([description[0] for description in cursor.description])

                # 写入数据
                writer.writerows(cursor.fetchall())

            print(f"✅ 数据已导出到: {filename}")

        except Exception as e:
            print(f"❌ 导出失败: {e}")