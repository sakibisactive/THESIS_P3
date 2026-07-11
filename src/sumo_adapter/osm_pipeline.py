"""OSM map compiler pipeline invoking netconvert to build SUMO networks."""

import shutil
import subprocess

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class OSMPipeline:
    """Handles parsing and compiling OpenStreetMap (.osm) files into
    SUMO network (.net.xml) files.
    """

    @staticmethod
    def compile_osm(
        osm_path: str,
        output_net_path: str,
        remove_geometry: bool = True,
        join_junctions: bool = True,
    ) -> None:
        """Invokes netconvert command-line compiler as a subprocess.

        Args:
            osm_path: Absolute or relative path to the .osm source map.
            output_net_path: Destination path for the compiled SUMO .net.xml file.
            remove_geometry: Simplify segment shapes for routing performance.
            join_junctions: Consolidate clustered intersections.
        """
        netconvert_bin = shutil.which("netconvert")
        if not netconvert_bin:
            logger.error("SUMO netconvert binary was not found in PATH.")
            raise RuntimeError(
                "netconvert tool is missing. Please ensure SUMO is installed."
            )

        cmd = [
            netconvert_bin,
            "--osm-files",
            osm_path,
            "--output-file",
            output_net_path,
        ]

        if remove_geometry:
            cmd.append("--geometry.remove")
        if join_junctions:
            cmd.append("--junctions.join")

        logger.info(f"Compiling OSM map via command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info("OSM compilation completed successfully.")
            logger.debug(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"netconvert failed with exit code {e.returncode}")
            logger.error(e.stderr)
            raise RuntimeError(
                f"netconvert compilation failed: {e.stderr}"
            ) from e
