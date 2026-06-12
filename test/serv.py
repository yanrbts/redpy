"""
Red Gateway - High-Performance UDP Traffic Decapsulator & Receiver.
Automatically strips outbound layer-2/layer-3 tunnel framing natively in Python.
"""

import argparse
import os
import sys
import time
from scapy.all import sniff, IP, UDP, Ether
from rich.console import Console
from rich.table import Table
from rich.live import Live

console = Console()

# ───────────────────────────────────────────────────────────────────────
#   PARSER & BOUNDARY CONFIGURATION
# ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="High-performance Tunnel Decapsulator Node.")
parser.add_argument("-i", "--iface", type=str, default="ens33", help="Physical NIC to monitor.")
parser.add_argument("-p", "--port", type=int, default=52719, help="Tunnel Destination UDP Port to intercept.")
args = parser.parse_args()

class AuditTelemetry:
    total_tunnels_peeled = 0
    inner_payload_bytes = 0
    last_inner_src = "0.0.0.0"
    last_inner_dst = "0.0.0.0"

stats = AuditTelemetry()


def build_live_screen() -> Table:
    """精美 TUI 渲染面"""
    table = Table(title="[bold cyan]130 Audit Node[/bold cyan] - Decapsulation Plane", expand=True)
    table.add_column("Telemetry Metric", justify="left", style="magenta")
    table.add_column("De-capsulated Value", justify="right", style="green")
    
    table.add_row("Receiver Backend", "Scapy Kernel BPF + Deep Packet Dissector")
    table.add_row("Peeled Tunnel Packets", f"{stats.total_tunnels_peeled:,} Pkts")
    table.add_row("Last Inner Payload Size", f"{stats.inner_payload_bytes} Bytes")
    table.add_row("Extracted Inner Route", f"{stats.last_inner_src} ──> {stats.last_inner_dst}")
    return table


def tunnel_decap_processor(pkt):
    """
    🌟 核心脱壳核心
    当外层 UDP 52719 的套娃包落地 130 时，物理剥离外层，还原最里面 128 的核心数据
    """
    try:
        # 1. 安全边界检查：确保这个包带有 UDP 层
        if not pkt.haslayer(UDP):
            return

        # 2. 🌟 提取外层的 UDP 载荷（也就是网关网强行塞进来的整个二层二进制流）
        outer_udp_payload = bytes(pkt[UDP].payload)
        
        # 3. 降维打击：将这串二进制流重新还原成一个 Scapy 能够识别的二层以太网帧对象
        # 这一步叫“解套娃 / 脱壳”
        inner_frame = Ether(outer_udp_payload)
        
        # 4. 穿透审计：提取最核心的、128 打过来的原始三层 IP 资产
        if inner_frame.haslayer(IP):
            inner_ip = inner_frame[IP]
            stats.last_inner_src = inner_ip.src
            stats.last_inner_dst = inner_ip.dst
            
            # 5. 提取最核心的业务数据载荷
            if inner_ip.haslayer(UDP):
                inner_payload = bytes(inner_ip[UDP].payload)
                stats.inner_payload_bytes = len(inner_payload)
                stats.total_tunnels_peeled += 1

    except Exception:
        pass


def main():
    if os.getuid() != 0:
        console.print("❌ [Security] Packet dissection requires root privileges: sudo $(which uv) run ...")
        sys.exit(1)

    import threading
    
    # 🌟 告诉内核：只捕获发往本机的、端口为 52719 的常规套娃 UDP 包
    # 这样内核 BPF 会把杂质完全过滤，保障 130 系统绝对不卡！
    bpf_filter = f"udp dst port {args.port}"
    
    sniff_thread = threading.Thread(
        target=lambda: sniff(
            iface=args.iface,
            filter=bpf_filter,
            prn=tunnel_decap_processor,
            store=0
        ),
        daemon=True
    )
    sniff_thread.start()

    with Live(build_live_screen(), auto_refresh=False, screen=True) as live:
        try:
            while True:
                live.update(build_live_screen(), refresh=True)
                time.sleep(0.1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Auditing node gracefully detached.[/yellow]")


if __name__ == "__main__":
    main()