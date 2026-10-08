import argparse
import json
from urllib.request import urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a deployed Carevia release.")
    parser.add_argument("base_url")
    parser.add_argument("--expected-release", default="")
    args = parser.parse_args()

    health_url = f"{args.base_url.rstrip('/')}/api/health/"
    with urlopen(health_url, timeout=15) as response:  # noqa: S310
        payload = json.load(response)

    if response.status != 200 or payload.get("status") != "ok":
        raise SystemExit(f"Unhealthy response from {health_url}: {payload}")
    if args.expected_release and payload.get("release") != args.expected_release:
        raise SystemExit(
            f"Release mismatch: expected {args.expected_release}, got {payload.get('release')}"
        )

    print(f"Carevia healthy: release={payload.get('release', 'unknown')}")


if __name__ == "__main__":
    main()
