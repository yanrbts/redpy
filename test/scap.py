"""
Red Gateway - Pure Python Layer-2 Sniffing & L3 standard UDP Forwarder.
Powered by Scapy. Zero Linux system commands configuration required.
"""
import threading
import os
import socket
import sys
from scapy.all import sniff, IP, UDP
from rich.console import Console
from rich.table import Table
from rich.live import Live

console = Console()

# ───────────────────────────────────────────────────────────────────────
# 🌟 MATRIX CONFIGURATION (全参数 Python 内部控制)
# ───────────────────────────────────────────────────────────────────────
LISTEN_INTERFACE = "ens33"         # 监听的物理网卡
TARGET_SERVER_IP = "192.168.211.130"
TARGET_SERVER_PORT = 52720         # 错位出站端口，彻底打破回环

class Telemetry:
    total_forwarded = 0
    last_packet_len = 0

stats = Telemetry()

# Pre-allocate standard outbound UDP socket (标准的独立出站三层套接字)
udp_tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_tx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)


def build_dashboard() -> Table:
    """Rich TUI 渲染大屏"""
    table = Table(title="[bold magenta]Red Gateway[/bold magenta] - Scapy Engine Plane", expand=True)
    table.add_column("Runtime Metric", justify="left", style="cyan")
    table.add_column("Value", justify="right", style="green")
    
    table.add_row("Data Plane Backend", "Python Scapy + Libpcap (BPF Filter)")
    table.add_row("System Command Risk", "ZERO (No iptables/sysctl used)")
    table.add_row("Relayed Safe Packets", f"{stats.total_forwarded:,} Pkts")
    table.add_row("Last Raw Packet Size", f"{stats.last_packet_len} Bytes")
    table.add_row("Egress Target Server", f"{TARGET_SERVER_IP}:{TARGET_SERVER_PORT}")
    return table


def packet_processor(pkt):
    """
    🌟 纯 Python 异步回调核心
    网卡硬件收到符合 BPF 过滤条件的包时，直接触发此函数。
    """
    try:
        # Scapy 抓到的是全装二层以太网帧，pkt.canvas 或 bytes(pkt) 包含完整原始数据
        raw_frame = bytes(pkt)
        stats.last_packet_len = len(raw_frame)
        stats.total_forwarded += 1

        # 🌟 工业级套娃：把完整的 L2/L3 报文当做 Payload，直接用标准 UDP 发射给 130！
        udp_tx_sock.sendto(raw_frame, (TARGET_SERVER_IP, TARGET_SERVER_PORT))

    except Exception:
        pass


def start_scapy_plane(live_updater):
    """启动 Scapy 内置的高性能内核 BPF 过滤器"""
    
    # 🌟 核心绝杀点：利用内核原生 BPF 表达式过滤端口。
    # 这会在网卡驱动层直接刷掉杂质流量，根本不会把非目标流量带入 Python，保障系统绝对不卡！
    bpf_filter_str = f"udp dst port 52719"
    
    # 开始潜伏抓包
    sniff(
        iface=LISTEN_INTERFACE,
        filter=bpf_filter_str,
        prn=packet_processor,     # 收到包后的回调函数
        store=0,                  # 🌟 关键：设置 store=0 强制内存零积压，抓完即丢，不留内存历史，防止内存泄露
        stop_filter=lambda p: False
    )


def main():
    if os.getuid() != 0:
        console.print("❌ [Security] Scapy Layer-2 operations require root: sudo $(which uv) run ...")
        sys.exit(1)

    # 点火 Live TUI 渲染
    with Live(build_dashboard(), auto_refresh=False, screen=True) as live:
        
        # 将 Scapy 扔进后台线程去死守网卡电信号
        scapy_thread = threading.Thread(
            target=start_scapy_plane, 
            args=(live,), 
            daemon=True
        )
        scapy_thread.start()

        try:
            while True:
                # 刷新主界面统计
                live.update(build_dashboard(), refresh=True)
                import time
                time.sleep(0.1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Gateway engine safely shutting down...[/yellow]")

if __name__ == "__main__":
    main()