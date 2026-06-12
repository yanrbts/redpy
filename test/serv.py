"""
Red Network Plane - Advanced Asynchronous Deep Packet Decapsulator & Feedback Reflector.
Processes incoming UDP tunnel arrays and crafts symmetric backward response primitives.
"""

import argparse
import os
import sys
import socket
import threading
import time
from scapy.all import IP, UDP, Ether
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.align import Align
from rich.panel import Panel

console = Console()

class ServerTelemetry:
    total_processed = 0
    total_reflected = 0
    extracted_payload_len = 0
    inner_src_route = "0.0.0.0"
    inner_dst_route = "0.0.0.0"

stats = ServerTelemetry()

# Standard L3 outback UDP Socket configured to punch feedback paths back to Gateway 129
gateway_tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def build_centered_ui(args) -> Align:
    table = Table(show_header=False, expand=True, border_style="bright_green")
    table.add_column("Metric Identifier", style="yellow", width=30)
    table.add_column("Data Element", style="green", justify="right")

    table.add_row("Receiver Context Node", f"Audit Server Core bound on port {args.port}")
    table.add_row("Peeled Tunnel Packets", f"{stats.total_processed:,} Frames")
    table.add_row("Reflected Response Waves", f"{stats.total_reflected:,} Packets")
    table.add_row("Inspected Inner Mass", f"{stats.extracted_payload_len} Bytes")
    table.add_row("Extracted Ingress Path", f"[bold cyan]{stats.inner_src_route} -> {stats.inner_dst_route}[/bold cyan]")

    panel = Panel(
        table, 
        title="[bold bright_green]🛰️ RED AUDIT SERVER DECAPSULATOR[/bold bright_green]", 
        border_style="bright_green",
        width=72
    )
    return Align.center(panel, vertical="middle")

def network_plane_receiver(args):
    rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, args.buffer)
    rx_sock.bind(("0.0.0.0", args.port))

    gateway_return_target = ("192.168.211.129", 52721)

    while True:
        try:
            # Capture incoming capsule payload pushed down from Gateway XDP layer
            encapsulated_data, _ = rx_sock.recvfrom(4096)
            
            # De-capsulate the payload, treating it explicitly as a Layer-2 Ethernet Frame
            inner_frame = Ether(encapsulated_data)
            
            if inner_frame.haslayer(IP):
                inner_ip = inner_frame[IP]
                stats.inner_src_route = inner_ip.src
                stats.inner_dst_route = inner_ip.dst
                
                if inner_ip.haslayer(UDP):
                    stats.extracted_payload_len = len(inner_ip[UDP].payload)
                    stats.total_processed += 1

                    # 🌟 REFLECTION MATRIX OPERATION: Construct a symmetric response packet
                    # Reverses IP endpoints and shifts operational port grids matching deep L4 definitions
                    response_packet = (
                        IP(src=inner_ip.dst, dst=inner_ip.src) /
                        UDP(sport=inner_ip[UDP].dport, dport=inner_ip[UDP].sport) /
                        b"ACK_STREAM_VERIFIED_SECURE_PAYLOAD_MATRIX"
                    )

                    # Export raw response structure bytes back into the gateway's response-handler port
                    gateway_tx_sock.sendto(bytes(response_packet), gateway_return_target)
                    stats.total_reflected += 1
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-p", "--port", type=int, default=52720, help="Egress Auditing Target Interface port.")
    parser.add_argument("-b", "--buffer", type=int, default=2*1024*1024, help="Network SO_RCVBUF size limits.")
    args = parser.parse_args()

    # Fire off network processing engines detached from UI scheduling blocking
    worker = threading.Thread(target=network_plane_receiver, args=(args,), daemon=True)
    worker.start()

    with Live(build_centered_ui(args), auto_refresh=False, screen=True) as live:
        try:
            while True:
                live.update(build_centered_ui(args), refresh=True)
                time.sleep(0.1)
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Audit Server node safely offline.[/bold yellow]")

if __name__ == "__main__":
    main()