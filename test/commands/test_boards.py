"""
  Test for the "apio boards" command
"""

from test.conftest import ApioRunner

# -- apio boards entry point
from apio.commands.boards import cli as apio_boards


CUSTOM_BOARDS = """
{
  "my_custom_board": {
    "name": "My Custom Board v3.1c",
    "fpga": "iCE40-UP5K-SG48",
    "programmer": {
      "type": "iceprog"
    },
    "usb": {
      "vid": "0403",
      "pid": "6010"
    },
    "ftdi": {
      "desc": "My Custom Board"
    }
  }
}
"""


def test_list_ok(apio_runner: ApioRunner):
    """Test normal board listing with the apio's boards.json."""

    with apio_runner.in_disposable_temp_dir():

        apio_runner.setup_env()

        result = apio_runner.invoke(apio_boards)
        apio_runner.assert_ok(result)
        # -- Note: pytest sees the piped version of the command's output.
        # -- Run 'apio build' | cat' to reproduce it.
        assert "Loading custom 'boards.json'" not in result.output
        assert "alhambra-ii" in result.output
        assert "my_custom_board" not in result.output
        assert "Total of 1 board" not in result.output


def test_custom_board(apio_runner: ApioRunner):
    """Test boards listing with a custom boards.json file."""

    with apio_runner.in_disposable_temp_dir():

        # -- Config the apio test environment
        apio_runner.setup_env()

        # -- Write a custom boards.json file in the project's directory.
        with open("boards.json", "w", encoding="utf-8") as f:
            f.write(CUSTOM_BOARDS)

        # -- Execute "apio boards"
        result = apio_runner.invoke(apio_boards)
        apio_runner.assert_ok(result)
        # -- Note: pytest sees the piped version of the command's output.
        # -- Run 'apio build' | cat' to reproduce it.
        assert "Loading custom 'boards.json'" in result.output
        assert "alhambra-ii" not in result.output
        assert "my_custom_board" in result.output
        assert "Total of 1 board" in result.output
