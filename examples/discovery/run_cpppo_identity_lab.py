"""Run the pinned cpppo simulator with only TwinForge's lab configuration."""

from __future__ import annotations

from pathlib import Path

from cpppo.server.enip import defaults
from cpppo.server.enip.main import main as cpppo_main


def main() -> int:
    """Bind cpppo to loopback without loading ambient default config files."""
    config_path = Path(__file__).with_name("cpppo_identity_lab.cfg").resolve()
    defaults.config_files.clear()
    return cpppo_main(
        argv=[
            "--config",
            str(config_path),
            "--address",
            "127.0.0.1:44818",
            "--no-udp",
            "--address-output",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
