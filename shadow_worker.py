#!/usr/bin/env python3
"""Root convenience launcher for ShadowWorker CLI daemon.

Usage:
  python shadow_worker.py --server-url http://localhost:8800 --role legal_counsel
"""

from shadow_adapter.worker import main

if __name__ == "__main__":
    main()
