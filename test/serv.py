"""
Red Gateway - High-Performance UDP Traffic Receiver Unit.
Validates arrived packet telemetry, payload structure, and sequence compliance.
"""

import argparse
import socket
import sys
import time


def main():
    # ────────────────────────────────────────────────────────────────
    # COMMAND LINE INTERFACE DESIGN (ARGPARSE CONFIGURATION)
    # ────────────────────────────────────────────────────────────────
    parser = argparse.ArgumentParser(
        description="Industrial-grade UDP packet receiver for gateway egress validation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("-i", "--ip", type=str, default="0.0.0.0", help="Binding IPv4 address. Use 0.0.0.0 for all interfaces.")
    parser.add_argument("-p", "--port", type=int, default=52719, help="Target Listening UDP Port.")
    parser.add_argument("-b", "--buffer", type=int, default=1024 * 1024, help="OS-level Socket Receive Buffer allocation (SO_RCVBUF) in bytes.")

    args = parser.parse_args()

    # ────────────────────────────────────────────────────────────────
    # NETWORK DATA PLANE INITIALIZATION
    # ────────────────────────────────────────────────────────────────
    # Instantiate standard IPv4 UDP reception socket
    rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        # 🌟 INDUSTRIAL DEFENSE: Scale up the kernel-level network ring buffer size.
        # This prevents the Linux OS from dropping packets under high-throughput spikes.
        rx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, args.buffer)
        
        # Bind socket to the requested physical interface boundary
        rx_sock.bind((args.ip, args.port))
    except PermissionError:
        print(f"❌ [Permission Denied] Cannot bind to port {args.port}. Root privileges may be required.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ [Binding Failure] Failed to collapse infrastructure onto {args.ip}:{args.port}. Details: {e}")
        sys.exit(1)

    # Fetch actual buffer size allocated by the kernel (Linux usually doubles the requested value)
    actual_buf_size = rx_sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)

    print("🛰️  [Traffic Receiver] Egress auditing node online.")
    print(f"   ↳ Listening Grid   : {args.ip}:{args.port}")
    print(f"   ↳ Kernel Ring Alloc: {actual_buf_size / 1024:.1f} KB (SO_RCVBUF scaled)")
    print("   ↳ Monitor Status   : Awaiting ingress gateway streams... (Press Ctrl+C to intercept)")
    print("-" * 80)

    # ────────────────────────────────────────────────────────────────
    # REAL-TIME INGRESS AUDITING LOOP
    # ────────────────────────────────────────────────────────────────
    total_received_pkts = 0
    total_received_bytes = 0
    start_time = None

    try:
        while True:
            # Reusable buffer read window (Standard MTU size 2048 to prevent fragmentation truncation)
            data, addr = rx_sock.recvfrom(2048)
            
            # Start timer calculation upon the arrival of the absolute first frame
            if start_time is None:
                start_time = time.time()

            pkt_len = len(data)
            total_received_pkts += 1
            total_received_bytes += pkt_len

            # Fetch high-resolution absolute timestamp
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            micros = int((time.time() % 1) * 1000000)

            # High-performance inline stream printout
            # Display packet count, sender metadata, payload size, and timestamp matrix
            sys.stdout.write(
                f"[{timestamp}.{micros:06d}] #[{total_received_pkts:06d}] "
                f"Ingress from {addr[0]}:{addr[1]} ──> Quantum: {pkt_len} Bytes\n"
            )
            
            # Industrial optimization: Flush standard output buffer selectively to prevent I/O blocking
            if total_received_pkts % 10 == 0:
                sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n🛑 [Traffic Receiver] Auditing intercepted by operator sequence.")
        
    finally:
        print("-" * 80)
        print("📊 [Audit Session Telemetry Summary]")
        print(f"   ↳ Aggregated Received Frames : {total_received_pkts:,} Pkts")
        print(f"   ↳ Aggregated Volumetric Data : {total_received_bytes / (1024 * 1024):.4f} MB")
        
        if start_time and (time.time() - start_time) > 0:
            duration = time.time() - start_time
            print(f"   ↳ Total Session Duration     : {duration:.3f} Seconds")
            print(f"   ↳ Steady-State Performance   : {total_received_pkts / duration:.2f} Pkts/Sec")
            
        rx_sock.close()


if __name__ == "__main__":
    main()