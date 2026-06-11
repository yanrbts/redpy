"""
Red Gateway - High-Speed UDP Traffic Injector Test Unit.
Generates structured dummy payloads to stress-test raw packet forwarding engines.
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
        description="Industrial-grade UDP packet generator for engineering validation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("-i", "--ip", type=str, default="127.0.0.1", help="Target Destination IPv4 address.")
    parser.add_argument("-p", "--port", type=int, default=52719, help="Target Destination UDP Port.")
    parser.add_argument("-s", "--size", type=int, default=256, help="Physical byte payload size of each generated frame.")
    parser.add_argument("-c", "--count", type=int, default=1, help="Total packets to transmit. Set to 0 or negative for continuous blasting.")
    parser.add_argument("-r", "--rate", type=float, default=0.0, help="Interval delay in seconds between packets (0.0 for maximum throttle).")

    args = parser.parse_args()

    # Enforce standard ethernet payload constraints (MTU boundary defenses)
    if args.size < 0 or args.size > 65507:
        print(f"❌ [Payload Bound Error] UDP max payload limit is 65507 bytes. Requested: {args.size}")
        sys.exit(1)

    print("🚀 [Traffic Injector] Initializing blast sequence vector...")
    print(f"   ↳ Target Endpoint : {args.ip}:{args.port}")
    print(f"   ↳ Frame Dimensions: {args.size} Bytes (Payload Data)")
    print(f"   ↳ Interval Backoff: {args.rate if args.rate > 0 else 'Zero-Delay (Wire-Speed)'}")
    print(f"   ↳ Mode Context    : {'Continuous Loop' if args.count <= 0 else f'Finite Block ({args.count} Pkts)'}")
    print("-" * 64)

    # ────────────────────────────────────────────────────────────────
    # DATA PLANE INJECTION ENGINE
    # ────────────────────────────────────────────────────────────────
    # Instantiate standard IPv4 UDP transmission socket
    tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Pre-allocate zeroed byte block to eliminate heap instantiation latency inside the critical loop
    dummy_payload = b"\x00" * args.size
    
    transmitted_pkts = 0
    start_time = time.time()

    try:
        while True:
            # Blast block into the kernel routing ring buffer
            tx_sock.sendto(dummy_payload, (args.ip, args.port))
            transmitted_pkts += 1

            # Handle finite-count transmission exit flags
            if args.count > 0 and transmitted_pkts >= args.count:
                break

            # Throttle injection pace if dynamic backoff rate is enforced
            if args.rate > 0:
                time.sleep(args.rate)

    except KeyboardInterrupt:
        print("\n🛑 [Traffic Injector] Transmission aborted by operator sequence.")
        
    finally:
        elapsed = time.time() - start_time
        # Prevent zero-division fault if script was aborted instantaneously
        rate_fps = transmitted_pkts / elapsed if elapsed > 0 else transmitted_pkts
        
        print("-" * 64)
        print("📊 [Injection Complete Telemetry Summary]")
        print(f"   ↳ Total Transmitted Packets: {transmitted_pkts:,} Pkts")
        print(f"   ↳ Total Transmitted Volumetric Data: {(transmitted_pkts * args.size) / (1024 * 1024):.2f} MB")
        print(f"   ↳ Total Execution Duration : {elapsed:.3f} Seconds")
        print(f"   ↳ Aggregated Engine Speed  : {rate_fps:.2f} Pkts/Sec")
        
        tx_sock.close()


if __name__ == "__main__":
    main()