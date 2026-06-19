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


def test_matrix_command_reports_bet_holds(capsys):
    assert main(["matrix", "--budget", "60"]) == 0
    out = capsys.readouterr().out
    assert "bet_holds=True" in out
    assert "relay-off/bounded" in out


def test_run_then_inspect_replays_without_model(tmp_path, capsys):
    db = str(tmp_path / "store.db")
    assert main(["run", "--db", db, "--budget", "60"]) == 0
    capsys.readouterr()  # drain run output

    # inspect a persisted session: replays recorded trace, exits zero
    assert main(["inspect", "synthesis", "--db", db]) == 0
    out = capsys.readouterr().out
    assert "session: synthesis" in out
    assert "artifact://demo/synthesis.out" in out


def test_inspect_unknown_session_exits_nonzero(tmp_path, capsys):
    db = str(tmp_path / "empty.db")
    assert main(["inspect", "nope", "--db", db]) == 1
    err = capsys.readouterr().err
    assert "session not found" in err


def test_graph_command_runs_demo_graph(capsys):
    assert main(["graph", "--budget", "60"]) == 0
    out = capsys.readouterr().out
    assert "synthesis [done]" in out


def test_graph_mixed_command_runs(capsys):
    assert main(["graph", "--mixed"]) == 0
    out = capsys.readouterr().out
    assert "impl [done]" in out
    assert "plan -> impl" in out


def test_execute_command_runs_demo_executor(capsys):
    assert main(["execute"]) == 0
    out = capsys.readouterr().out
    assert "patch=artifact://exec/addgreet.patch" in out
    assert "status=passed" in out
