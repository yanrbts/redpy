"""
Red Gateway - High-Performance Data Plane Engine.
Handles low-level AF_PACKET raw socket bridging with strict UDP port filtering.
"""

import os
import socket
import struct
import threading
from dataclasses import dataclass


@dataclass
class EngineTelemetry:
    """Thread-safe telemetry structure shared globally via references."""
    eth1_to_eth2_pkts: int = 0
    eth2_to_eth1_pkts: int = 0
    loopback_udp_pkts: int = 0
    last_packet_bytes: int = 0
    last_protocol: str = "NONE"
    is_running: bool = True


# Standard Linux constant to capture all Link-Layer Ethernet frames
ETH_P_ALL = 0x0003  
# Target industrial filtering metric
TARGET_UDP_PORT = 52719


def raw_packet_forwarder(rx_iface: str, tx_iface: str, telemetry: EngineTelemetry, is_loopback: bool) -> None:
    """
    Spawns an infinite ingress-to-egress forwarding loop.
    Enforces kernel-level-like manual offset checking to filter precise UDP streams.
    """
    try:
        # Bind raw socket to the physical Link-Layer ingress interface
        rx_sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
        rx_sock.bind((rx_iface, 0))
        
        if is_loopback:
            tx_sock = rx_sock
            # Pre-allocate standard UDP socket for loopback payload injection
            udp_tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        else:
            # Bind separate raw socket to egress interface for symmetric bridge
            tx_sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
            tx_sock.bind((tx_iface, 0))
            
    except PermissionError:
        telemetry.is_running = False
        return
    except Exception:
        telemetry.is_running = False
        return

    # Zero-allocation reusable memory buffer (Covers standard Jumbo MTU frames)
    packet_buffer = bytearray(2048)

    while telemetry.is_running:
        try:
            # Zero-copy memory buffer slice write directly from driver layer
            pkt_len, _ = rx_sock.recvfrom_into(packet_buffer)
            
            # ────────────────────────────────────────────────────────────────
            # INDUSTRIAL PROTOCOL SANITY CHECK & BOUNDARY FILTERING
            # Minimum boundaries: Eth(14) + IPv4(20) + UDP(8) = 42 bytes
            # ────────────────────────────────────────────────────────────────
            if pkt_len < 42:
                continue

            # Step 1: Check Layer 2 Ethernet Protocol type (Must be IPv4: 0x0800)
            eth_proto = struct.unpack("!H", packet_buffer[12:14])[0]
            if eth_proto != 0x0800:
                continue

            # Step 2: Check Layer 3 IP Protocol Identifier (Must be UDP: 17 / 0x11)
            # Offset 23 points exactly to the IPv4 Protocol block
            ip_proto = packet_buffer[23]
            if ip_proto != 17:
                continue

            # Step 3: Check Layer 4 UDP Destination Port Matrix
            # Assuming standard 20-byte IPv4 Header without dynamic options fields
            # Offset 36-38 captures the 16-bit network byte-order Destination Port
            dst_port = struct.unpack("!H", packet_buffer[36:38])[0]
            if dst_port != TARGET_UDP_PORT:
                continue

            # ────────────────────────────────────────────────────────────────
            # PACKET MATCHED -> ENTER FORWARDING PIPELINE
            # ────────────────────────────────────────────────────────────────
            telemetry.last_packet_bytes = pkt_len
            telemetry.last_protocol = f"UDP:{dst_port}"

            if not is_loopback:
                # ─── ROUTE A: Dual-Interface Symmetric Bridge ───
                tx_sock.send(packet_buffer[:pkt_len])
                if rx_iface == "eth1":
                    telemetry.eth1_to_eth2_pkts += 1
                else:
                    telemetry.eth2_to_eth1_pkts += 1
            else:
                # ─── ROUTE B: Single-Interface Loopback Tunnel ───
                ip_header = packet_buffer[14:34]
                iph = struct.unpack('!BBHHHBBH4s4s', ip_header)
                dst_ip = socket.inet_ntoa(iph[9])
                
                raw_payload = bytes(packet_buffer[:pkt_len])
                try:
                    # Forward target payload wrapped seamlessly to upstream nodes
                    udp_tx_sock.sendto(raw_payload, (dst_ip, 9999))
                    telemetry.loopback_udp_pkts += 1
                except socket.error:
                    pass

        except (socket.error, ValueError):
            continue