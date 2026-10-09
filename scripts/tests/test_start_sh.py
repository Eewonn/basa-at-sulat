"""start.sh --check hands over to check_setup.py with a Python it finds, and passes the exit code on."""

import os
import stat
import subprocess
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
START = SCRIPTS / "start.sh"


def stub_python(tmp_path, exit_code=0):
    """A fake Python that records its arguments, so we see what start.sh would have run."""
    stub = tmp_path / "fake-python"
    log = tmp_path / "args.txt"
    stub.write_text(f'#!/bin/sh\necho "$@" > "{log}"\nexit {exit_code}\n')
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    return stub, log


def run_start(args, tmp_path, python=None, path=None):
    env = {**os.environ}
    if python:
        env["BASA_PYTHON"] = str(python)
    if path is not None:
        env["PATH"] = path
    return subprocess.run(["bash", str(START), *args], capture_output=True, text=True, env=env, timeout=60)


def test_check_runs_check_setup_with_the_python_it_was_given(tmp_path):
    stub, log = stub_python(tmp_path)
    result = run_start(["--check"], tmp_path, python=stub)
    assert result.returncode == 0
    assert "check_setup.py" in log.read_text()


def test_check_passes_the_exit_code_through(tmp_path):
    stub, _ = stub_python(tmp_path, exit_code=1)
    assert run_start(["--check"], tmp_path, python=stub).returncode == 1


def test_without_any_python_it_says_so_and_fails(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    # No BASA_PYTHON and no python on PATH (bash itself is found by absolute path).
    result = subprocess.run(
        ["/bin/bash", str(START), "--check"], capture_output=True, text=True,
        env={"PATH": str(empty), "HOME": str(tmp_path)}, timeout=60,
    )
    assert result.returncode != 0
    assert "python" in (result.stdout + result.stderr).lower()


def test_an_unknown_option_prints_usage_and_fails(tmp_path):
    stub, _ = stub_python(tmp_path)
    result = run_start(["--nope"], tmp_path, python=stub)
    assert result.returncode == 2
    assert "usage" in (result.stdout + result.stderr).lower()


def stub_python_for_order(tmp_path, check_exit):
    """A fake Python that logs which script it was asked to run, and fails the check on request."""
    stub = tmp_path / "fake-python"
    log = tmp_path / "order.txt"
    stub.write_text(
        '#!/bin/sh\n'
        f'echo "$1" >> "{log}"\n'
        f'case "$1" in *check_setup.py) exit {check_exit};; esac\n'
        'exit 0\n'
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    return stub, log


def test_a_normal_start_checks_first_then_launches(tmp_path):
    stub, log = stub_python_for_order(tmp_path, check_exit=0)
    assert run_start([], tmp_path, python=stub).returncode == 0
    ran = log.read_text().split()
    assert [Path(p).name for p in ran] == ["check_setup.py", "launch.py"]


def test_a_failed_check_stops_the_start_before_anything_launches(tmp_path):
    stub, log = stub_python_for_order(tmp_path, check_exit=1)
    result = run_start([], tmp_path, python=stub)
    assert result.returncode == 1
    assert [Path(p).name for p in log.read_text().split()] == ["check_setup.py"]
