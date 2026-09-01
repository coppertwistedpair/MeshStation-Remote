#!/usr/bin/env python3
"""Entry point: runs the RTL-SDR -> ZMQ PUB remote receiver for MeshStation."""
from meshrx.run_engine import main

if __name__ == "__main__":
    raise SystemExit(main())
