"""
  Test for the "apio clean" command
"""

# -- apio clean entry point
from apio.commands.clean import cli as cmd_clean


def test_clean_no_apio_ini_no_params(click_cmd_runner, setup_apio_test_env):
    """Test: apio clean when no apio.ini file is given
    No additional parameters are given
    """

    with click_cmd_runner.isolated_filesystem():

        # -- Config the apio test environment
        setup_apio_test_env()

        # -- Execute "apio clean"
        result = click_cmd_runner.invoke(cmd_clean)

        # -- It is an error. Exit code should not be 0
        assert result.exit_code != 0, result.output
        assert "Info: Project has no apio.ini file" in result.output
        assert "Error: insufficient arguments: missing board" in result.output

        # -- Execute "apio clean --board alhambra-ii"
        result = click_cmd_runner.invoke(cmd_clean, ["--board", "alhambra-ii"])
        assert result.exit_code == 0, result.output


def test_clean_no_apio_ini_params(
    click_cmd_runner, setup_apio_test_env, path_in_project
):
    """Test: apio clean when no apio.ini file is given. Board definition
    comes from --board parameter.
    """

    with click_cmd_runner.isolated_filesystem():

        # -- Config the apio test environment
        setup_apio_test_env()

        # -- Create a legacy artifact file.
        path_in_project("main_tb.vcd").touch()

        # -- Create a current artifact file.
        path_in_project("_build").mkdir()
        path_in_project("_build/main_tb.vcd").touch()

        # Confirm that the files exists
        assert path_in_project("main_tb.vcd").is_file()
        assert path_in_project("_build/main_tb.vcd").is_file()

        # -- Execute "apio clean --board alhambra-ii"
        result = click_cmd_runner.invoke(cmd_clean, ["--board", "alhambra-ii"])
        assert result.exit_code == 0, result.output

        # Confirm that the files do not exist.
        assert not path_in_project("main_tb.vcd").exists()
        assert not path_in_project("_build/main_tb.vcd").exists()


def test_clean_create(
    click_cmd_runner, setup_apio_test_env, path_in_project, write_apio_ini
):
    """Test: apio clean when there is an apio.ini file"""

    with click_cmd_runner.isolated_filesystem():

        # -- Config the apio test environment
        setup_apio_test_env()

        # -- Create apio.ini
        write_apio_ini({"board": "icezum", "top-module": "main"})

        # -- Create a legacy artifact file.
        path_in_project("main_tb.vcd").touch()

        # -- Create a current artifact file.
        path_in_project("_build").mkdir()
        path_in_project("_build/main_tb.vcd").touch()

        # Confirm that the files exists
        assert path_in_project("main_tb.vcd").is_file()
        assert path_in_project("_build/main_tb.vcd").is_file()

        # --- Execute "apio clean"
        result = click_cmd_runner.invoke(cmd_clean)
        assert result.exit_code == 0, result.output

        # Confirm that the files do not exist.
        assert not path_in_project("main_tb.vcd").exists()
        assert not path_in_project("_build/main_tb.vcd").exists()
