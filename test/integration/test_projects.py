"""
  Test different "apio" commands
"""

from os import listdir, chdir
from os.path import getsize
from pathlib import Path
from test.conftest import ApioRunner
import pytest

# -- Entry point for apio commands.
from apio.commands.clean import cli as apio_clean
from apio.commands.graph import cli as apio_graph
from apio.commands.test import cli as apio_test
from apio.commands.report import cli as apio_report
from apio.commands.lint import cli as apio_lint
from apio.commands.build import cli as apio_build
from apio.commands.packages import cli as apio_packages
from apio.commands.examples import cli as apio_examples


# R0801: Similar lines in 2 files
# pylint: disable=R0801
def _test_project(
    apio_runner: ApioRunner,
    *,
    example: str,
    testbench: str,
    binary: str,
    report_item: str,
):
    """A common project integration test. Invoked per each tested
    architecture.
    """

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

        # -- The current proj directory should be still empty
        assert not listdir(".")

        # -- Fetch example files to current directory
        result = apio_runner.invoke(
            apio_examples,
            ["--fetch-files", example],
        )
        apio_runner.assert_ok(result)
        assert f"Copying {example} example files" in result.output
        assert "have been successfully created!" in result.output
        assert getsize("apio.ini")

        # -- Remember the list of project files.
        project_files = listdir(".")

        # -- Build the project.
        result = apio_runner.invoke(apio_build)
        apio_runner.assert_ok(result)
        assert "SUCCESS" in result.output
        assert getsize(f"_build/{binary}")

        # -- Lint
        result = apio_runner.invoke(apio_lint)
        apio_runner.assert_ok(result)
        assert "SUCCESS" in result.output
        assert getsize("_build/hardware.vlt")

        # -- Test
        result = apio_runner.invoke(apio_test)
        apio_runner.assert_ok(result)
        assert "SUCCESS" in result.output
        assert getsize(f"_build/{testbench}.out")
        assert getsize(f"_build/{testbench}.vcd")

        # -- Report
        result = apio_runner.invoke(apio_report)
        apio_runner.assert_ok(result)
        assert "SUCCESS" in result.output
        assert report_item in result.output
        assert getsize("_build/hardware.pnr")

        # -- Graph svg
        result = apio_runner.invoke(apio_graph)
        apio_runner.assert_ok(result)
        assert "SUCCESS" in result.output
        assert getsize("_build/hardware.dot")
        assert getsize("_build/hardware.svg")

        # -- Clean
        result = apio_runner.invoke(apio_clean)
        apio_runner.assert_ok(result)
        assert "SUCCESS" in result.output
        assert not Path("_build").exists()

        # -- Check that we have exactly the original project files,
        assert set(listdir(".")) == set(project_files)


def test_project_ice40(apio_runner: ApioRunner):
    """Tests building and testing an ice40  project."""
    _test_project(
        apio_runner,
        example="Alhambra-II/ledon",
        testbench="ledon_tb",
        binary="hardware.bin",
        report_item="ICESTORM_LC:",
    )


def test_project_ecp5(apio_runner: ApioRunner):
    """Tests building and testing an ecp5 project."""
    _test_project(
        apio_runner,
        example="ColorLight-5A-75B-V8/Ledon",
        testbench="ledon_tb",
        binary="hardware.bit",
        report_item="ALU54B:",
    )
