"""
Red Network Plane - Industrial-Grade High-Speed Traffic Injector.
Features synchronized asynchronous telemetry and viewport-centered Rich UI.
"""

import argparse
import socket
import sys
import threading
import time
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.align import Align
from rich.panel import Panel

console = Console()

class ClientTelemetry:
    def __init__(self, target_count):
        self.transmitted_pkts = 0
        self.start_time = time.time()
        self.is_running = True
        self.target_count = target_count
        self.current_pps = 0.0
        self.last_pkt_count = 0
        self.last_check_time = time.time()

    def calculate_pps(self):
        now = time.time()
        duration = now - self.last_check_time
        if duration >= 0.5:
            delta = self.transmitted_pkts - self.last_pkt_count
            self.current_pps = delta / duration
            self.last_pkt_count = self.transmitted_pkts
            self.last_check_time = now

def build_centered_ui(stats: ClientTelemetry, args) -> Align:
    """Renders a layout precisely locked to the horizontal center of the terminal."""
    elapsed = time.time() - stats.start_time
    total_mb = (stats.transmitted_pkts * args.size) / (1024 * 1024)
    avg_pps = stats.transmitted_pkts / elapsed if elapsed > 0 else 0

    table = Table(show_header=False, expand=True, border_style="bright_blue")
    table.add_column("Key", style="cyan", width=30)
    table.add_column("Value", style="green", justify="right")

    table.add_row("Engine Target Grid", f"{args.ip}:{args.port}")
    table.add_row("Frame Dimension Bound", f"{args.size} Bytes")
    table.add_row("Sequence Lifetime", f"{elapsed:.2f} Seconds")
    table.add_row("Aggregated Outbound", f"{stats.transmitted_pkts:,} Packets")
    table.add_row("Volumetric Throughput", f"{total_mb:.4f} MB")
    table.add_row("Instantaneous Velocity", f"[bold red]{stats.current_pps:,.2f} Pkts/Sec[/bold red]")
    table.add_row("Steady-State Performance", f"{avg_pps:,.2f} Pkts/Sec")

    panel = Panel(
        table, 
        title="[bold bright_blue]🛰️ RED INJECTOR CORE v2.6[/bold bright_blue]", 
        border_style="bright_blue",
        width=70
    )
    return Align.center(panel, vertical="middle")

def injection_loop(tx_sock, payload, args, stats: ClientTelemetry):
    target = (args.ip, args.port)
    while stats.is_running:
        try:
            tx_sock.sendto(payload, target)
            stats.transmitted_pkts += 1
            if args.count > 0 and stats.transmitted_pkts >= args.count:
                stats.is_running = False
                break
            if args.rate > 0:
                time.sleep(args.rate)
        except Exception:
            stats.is_running = False

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-i", "--ip", type=str, default="192.168.211.129", help="Gateway IP Address.")
    parser.add_argument("-p", "--port", type=int, default=52719, help="Target Port.")
    parser.add_argument("-s", "--size", type=int, default=256, help="Payload dimensions.")
    parser.add_argument("-c", "--count", type=int, default=0, help="Total execution limit (0=continuous).")
    parser.add_argument("-r", "--rate", type=float, default=0.0, help="Pacing throttling interval.")
    args = parser.parse_args()

    tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
    dummy_payload = b"\x00" * args.size
    stats = ClientTelemetry(target_count=args.count)

    engine_thread = threading.Thread(target=injection_loop, args=(tx_sock, dummy_payload, args, stats), daemon=True)
    engine_thread.start()

    with Live(build_centered_ui(stats, args), auto_refresh=False, screen=True) as live:
        try:
            while stats.is_running:
                stats.calculate_pps()
                live.update(build_centered_ui(stats, args), refresh=True)
                time.sleep(0.1)
        except KeyboardInterrupt:
            stats.is_running = False

    tx_sock.close()

if __name__ == "__main__":
    main()