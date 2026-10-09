"""download_models.py decides what to fetch; the tests inject fakes so nothing is ever downloaded."""

import subprocess

import pytest

import download_models as dm


class Fake:
    """A model whose status and download are scripted, and which records what was downloaded."""

    def __init__(self, name, status, fail=None):
        self.name, self._status, self.fail, self.downloads = name, status, fail, 0

    def status(self):
        return self._status

    def download(self):
        self.downloads += 1
        if self.fail:
            raise self.fail
        self._status = dm.PRESENT


def run(models, argv=(), capsys=None):
    code = dm.main(list(argv), models=models)
    return code, capsys.readouterr().out if capsys else ""


def test_it_downloads_only_what_is_missing(capsys):
    aligner, ollama = Fake("aligner", dm.MISSING), Fake("ollama", dm.PRESENT)
    code, out = run([aligner, ollama], capsys=capsys)
    assert code == 0
    assert (aligner.downloads, ollama.downloads) == (1, 0)
    assert "already" in out  # says plainly that the cached one was skipped


def test_nothing_is_downloaded_when_everything_is_already_there(capsys):
    models = [Fake("aligner", dm.PRESENT), Fake("ollama", dm.PRESENT)]
    code, _ = run(models, capsys=capsys)
    assert code == 0 and [m.downloads for m in models] == [0, 0]


def test_a_failed_download_exits_non_zero_with_the_reason_and_still_tries_the_others(capsys):
    aligner = Fake("aligner", dm.MISSING, fail=OSError("no route to host"))
    ollama = Fake("ollama", dm.MISSING)
    code, out = run([aligner, ollama], capsys=capsys)
    assert code == 1
    assert "no route to host" in out
    assert ollama.downloads == 1  # one failure doesn't stop the rest


def test_missing_torch_gets_an_actionable_message(capsys):
    aligner = Fake("aligner", dm.MISSING, fail=ModuleNotFoundError("No module named 'torch'"))
    code, out = run([aligner], capsys=capsys)
    assert code == 1
    assert "pip install -r ai/requirements.txt" in out


def test_ollama_not_installed_is_a_warning_not_a_failure(capsys):
    aligner, ollama = Fake("aligner", dm.PRESENT), Fake("ollama", dm.UNAVAILABLE)
    code, out = run([aligner, ollama], capsys=capsys)
    assert code == 0
    assert ollama.downloads == 0
    assert "ollama.com" in out


def test_check_reports_without_downloading_and_exits_non_zero_when_something_is_missing(capsys):
    aligner, ollama = Fake("aligner", dm.MISSING), Fake("ollama", dm.PRESENT)
    code, out = run([aligner, ollama], ["--check"], capsys)
    assert code == 1
    assert (aligner.downloads, ollama.downloads) == (0, 0)
    assert "aligner" in out and "missing" in out


def test_check_exits_zero_when_everything_is_there(capsys):
    code, _ = run([Fake("aligner", dm.PRESENT), Fake("ollama", dm.PRESENT)], ["--check"], capsys)
    assert code == 0


# --- the real Ollama probe, with a fake `ollama` command ---

LIST = (
    "NAME           ID            SIZE      MODIFIED\n"
    "qwen2.5:7b     abc123def456  4.7 GB    2 days ago\n"
    "llama3:latest  fff000fff000  4.7 GB    3 days ago\n"
)


def fake_run(stdout="", returncode=0, stderr="", missing=False):
    def run_(cmd, **kwargs):
        if missing:
            raise FileNotFoundError("ollama")
        return subprocess.CompletedProcess(cmd, returncode, stdout, stderr)

    return run_


def test_ollama_status_finds_the_exact_model_and_tag():
    assert dm.ollama_status("qwen2.5:7b", run=fake_run(LIST)) == dm.PRESENT
    assert dm.ollama_status("qwen2.5:3b", run=fake_run(LIST)) == dm.MISSING
    assert dm.ollama_status("qwen2.5", run=fake_run(LIST)) == dm.MISSING  # a different tag is not a match


def test_ollama_status_when_the_command_is_not_installed():
    assert dm.ollama_status("qwen2.5:7b", run=fake_run(missing=True)) == dm.UNAVAILABLE


def test_ollama_status_when_the_server_is_not_running():
    broken = fake_run(returncode=1, stderr="could not connect to ollama server")
    assert dm.ollama_status("qwen2.5:7b", run=broken) == dm.UNAVAILABLE


def test_ollama_pull_runs_the_pull_command_and_reports_a_failure():
    calls = []

    def run_(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    dm.ollama_pull("qwen2.5:7b", run=run_)
    assert calls == [["ollama", "pull", "qwen2.5:7b"]]
    with pytest.raises(RuntimeError, match="disk full"):
        dm.ollama_pull("qwen2.5:7b", run=fake_run(returncode=1, stderr="disk full"))
