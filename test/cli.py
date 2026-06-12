"""
Red Gateway - High-Speed UDP Traffic Injector Test Unit.
Generates structured dummy payloads to stress-test raw packet forwarding engines.
Optimized with Rich TUI interface.
"""

import argparse
import os
import socket
import sys
import threading
import time
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn

console = Console()

# ───────────────────────────────────────────────────────────────────────
# 🌟 TELEMETRY MATRIX (全局状态监视)
# ───────────────────────────────────────────────────────────────────────
class InjectorStats:
    def __init__(self, target_count):
        self.transmitted_pkts = 0
        self.start_time = time.time()
        self.is_running = True
        self.target_count = target_count
        self.current_pps = 0.0
        self.last_pkt_count = 0
        self.last_check_time = time.time()

    def update_pps(self):
        """每隔一段时间计算一次瞬时每秒发包数 (PPS)"""
        now = time.time()
        duration = now - self.last_check_time
        if duration >= 0.5:  # 每 0.5 秒计算一次
            delta_pkts = self.transmitted_pkts - self.last_pkt_count
            self.current_pps = delta_pkts / duration
            self.last_pkt_count = self.transmitted_pkts
            self.last_check_time = now


def build_dashboard(stats: InjectorStats, args) -> Table:
    """动态构建极具工业感的 Rich 大屏"""
    table = Table(title="[bold orange3]Red Gateway[/bold orange3] - Traffic Injector Core", expand=True)
    table.add_column("Vector Target", style="cyan", justify="left")
    table.add_column("Real-Time Telemetry Metrics", style="green", justify="right")

    # 基础静态配置
    table.add_row("Target Destination Endpoint", f"[bold white]{args.ip}:{args.port}[/bold white]")
    table.add_row("Frame Dimension (Payload)", f"{args.size} Bytes")
    table.add_row("Injection Throttle Backoff", f"{f'{args.rate}s Delay' if args.rate > 0 else '⚡ Wire-Speed (Zero-Delay)'}")
    
    table.add_section() # 物理分界线
    
    # 实时动态指标
    elapsed = time.time() - stats.start_time
    total_mb = (stats.transmitted_pkts * args.size) / (1024 * 1024)
    avg_pps = stats.transmitted_pkts / elapsed if elapsed > 0 else 0
    
    table.add_row("Elapsed Sequence Duration", f"{elapsed:.2f} Seconds")
    table.add_row("Aggregated Transmitted Frames", f"[bold yellow]{stats.transmitted_pkts:,}[/bold yellow] Pkts")
    table.add_row("Aggregated Volumetric Data", f"{total_mb:.4f} MB")
    table.add_row("Instantaneous Blast Speed", f"[bold red]{stats.current_pps:,.2f}[/bold red] Pkts/Sec")
    table.add_row("Average Engine Performance", f"{avg_pps:,.2f} Pkts/Sec")

    # 如果是有限包模式，拉一个进度条进去
    if args.count > 0:
        pct = min((stats.transmitted_pkts / args.count) * 100, 100.0)
        table.add_row("Sequence Block Progress", f"[{pct:.1f}%] {'█' * int(pct//5)}{'░' * (20 - int(pct//5))}")

    return table


def blast_engine(tx_sock, dummy_payload, args, stats: InjectorStats):
    """底层的发包死循环，剥离一切 I/O 阻碍，全速冲刺"""
    try:
        target_endpoint = (args.ip, args.port)
        
        while stats.is_running:
            tx_sock.sendto(dummy_payload, target_endpoint)
            stats.transmitted_pkts += 1

            # 有限包计数退出
            if args.count > 0 and stats.transmitted_pkts >= args.count:
                stats.is_running = False
                break

            # 延迟控制
            if args.rate > 0:
                time.sleep(args.rate)
                
    except Exception as e:
        stats.is_running = False


def main():
    parser = argparse.ArgumentParser(
        description="Industrial-grade UDP packet generator with Rich interface.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-i", "--ip", type=str, default="127.0.0.1", help="Target Destination IPv4 address.")
    parser.add_argument("-p", "--port", type=int, default=52719, help="Target Destination UDP Port.")
    parser.add_argument("-s", "--size", type=int, default=256, help="Byte size of each generated frame.")
    parser.add_argument("-c", "--count", type=int, default=0, help="Total packets. Set to 0 for continuous loop.")
    parser.add_argument("-r", "--rate", type=float, default=0.0, help="Interval delay in seconds.")

    args = parser.parse_args()

    if args.size < 0 or args.size > 65507:
        console.print(f"[bold red]❌ [Payload Bound Error] UDP max payload limit is 65507. Requested: {args.size}[/bold red]")
        sys.exit(1)

    # 物理初始化网络平面
    tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # 扩容系统级发送缓冲区，防止高频时被系统卡壳
    tx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
    
    dummy_payload = b"\x00" * args.size
    stats = InjectorStats(target_count=args.count)

    # 1. 将全速发包循环扔进后台线程，解耦主控制台渲染
    engine_thread = threading.Thread(
        target=blast_engine, 
        args=(tx_sock, dummy_payload, args, stats),
        daemon=True
    )
    engine_thread.start()

    # 2. 主线程启动 Rich Live 异步渲染视图
    with Live(build_dashboard(stats, args), auto_refresh=False, screen=True) as live:
        try:
            while stats.is_running:
                stats.update_pps()
                live.update(build_dashboard(stats, args), refresh=True)
                time.sleep(0.1)  # 精准控制：限制 UI 渲染层每秒只刷新 10 次，绝不吃发包性能！
        except KeyboardInterrupt:
            stats.is_running = False
            console.print("\n[bold yellow]🛑 [Traffic Injector] Transmission aborted by operator sequence.[/bold yellow]")

    # 3. 退出收尾总结
    elapsed = time.time() - stats.start_time
    rate_fps = stats.transmitted_pkts / elapsed if elapsed > 0 else stats.transmitted_pkts
    
    # 完美的最终落幕报告
    summary_table = Table(title="📊 Final Mission Telemetry Summary", show_header=False, border_style="orange3")
    summary_table.add_row("Total Transmitted Packets", f"{stats.transmitted_pkts:,} Pkts")
    summary_table.add_row("Total Volumetric Data", f"{(stats.transmitted_pkts * args.size) / (1024 * 1024):.2f} MB")
    summary_table.add_row("Total Execution Duration", f"{elapsed:.3f} Seconds")
    summary_table.add_row("Steady-State Performance", f"[bold red]{rate_fps:,.2f} Pkts/Sec[/bold red]")
    
    console.print("\n")
    console.print(summary_table)
    tx_sock.close()


if __name__ == "__main__":
    main()