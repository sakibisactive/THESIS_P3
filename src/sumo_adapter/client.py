"""SUMO TraCI client managing simulation subprocess connection and
teardown lifecycle.
"""

from typing import Any

import traci  # type: ignore[import-untyped]

from src.utils.config import SimulationConfig
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SumoClient:
    """Manages the startup, connection, and teardown of the SUMO simulator via TraCI."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self._connected = False

    def start(self, net_file: str, route_file: str | None = None) -> None:
        """Starts SUMO and establishes the TraCI connection.

        Args:
            net_file: Path to the SUMO net.xml file.
            route_file: Optional path to route/trip xml definitions.
        """
        if self._connected:
            return

        # Determine binary
        binary = self.config.sumo_binary
        if self.config.use_gui:
            if binary == "sumo":
                binary = "sumo-gui"

        # Construct start command
        cmd = [
            binary,
            "-n",
            net_file,
            "--step-length",
            str(self.config.step_length),
            "--seed",
            str(self.config.seed),
            "--no-warnings",
            "--no-step-log",
        ]
        if route_file:
            cmd.extend(["-r", route_file])
        if self.config.real_time_factor > 0:
            cmd.extend(["--real-time-factor", str(self.config.real_time_factor)])

        try:
            import io
            import os
            import sys
            from contextlib import redirect_stdout, redirect_stderr

            # Auto-detect or override invalid SUMO_HOME to prevent XML validation warnings
            sumo_home = os.environ.get("SUMO_HOME", "")
            if not sumo_home or not os.path.isdir(sumo_home):
                for candidate in ["/usr/share/sumo", "/usr/local/share/sumo"]:
                    if os.path.isdir(candidate):
                        os.environ["SUMO_HOME"] = candidate
                        break

            f_null = io.StringIO()
            try:
                # Redirect stdout/stderr to capture "Retrying in 1 seconds" and warnings
                with redirect_stdout(f_null), redirect_stderr(f_null):
                    traci.start(cmd, port=self.config.traci_port)
                self._connected = True
                logger.info("Successfully connected to SUMO via TraCI.")
            except Exception as e:
                # If connection fails, log the captured outputs for diagnostics
                captured = f_null.getvalue()
                if captured:
                    logger.error(f"SUMO/TraCI startup output:\n{captured}")
                raise
        except Exception as e:
            logger.error(f"Failed to start SUMO / connect TraCI: {e}")
            raise RuntimeError(f"TraCI connection failed: {e}") from e

    def stop(self) -> None:
        """Closes the TraCI connection and terminates the SUMO process."""
        if not self._connected:
            return
        try:
            traci.close()
            logger.info("Closed TraCI connection.")
        except Exception as e:
            logger.warning(f"Error during traci.close(): {e}")
        finally:
            self._connected = False

    def step(self) -> None:
        """Advances the simulation by one step."""
        if not self._connected:
            raise RuntimeError("Not connected to SUMO.")
        try:
            traci.simulationStep()
        except Exception as e:
            logger.error(f"Error during simulation step: {e}")
            raise

    def is_connected(self) -> bool:
        """Returns True if connected to SUMO."""
        return self._connected

    def __enter__(self) -> "SumoClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()
