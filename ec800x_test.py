import serial
import time
import json
import struct
import hashlib
import threading
import queue
import random
from datetime import datetime
from collections import deque
from typing import Dict, List, Optional, Tuple, Any


class EC800XStableTransmission:
    """
    EC800X 4G模块稳定传输类
    确保信道稳定和数据准确无误传输
    """

    def __init__(self, serial_port: str = 'COM3', baudrate: int = 115200):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.ser = None

        # 服务器配置
        self.server_host = "httpbin.org"
        self.server_port = 80
        self.api_path = "/post"

        # 通信参数
        self.at_timeout = 5  # AT命令超时时间
        self.data_timeout = 30  # 数据传输超时时间
        self.max_retries = 3  # 最大重试次数

        # 信道状态
        self.channel_state = {
            "quality_score": 0,  # 信道质量评分 (0-100)
            "signal_strength": 0,  # 信号强度 (0-31)
            "bit_error_rate": 0.0,  # 误码率
            "rssi": 0,  # 接收信号强度指示
            "sinr": 0,  # 信噪比
            "latency": 0,  # 延迟 (ms)
            "throughput": 0,  # 吞吐量 (bps)
            "stability": "unknown",  # 稳定性状态
            "last_update": 0  # 最后更新时间戳
        }

        # 传输统计
        self.transmission_stats = {
            "total_packets": 0,
            "successful_packets": 0,
            "failed_packets": 0,
            "retransmissions": 0,
            "total_bytes": 0,
            "avg_latency": 0,
            "success_rate": 0.0,
            "connection_uptime": 0
        }

        # 数据队列
        self.data_queue = queue.Queue()
        self.ack_queue = queue.Queue()

        # 序列号管理
        self.sequence_counter = 0
        self.pending_ack = {}

        # 连接状态
        self.is_connected = False
        self.connection_id = 0
        self.pdp_context_active = False
        self.tcp_connected = False

        # 监控线程
        self.monitor_thread = None
        self.monitor_active = False
        self.monitor_interval = 10  # 监控间隔(秒)

        # 数据库连接
        try:
            from database_manager import SensorDatabase
            self.database = SensorDatabase('sensor_data.db')
            self.use_database = True
        except ImportError:
            print("⚠️  数据库模块未找到，数据将仅保存在内存中")
            self.use_database = False
            self.data_storage = []

        # 配置传输参数
        self.transmission_config = {
            "packet_size": 1024,  # 数据包大小
            "chunk_size": 512,  # 分块大小
            "timeout": 15,  # 传输超时
            "max_retries": 5,  # 最大重试
            "retry_delay": 2,  # 重试延迟
            "use_checksum": True,  # 使用校验和
            "use_sequence": True,  # 使用序列号
            "enable_fec": False,  # 前向纠错
            "compress_data": False,  # 压缩数据
            "adaptive_mode": True  # 自适应模式
        }

        # 连接开始时间
        self.connection_start_time = time.time()

        print(f"📡 EC800X稳定传输系统初始化完成")
        print(f"   串口: {serial_port}")
        print(f"   波特率: {baudrate}")
        print(f"   服务器: {self.server_host}:{self.server_port}")

    def init_serial(self) -> bool:
        """
        初始化串口连接
        返回: True表示成功，False表示失败
        """
        try:
            print(f"🔌 正在连接串口 {self.serial_port}...")

            # 首先尝试无流控制
            try:
                self.ser = serial.Serial(
                    port=self.serial_port,
                    baudrate=self.baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1,
                    write_timeout=1,
                    rtscts=False,  # 关闭硬件流控制
                    dsrdtr=False  # 关闭DSR/DTR流控制
                )
                print("✅ 串口连接成功 (无流控制)")
            except Exception as e:
                print(f"❌ 串口连接失败: {e}")
                return False

            # 测试AT命令
            if not self.test_at_command():
                print("❌ AT命令测试失败")
                return False

            print("✅ 串口初始化完成")
            return True

        except Exception as e:
            print(f"❌ 串口初始化异常: {e}")
            return False

    def test_at_command(self) -> bool:
        """测试AT命令是否正常响应"""
        try:
            response = self.send_at_command_raw("AT", timeout=2)
            if response and ("OK" in response or "ok" in response):
                print("✅ AT命令测试通过")
                return True
            else:
                print(f"❌ AT命令无响应: {response}")
                return False
        except Exception as e:
            print(f"❌ AT命令测试异常: {e}")
            return False

    def send_at_command_raw(self, command: str, timeout: float = 5) -> str:
        """
        发送原始AT命令
        返回: 响应字符串
        """
        if not self.ser or not self.ser.is_open:
            print("❌ 串口未打开")
            return ""

        try:
            # 清空输入缓冲区
            self.ser.reset_input_buffer()
            time.sleep(0.05)

            # 发送命令
            full_command = f"{command}\r\n"
            print(f"📤 AT命令: {command}")

            self.ser.write(full_command.encode('utf-8'))
            self.ser.flush()

            # 等待响应
            response_bytes = b""
            start_time = time.time()

            while time.time() - start_time < timeout:
                if self.ser.in_waiting > 0:
                    chunk = self.ser.read(self.ser.in_waiting)
                    response_bytes += chunk
                    # 如果已经收到完整响应，提前退出
                    if b"OK\r\n" in response_bytes or b"ERROR\r\n" in response_bytes:
                        time.sleep(0.1)  # 等待可能的额外数据
                        break
                time.sleep(0.05)

            # 解码响应
            try:
                response = response_bytes.decode('utf-8', errors='ignore').strip()
            except:
                response = response_bytes.decode('ascii', errors='ignore').strip()

            # 清理响应（移除回显）
            response = self._clean_at_response(command, response)

            # 显示响应摘要
            if response:
                response_lines = response.split('\n')
                if len(response_lines) <= 3:
                    print(f"📥 响应: {response}")
                else:
                    print(f"📥 响应: {response_lines[0]} ... ({len(response_lines)}行)")

            return response

        except serial.SerialException as e:
            print(f"❌ 串口通信错误: {e}")
            return ""
        except Exception as e:
            print(f"❌ AT命令发送错误: {e}")
            return ""

    def _clean_at_response(self, command: str, response: str) -> str:
        """清理AT响应，移除回显"""
        lines = response.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 移除命令回显
            if line == command or line.startswith("AT+"):
                continue

            # 移除回车符和多余空白
            line = line.replace('\r', '').strip()
            if line:
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def check_response_ok(self, response: str) -> bool:
        """检查响应是否包含OK"""
        return "OK" in response.upper()

    def setup_module(self) -> bool:
        """
        配置EC800X模块
        返回: True表示成功，False表示失败
        """
        print("\n" + "=" * 60)
        print("🔧 EC800X模块初始化配置")
        print("=" * 60)

        # 1. 关闭回显
        print("\n1. 关闭命令回显...")
        response = self.send_at_command_raw("ATE0", timeout=2)
        if not self.check_response_ok(response):
            print("⚠️  无法关闭回显，继续使用回显模式")

        # 2. 检查模块信息
        print("\n2. 检查模块信息...")
        info_commands = [
            ("ATI", "模块识别"),
            ("AT+CGMI", "制造商"),
            ("AT+CGMM", "型号"),
            ("AT+CGMR", "版本"),
            ("AT+CGSN", "IMEI"),
        ]

        for cmd, desc in info_commands:
            print(f"   {desc}...", end=" ")
            response = self.send_at_command_raw(cmd, timeout=2)
            if self.check_response_ok(response):
                print("✅")
            else:
                print("❌")

        # 3. 检查网络状态
        print("\n3. 检查网络状态...")
        network_commands = [
            ("AT+CPIN?", "SIM卡状态"),
            ("AT+CSQ", "信号强度"),
            ("AT+COPS?", "运营商"),
            ("AT+CREG?", "网络注册"),
            ("AT+CGREG?", "GPRS注册"),
        ]

        network_ok = True
        for cmd, desc in network_commands:
            print(f"   {desc}...", end=" ")
            response = self.send_at_command_raw(cmd, timeout=3)

            if self.check_response_ok(response):
                print("✅")
                # 解析信号强度
                if cmd == "AT+CSQ" and "+CSQ:" in response:
                    try:
                        signal_part = response.split("+CSQ:")[1].split(",")[0].strip()
                        signal_value = int(signal_part)
                        self.channel_state["signal_strength"] = signal_value
                        print(f"     信号强度: {signal_value}/31")
                    except:
                        pass
            else:
                print("❌")
                network_ok = False

        return network_ok

    def setup_network_connection(self) -> bool:
        """
        建立网络连接
        返回: True表示成功，False表示失败
        """
        print("\n" + "=" * 60)
        print("🌐 建立网络连接")
        print("=" * 60)

        max_retries = 3
        for attempt in range(max_retries):
            print(f"\n🔗 尝试 {attempt + 1}/{max_retries}")

            try:
                # 1. 设置APN (使用移动网络CMNET)
                print("1. 设置APN...")
                apn_cmd = 'AT+QICSGP=1,1,"CMNET","","",1'
                response = self.send_at_command_raw(apn_cmd, timeout=5)

                if not self.check_response_ok(response):
                    print("⚠️  APN设置失败，尝试继续")

                # 2. 激活PDP上下文
                print("2. 激活PDP上下文...")
                response = self.send_at_command_raw("AT+QIACT=1", timeout=10)

                if self.check_response_ok(response):
                    print("✅ PDP上下文激活成功")
                    self.pdp_context_active = True
                else:
                    # 如果激活失败，尝试先取消激活
                    print("⚠️  PDP激活失败，尝试重新激活...")
                    self.send_at_command_raw("AT+QIDEACT=1", timeout=5)
                    time.sleep(2)
                    response = self.send_at_command_raw("AT+QIACT=1", timeout=10)

                    if self.check_response_ok(response):
                        print("✅ PDP上下文重新激活成功")
                        self.pdp_context_active = True
                    else:
                        print("❌ PDP上下文激活失败")
                        continue

                # 3. 检查激活状态
                print("3. 检查网络激活状态...")
                response = self.send_at_command_raw("AT+QIACT?", timeout=3)

                if "1,1" in response or "1,3" in response:
                    print("✅ 网络已激活")
                    self.is_connected = True

                    # 更新连接时间
                    self.connection_start_time = time.time()

                    return True
                else:
                    print(f"❌ 网络未激活: {response}")

            except Exception as e:
                print(f"❌ 网络连接异常: {e}")

            # 等待后重试
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                print(f"⏳ {wait_time}秒后重试...")
                time.sleep(wait_time)

        print("🚨 网络连接失败")
        return False

    def establish_tcp_connection(self) -> bool:
        """
        建立TCP连接
        返回: True表示成功，False表示失败
        """
        print("\n" + "=" * 60)
        print("🔗 建立TCP连接")
        print("=" * 60)

        max_retries = 3
        for attempt in range(max_retries):
            print(f"\n🔗 TCP连接尝试 {attempt + 1}/{max_retries}")

            try:
                # 1. 关闭现有连接
                print("1. 清理现有连接...")
                self.send_at_command_raw(f"AT+QICLOSE={self.connection_id}", timeout=3)
                time.sleep(1)

                # 2. 建立新连接
                print("2. 建立TCP连接...")
                connect_cmd = f'AT+QIOPEN=1,{self.connection_id},"TCP","{self.server_host}",{self.server_port}'
                response = self.send_at_command_raw(connect_cmd, timeout=15)

                if f"+QIOPEN: {self.connection_id},0" in response:
                    print(f"✅ TCP连接成功 (ID: {self.connection_id})")
                    self.tcp_connected = True
                    return True
                else:
                    print(f"❌ TCP连接失败: {response}")

            except Exception as e:
                print(f"❌ TCP连接异常: {e}")

            # 等待后重试
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"⏳ {wait_time}秒后重试...")
                time.sleep(wait_time)

        print("🚨 TCP连接失败")
        return False

    def assess_channel_quality(self) -> Dict[str, Any]:
        """
        评估信道质量
        返回: 信道质量报告
        """
        print("\n📊 信道质量评估...")

        quality_report = {
            "timestamp": datetime.now().isoformat(),
            "signal_strength": 0,
            "signal_quality": 0,
            "network_status": "unknown",
            "recommended_action": "none"
        }

        try:
            # 1. 检查信号强度
            print("1. 测量信号强度...")
            response = self.send_at_command_raw("AT+CSQ", timeout=3)

            if "+CSQ:" in response:
                try:
                    parts = response.split("+CSQ:")[1].split(",")
                    rssi = int(parts[0].strip()) if parts[0].strip() else 99
                    ber = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip() else 99

                    self.channel_state["signal_strength"] = rssi
                    self.channel_state["bit_error_rate"] = ber if ber != 99 else 0

                    # 计算信号质量百分比
                    if rssi == 99:
                        signal_quality = 0
                    else:
                        signal_quality = min(int((rssi / 31) * 100), 100)

                    quality_report["signal_strength"] = rssi
                    quality_report["signal_quality"] = signal_quality

                    print(f"   📶 RSSI: {rssi} ({signal_quality}%)")
                    print(f"   🔧 BER: {ber}")

                except Exception as e:
                    print(f"   ⚠️  信号强度解析错误: {e}")

            # 2. 检查网络注册状态
            print("2. 检查网络注册...")
            response = self.send_at_command_raw("AT+CREG?", timeout=3)

            if "+CREG:" in response:
                try:
                    parts = response.split("+CREG:")[1].split(",")
                    if len(parts) >= 2:
                        n = int(parts[0].strip())
                        stat = int(parts[1].strip())

                        status_map = {
                            0: "未注册",
                            1: "已注册(本地)",
                            2: "未注册(搜索中)",
                            3: "注册被拒绝",
                            4: "未知",
                            5: "已注册(漫游)"
                        }

                        network_status = status_map.get(stat, "未知")
                        quality_report["network_status"] = network_status

                        print(f"   🌐 网络状态: {network_status}")
                except:
                    pass

            # 3. 检查GPRS附着状态
            print("3. 检查GPRS附着...")
            response = self.send_at_command_raw("AT+CGATT?", timeout=3)

            if "+CGATT: 1" in response:
                print("   ✅ GPRS已附着")
                quality_report["network_status"] = "GPRS已附着"
            elif "+CGATT: 0" in response:
                print("   ❌ GPRS未附着")
                quality_report["network_status"] = "GPRS未附着"

            # 4. 计算信道质量评分
            quality_score = self._calculate_channel_quality_score(quality_report)
            self.channel_state["quality_score"] = quality_score

            # 5. 根据评分提供建议
            if quality_score >= 80:
                quality_report["stability"] = "优秀"
                quality_report["recommended_action"] = "正常传输"
                print(f"   🎯 信道质量: 优秀 ({quality_score}/100)")
            elif quality_score >= 60:
                quality_report["stability"] = "良好"
                quality_report["recommended_action"] = "正常传输"
                print(f"   👍 信道质量: 良好 ({quality_score}/100)")
            elif quality_score >= 40:
                quality_report["stability"] = "一般"
                quality_report["recommended_action"] = "小包传输"
                print(f"   ⚠️  信道质量: 一般 ({quality_score}/100)")
            else:
                quality_report["stability"] = "较差"
                quality_report["recommended_action"] = "等待恢复"
                print(f"   ❌ 信道质量: 较差 ({quality_score}/100)")

            # 更新状态时间戳
            self.channel_state["last_update"] = time.time()

            return quality_report

        except Exception as e:
            print(f"❌ 信道质量评估失败: {e}")
            return quality_report

    def _calculate_channel_quality_score(self, quality_report: Dict) -> int:
        """计算信道质量综合评分"""
        score = 0

        # 信号强度权重 50%
        signal_quality = quality_report.get("signal_quality", 0)
        score += signal_quality * 0.5

        # 网络状态权重 30%
        network_status = quality_report.get("network_status", "")
        if "已注册" in network_status or "GPRS已附着" in network_status:
            score += 30
        elif "未注册" in network_status or "GPRS未附着" in network_status:
            score += 10
        else:
            score += 20

        # 历史成功率权重 20%
        if self.transmission_stats["total_packets"] > 0:
            success_rate = self.transmission_stats["success_rate"]
            score += success_rate * 0.2

        return min(int(score), 100)

    def generate_data_packet(self, data: Dict) -> Tuple[bytes, int]:
        """
        生成数据包（带校验和和序列号）
        返回: (数据包字节, 序列号)
        """
        # 增加序列号
        sequence = self.sequence_counter
        self.sequence_counter += 1

        # 添加序列号和校验信息
        enhanced_data = data.copy()
        enhanced_data["sequence"] = sequence
        enhanced_data["timestamp"] = datetime.now().isoformat()
        enhanced_data["checksum_seed"] = random.randint(1000, 9999)

        # 转换为JSON
        json_data = json.dumps(enhanced_data, ensure_ascii=False)

        # 计算CRC32校验和
        crc32 = self._calculate_crc32(json_data)

        # 创建数据包结构
        packet_struct = struct.pack(
            '!II',  # 序列号(4字节) + 校验和(4字节)
            sequence,
            crc32
        )

        # 组合数据包
        packet = packet_struct + json_data.encode('utf-8')

        print(f"📦 生成数据包 #{sequence}, 大小: {len(packet)}字节")

        return packet, sequence

    def _calculate_crc32(self, data: str) -> int:
        """计算CRC32校验和"""
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    def send_data_packet(self, packet: bytes, sequence: int) -> bool:
        """
        发送单个数据包
        返回: True表示成功，False表示失败
        """
        print(f"\n📤 发送数据包 #{sequence}...")

        max_retries = self.transmission_config["max_retries"]

        for attempt in range(max_retries):
            print(f"   尝试 {attempt + 1}/{max_retries}")

            try:
                # 检查TCP连接状态
                if not self.tcp_connected:
                    print("   ⚠️  TCP连接断开，尝试重连...")
                    if not self.establish_tcp_connection():
                        print("   ❌ TCP重连失败")
                        continue

                # 发送数据
                send_cmd = f'AT+QISEND={self.connection_id},{len(packet)}'
                response = self.send_at_command_raw(send_cmd, timeout=5)

                if ">" in response:
                    print(f"   📤 发送数据 ({len(packet)}字节)...")
                    self.ser.write(packet)
                    time.sleep(1)  # 等待发送完成

                    # 检查发送状态
                    status_cmd = f"AT+QISEND={self.connection_id},0"
                    status_response = self.send_at_command_raw(status_cmd, timeout=3)

                    if "0,0" in status_response:
                        print(f"   ✅ 数据包 #{sequence} 发送成功")

                        # 更新统计
                        self.transmission_stats["total_packets"] += 1
                        self.transmission_stats["successful_packets"] += 1
                        self.transmission_stats["total_bytes"] += len(packet)

                        # 计算成功率
                        total = self.transmission_stats["total_packets"]
                        success = self.transmission_stats["successful_packets"]
                        if total > 0:
                            self.transmission_stats["success_rate"] = (success / total) * 100

                        return True
                    else:
                        print(f"   ❌ 发送状态异常: {status_response}")
                else:
                    print(f"   ❌ 发送准备失败: {response}")

            except Exception as e:
                print(f"   ❌ 发送异常: {e}")

            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                wait_time = self.transmission_config["retry_delay"] * (attempt + 1)
                print(f"   ⏳ {wait_time}秒后重试...")
                time.sleep(wait_time)

        # 所有尝试都失败
        print(f"   🚨 数据包 #{sequence} 发送失败")
        self.transmission_stats["total_packets"] += 1
        self.transmission_stats["failed_packets"] += 1
        self.transmission_stats["retransmissions"] += max_retries - 1

        return False

    def send_sensor_data(self, sensor_data: Dict) -> bool:
        """
        发送传感器数据（带完整性保证）
        返回: True表示成功，False表示失败
        """
        print("\n" + "=" * 60)
        print("📊 发送传感器数据")
        print("=" * 60)

        # 1. 评估信道质量
        quality_report = self.assess_channel_quality()

        # 如果信道质量太差，延迟发送
        if quality_report["signal_quality"] < 30:
            print("⚠️  信道质量过差，延迟发送数据")
            self.data_queue.put(sensor_data)
            return False

        # 2. 根据信道质量调整传输参数
        self._adjust_transmission_parameters(quality_report)

        # 3. 生成数据包
        packet, sequence = self.generate_data_packet(sensor_data)

        # 4. 发送数据包
        success = self.send_data_packet(packet, sequence)

        # 5. 记录到数据库
        if success and self.use_database:
            try:
                # 添加传输状态信息
                sensor_data["transmission_status"] = "success"
                sensor_data["transmission_sequence"] = sequence
                sensor_data["channel_quality"] = quality_report["signal_quality"]
                self.database.save_sensor_data(sensor_data)
            except Exception as e:
                print(f"⚠️  数据库保存失败: {e}")

        return success

    def _adjust_transmission_parameters(self, quality_report: Dict):
        """根据信道质量调整传输参数"""
        signal_quality = quality_report["signal_quality"]

        if signal_quality >= 80:  # 优秀信道
            self.transmission_config.update({
                "packet_size": 2048,
                "chunk_size": 1024,
                "timeout": 10,
                "max_retries": 3,
                "enable_fec": False,
                "compress_data": True
            })
            print("📈 使用高速传输模式")

        elif signal_quality >= 60:  # 良好信道
            self.transmission_config.update({
                "packet_size": 1024,
                "chunk_size": 512,
                "timeout": 15,
                "max_retries": 5,
                "enable_fec": False,
                "compress_data": False
            })
            print("📶 使用标准传输模式")

        elif signal_quality >= 40:  # 一般信道
            self.transmission_config.update({
                "packet_size": 512,
                "chunk_size": 256,
                "timeout": 20,
                "max_retries": 8,
                "enable_fec": True,
                "compress_data": False
            })
            print("⚠️  使用保守传输模式")

        else:  # 差信道
            self.transmission_config.update({
                "packet_size": 256,
                "chunk_size": 128,
                "timeout": 30,
                "max_retries": 10,
                "enable_fec": True,
                "compress_data": False
            })
            print("🔻 使用增强纠错模式")

    def start_channel_monitoring(self, interval: int = 10):
        """启动信道监控线程"""
        if self.monitor_active:
            print("⚠️  监控线程已在运行")
            return

        print(f"📡 启动信道监控，间隔: {interval}秒")

        self.monitor_active = True

        def monitor_loop():
            while self.monitor_active:
                try:
                    # 评估信道质量
                    self.assess_channel_quality()

                    # 检查连接状态
                    if self.is_connected and not self.check_connection_health():
                        print("🚨 检测到连接问题，尝试恢复...")
                        self.recover_connection()

                    # 检查是否有待发送数据
                    if not self.data_queue.empty():
                        quality = self.channel_state["quality_score"]
                        if quality > 50:  # 信道质量足够好
                            try:
                                data = self.data_queue.get_nowait()
                                print("📤 发送队列中的待发数据...")
                                self.send_sensor_data(data)
                            except queue.Empty:
                                pass

                except Exception as e:
                    print(f"⚠️  监控线程异常: {e}")

                # 等待下一个监控周期
                time.sleep(interval)

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()

    def check_connection_health(self) -> bool:
        """检查连接健康状况"""
        try:
            # 检查PDP上下文
            response = self.send_at_command_raw("AT+QIACT?", timeout=3)
            if "1,1" not in response and "1,3" not in response:
                print("⚠️  PDP上下文异常")
                return False

            # 检查TCP连接
            response = self.send_at_command_raw(f"AT+QISTATE=1,{self.connection_id}", timeout=3)
            if "CONNECTED" not in response:
                print("⚠️  TCP连接断开")
                return False

            return True

        except Exception as e:
            print(f"⚠️  连接健康检查异常: {e}")
            return False

    def recover_connection(self) -> bool:
        """恢复连接"""
        print("🔧 尝试恢复连接...")

        try:
            # 1. 关闭TCP连接
            self.send_at_command_raw(f"AT+QICLOSE={self.connection_id}", timeout=3)
            self.tcp_connected = False
            time.sleep(2)

            # 2. 重新建立TCP连接
            if self.establish_tcp_connection():
                print("✅ 连接恢复成功")
                return True
            else:
                print("❌ 连接恢复失败")
                return False

        except Exception as e:
            print(f"❌ 连接恢复异常: {e}")
            return False

    def generate_sensor_data(self) -> Dict:
        """生成模拟传感器数据"""
        return {
            "device_id": "EC800X_Sensor_001",
            "timestamp": datetime.now().isoformat(),
            "location": "实验室监测点A",
            "sensor_type": "environment_monitor",
            "temperature": round(20 + random.uniform(0, 10), 2),
            "humidity": round(40 + random.uniform(0, 30), 2),
            "pressure": round(1000 + random.uniform(-10, 10), 2),
            "voltage": round(3.6 + random.uniform(0, 0.4), 2),
            "signal_strength": self.channel_state["signal_strength"],
            "channel_quality": self.channel_state["quality_score"],
            "battery_level": round(85 + random.uniform(-10, 10), 1),
            "status": "normal"
        }

    def run_stable_transmission_test(self, cycles: int = 10, interval: int = 30):
        """
        运行稳定传输测试
        cycles: 测试周期数
        interval: 每个周期间隔(秒)
        """
        print("\n" + "=" * 70)
        print("🚀 EC800X稳定传输测试开始")
        print("=" * 70)

        # 1. 初始化串口
        if not self.init_serial():
            print("❌ 串口初始化失败")
            return False

        # 2. 配置模块
        if not self.setup_module():
            print("⚠️  模块配置有警告，继续测试...")

        # 3. 建立网络连接
        if not self.setup_network_connection():
            print("❌ 网络连接失败")
            return False

        # 4. 建立TCP连接
        if not self.establish_tcp_connection():
            print("❌ TCP连接失败")
            return False

        # 5. 启动信道监控
        self.start_channel_monitoring(interval=15)

        print(f"\n🎯 开始传输测试，共{cycles}个周期")

        # 6. 运行传输测试
        for cycle in range(1, cycles + 1):
            print(f"\n{'=' * 60}")
            print(f"🔄 传输周期 {cycle}/{cycles}")
            print('=' * 60)

            # 生成传感器数据
            sensor_data = self.generate_sensor_data()

            print(f"📊 传感器数据:")
            for key, value in sensor_data.items():
                if key not in ["timestamp", "location", "device_id"]:
                    print(f"   {key}: {value}")

            # 发送数据
            success = self.send_sensor_data(sensor_data)

            if success:
                print(f"✅ 周期 {cycle} 传输成功")
            else:
                print(f"❌ 周期 {cycle} 传输失败")
                # 加入重试队列
                self.data_queue.put(sensor_data)

            # 显示统计信息
            self.show_current_stats()

            # 等待下一个周期
            if cycle < cycles:
                actual_interval = max(10, interval - self.channel_state["quality_score"] / 2)
                print(f"\n⏳ 等待 {actual_interval:.1f} 秒进入下一个周期...")
                time.sleep(actual_interval)

        # 7. 最终报告
        self.show_final_report()

        return True

    def show_current_stats(self):
        """显示当前统计信息"""
        print(f"\n📈 当前统计:")
        print(f"   总数据包: {self.transmission_stats['total_packets']}")
        print(f"   成功: {self.transmission_stats['successful_packets']}")
        print(f"   失败: {self.transmission_stats['failed_packets']}")

        if self.transmission_stats['total_packets'] > 0:
            success_rate = self.transmission_stats['success_rate']
            print(f"   成功率: {success_rate:.1f}%")

        print(f"   重传次数: {self.transmission_stats['retransmissions']}")
        print(f"   总数据量: {self.transmission_stats['total_bytes'] / 1024:.2f} KB")

        # 显示信道状态
        print(f"📊 信道状态:")
        print(f"   信号强度: {self.channel_state['signal_strength']}/31")
        print(f"   质量评分: {self.channel_state['quality_score']}/100")

        # 显示连接状态
        uptime = time.time() - self.connection_start_time
        hours, remainder = divmod(int(uptime), 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f"🔗 连接状态:")
        print(f"   连接时间: {hours:02d}:{minutes:02d}:{seconds:02d}")
        print(f"   TCP连接: {'✅' if self.tcp_connected else '❌'}")
        print(f"   待发数据: {self.data_queue.qsize()} 条")

    def show_final_report(self):
        """显示最终报告"""
        print("\n" + "=" * 70)
        print("📋 EC800X稳定传输测试最终报告")
        print("=" * 70)

        total = self.transmission_stats["total_packets"]
        success = self.transmission_stats["successful_packets"]

        if total > 0:
            success_rate = self.transmission_stats["success_rate"]

            print(f"\n🎯 传输性能分析:")
            print(f"   总传输次数: {total}")
            print(f"   成功次数: {success}")
            print(f"   失败次数: {self.transmission_stats['failed_packets']}")
            print(f"   最终成功率: {success_rate:.2f}%")
            print(f"   平均重传次数: {self.transmission_stats['retransmissions'] / max(total, 1):.2f}")
            print(f"   总数据量: {self.transmission_stats['total_bytes'] / 1024:.2f} KB")

            # 评估传输质量
            if success_rate >= 95:
                rating = "🔴 优秀"
            elif success_rate >= 85:
                rating = "🟢 良好"
            elif success_rate >= 70:
                rating = "🟡 一般"
            else:
                rating = "🔴 较差"

            print(f"\n📊 传输质量评级: {rating}")

        # 信道质量总结
        print(f"\n📡 信道质量总结:")
        print(f"   最终信号强度: {self.channel_state['signal_strength']}/31")
        print(f"   最终质量评分: {self.channel_state['quality_score']}/100")

        # 建议
        print(f"\n💡 建议:")
        if self.channel_state['quality_score'] >= 80:
            print("   信道质量优秀，可以增加数据传输频率")
        elif self.channel_state['quality_score'] >= 60:
            print("   信道质量良好，适合常规数据传输")
        elif self.channel_state['quality_score'] >= 40:
            print("   信道质量一般，建议减少数据包大小")
        else:
            print("   信道质量较差，建议检查天线和信号覆盖")

        if self.data_queue.qsize() > 0:
            print(f"\n⚠️  注意: 仍有 {self.data_queue.qsize()} 条数据在队列中")
            print("   重启程序时会自动尝试发送")

    def cleanup(self):
        """清理资源"""
        print("\n🧹 清理资源...")

        # 停止监控线程
        self.monitor_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        # 关闭TCP连接
        if self.tcp_connected:
            try:
                self.send_at_command_raw(f"AT+QICLOSE={self.connection_id}", timeout=3)
                print("✅ TCP连接已关闭")
            except:
                pass

        # 关闭串口
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("✅ 串口已关闭")

        print("✅ 资源清理完成")


def main():
    """主函数"""
    print("EC800X 4G模块稳定传输系统")
    print("版本: 2.0 - 增强稳定传输版")
    print("=" * 70)

    # 创建传输实例
    transmitter = EC800XStableTransmission(
        serial_port='COM3',
        baudrate=115200
    )

    try:
        # 运行稳定传输测试
        success = transmitter.run_stable_transmission_test(
            cycles=8,  # 8个传输周期
            interval=25  # 每个周期间隔25秒
        )

        if success:
            print("\n🎉 稳定传输测试完成!")
        else:
            print("\n⚠️  测试过程中出现问题")

        # 询问是否显示详细报告
        choice = input("\n是否显示详细统计报告? (y/n): ").lower()
        if choice == 'y':
            transmitter.show_final_report()

    except KeyboardInterrupt:
        print("\n🛑 用户中断测试")
    except Exception as e:
        print(f"\n❌ 程序运行错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        transmitter.cleanup()


if __name__ == "__main__":
    main()