"""
Red Gateway - Terminal User Interface Presentation Layer.
Handles asynchronous rendering grids using Rich.Live displays.
"""

from rich.align import Align
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from red.engine import EngineTelemetry


class GatewayDashboard:
    """Manages structural layout building for terminal matrix updates."""
    
    def __init__(self, eth1: str, eth2: str, is_loopback: bool, telemetry: EngineTelemetry):
        self.eth1 = eth1
        self.eth2 = eth2
        self.is_loopback = is_loopback
        self.telemetry = telemetry

    def generate_renderable(self) -> Panel:
        """Constructs an isolated, zero-flicker table layout frame based on current telemetry state."""
        table = Table(
            title="🛰️ RED GATEWAY CORE - HIGH THROUGHPUT FORWARDING MATRIX",
            title_style="bold cyan",
            expand=True
        )
        
        table.add_column("⚙️ System Topologies & Vectors", justify="center", style="green")
        table.add_column("📊 Live Dynamic Telemetry Metrics", justify="center", style="yellow bold")

        # Select UI tags based on network topology
        mode_tag = "[bold red]SINGLE-NIC UDP PAYLOAD ENCAPSULATION[/bold red]" if self.is_loopback else "[bold green]DUAL-NIC TRANSPARENT PHYSICAL BRIDGE[/bold green]"
        
        table.add_row("Operational Interface Gateway Mode", mode_tag)
        table.add_row("Hardware Boundaries Bond", f"NIC_1: [cyan]{self.eth1}[/cyan] <---> NIC_2: [cyan]{self.eth2}[/cyan]")
        
        if not self.is_loopback:
            table.add_row(f"Forward Vectors [{self.eth1} -> {self.eth2}] Combined Count", f"{self.telemetry.eth1_to_eth2_pkts:,} Pkts")
            table.add_row(f"Forward Vectors [{self.eth2} -> {self.eth1}] Combined Count", f"{self.telemetry.eth2_to_eth1_pkts:,} Pkts")
        else:
            table.add_row("Encapsulated Raw -> UDP Loopback Transmissions", f"{self.telemetry.loopback_udp_pkts:,} Pkts")
            
        table.add_row("Latest Observed Packet Frame Size", f"{self.telemetry.last_packet_bytes} Bytes")
        table.add_row("Latest Observed Link-Layer Protocol", str(self.telemetry.last_protocol))

        return Panel(
            Align.center(table),
            title="[bold yellow]Core Network Sandbox Telemetry Station[/bold yellow]",
            border_style="cyan"
        )