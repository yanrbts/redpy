"""
Red Gateway - Main Application Orchestrator.
Maintains setup verification, thread scheduling, and clean shutdown procedures.
"""

import asyncio
import os
import sys
import threading
from rich.live import Live
from red.engine import EngineTelemetry, raw_packet_forwarder
from red.tui import GatewayDashboard


async def main():
    # Enforce kernel root permission guardrail required to bind AF_PACKET raw sockets
    if os.getuid() != 0:
        print("❌ [Security Halt] Raw socket operations require administrative privileges.")
        print("   Please execute using: sudo uv run python red/main.py")
        sys.exit(1)

    # ────────────────────────────────────────────────────────
    # Industrial Configuration Block
    # Change these values to match target network interface names
    # Set both identical to trigger single-NIC UDP payload fallback loop
    # ────────────────────────────────────────────────────────
    ETH1_NAME = "eth0"
    ETH2_NAME = "eth0"
    
    is_loopback = (ETH1_NAME == ETH2_NAME)

    # Force network cards into Promiscuous Mode to catch non-local IP addresses
    os.system(f"ip link set dev {ETH1_NAME} promisc on >/dev/null 2>&1")
    if not is_loopback:
        os.system(f"ip link set dev {ETH2_NAME} promisc on >/dev/null 2>&1")

    # Allocate cross-boundary shared telemetry data structure (Global heap reference)
    telemetry = EngineTelemetry()

    # Launch asynchronous high-performance data plane worker threads
    if not is_loopback:
        # Thread A: Handles [ETH1 Ingress -> ETH2 Egress]
        t1 = threading.Thread(
            target=raw_packet_forwarder, 
            args=(ETH1_NAME, ETH2_NAME, telemetry, False), 
            daemon=True
        )
        # Thread B: Handles [ETH2 Ingress -> ETH1 Egress]
        t2 = threading.Thread(
            target=raw_packet_forwarder, 
            args=(ETH2_NAME, ETH1_NAME, telemetry, False), 
            daemon=True
        )
        t1.start()
        t2.start()
    else:
        # Isolated Thread: Handles Single-NIC Loopback Encapsulation
        t_loop = threading.Thread(
            target=raw_packet_forwarder, 
            args=(ETH1_NAME, ETH1_NAME, telemetry, True), 
            daemon=True
        )
        t_loop.start()

    # Instantiate UI layout compiler
    dashboard = GatewayDashboard(ETH1_NAME, ETH2_NAME, is_loopback, telemetry)

    # Execute non-flicker alternate screen console render block
    # Frequency locked to 15Hz sweet spot (66ms sleep cycle) to ensure zero UI cpu impact
    with Live(dashboard.generate_renderable(), auto_refresh=False, screen=True) as live:
        try:
            while telemetry.is_running:
                live.update(dashboard.generate_renderable(), refresh=True)
                await asyncio.sleep(0.066)
        except asyncio.CancelledError:
            pass
        finally:
            telemetry.is_running = False
            # Clean up promiscuous settings on interface teardown
            os.system(f"ip link set dev {ETH1_NAME} promisc off >/dev/null 2>&1")
            if not is_loopback:
                os.system(f"ip link set dev {ETH2_NAME} promisc off >/dev/null 2>&1")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Gateway gracefully halted. Interfaces restored.")