from relayflow import __version__
from relayflow.cli import build_parser, main


def test_version_matches_package():
    parser = build_parser()
    assert __version__ == "0.1.0"
    assert parser.prog == "relayflow"


def test_main_no_args_prints_help_and_exits_zero(capsys):
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "relayflow" in out
