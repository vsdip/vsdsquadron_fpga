"""
  Test different "apio" commands
"""

from os import listdir, chdir
from test.conftest import ApioRunner
import pytest


# -- Entry point for apio commands.
from apio.commands.raw import cli as apio_raw
from apio.commands.upgrade import cli as apio_upgrade
from apio.commands.system import cli as apio_system
from apio.commands.packages import cli as apio_packages


# R0801: Similar lines in 2 files
# pylint: disable=R0801
def test_utilities(apio_runner: ApioRunner):
    """Tests apio utility commands."""

    # -- If the option 'offline' is passed, the test is skip
    # -- (This test is slow and requires internet connectivity)
    if apio_runner.offline_flag:
        pytest.skip("requires internet connection")

    with apio_runner.in_disposable_temp_dir():

        # -- Config the apio test environment.
        proj_dir, _, packages_dir = apio_runner.setup_env()

        # -- Create and change to project dir.
        proj_dir.mkdir(exist_ok=False)
        chdir(proj_dir)

        # -- Install all packages
        result = apio_runner.invoke(apio_packages, ["--install", "--verbose"])
        apio_runner.assert_ok(result)
        assert "'examples' installed successfully" in result.output
        assert "'oss-cad-suite' installed successfully" in result.output
        assert listdir(packages_dir / "examples")
        assert listdir(packages_dir / "tools-oss-cad-suite")

        # -- Run 'apio upgrade'
        result = apio_runner.invoke(apio_upgrade)
        apio_runner.assert_ok(result)
        assert "Lastest Apio stable version" in result.output

        # -- Run 'apio system --info'
        result = apio_runner.invoke(apio_system, ["--info"])
        apio_runner.assert_ok(result)
        assert "Apio version" in result.output

        # -- Run 'apio raw --env "nextpnr-ice40 --help"
        result = apio_runner.invoke(
            apio_raw, ["--env", "nextpnr-ice40 --help"], input="exit"
        )
        apio_runner.assert_ok(result)
