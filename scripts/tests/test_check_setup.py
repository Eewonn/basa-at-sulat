"""check_setup.py reports what is ready and what is missing. Probes are injected, so the result never
depends on what happens to be installed on the machine running the tests."""

import check_setup as cs
import download_models as dm


def check(name, problem=None, required=True, fix="fix it"):
    return cs.Check(name=name, probe=lambda: problem, fix=fix, required=required)


def run(checks, capsys):
    code = cs.main([], checks=checks)
    return code, capsys.readouterr().out


def test_everything_ready_exits_zero(capsys):
    code, out = run([check("ffmpeg"), check("aligner weights")], capsys)
    assert code == 0
    assert "[ok] ffmpeg" in out and "[ok] aligner weights" in out
    assert "Ready" in out


def test_every_missing_required_item_is_listed_with_its_fix_and_the_exit_is_non_zero(capsys):
    code, out = run(
        [
            check("ffmpeg", "not found", fix="install ffmpeg"),
            check("aligner weights", "not downloaded", fix="python scripts/download_models.py"),
            check("desktop dependencies"),
        ],
        capsys,
    )
    assert code == 1
    assert "[MISSING] ffmpeg" in out and "install ffmpeg" in out
    assert "[MISSING] aligner weights" in out and "python scripts/download_models.py" in out
    assert "[ok] desktop dependencies" in out  # a problem doesn't hide what is fine
    assert "Not ready" in out and "2" in out


def test_a_missing_optional_item_only_warns_and_still_exits_zero(capsys):
    code, out = run([check("ffmpeg"), check("Ollama", "not installed", required=False, fix="see ollama.com")], capsys)
    assert code == 0
    assert "[warn] Ollama" in out and "see ollama.com" in out
    assert "Ready" in out


def test_a_probe_that_crashes_counts_as_a_problem_not_a_crash(capsys):
    def boom():
        raise OSError("disk unreadable")

    code, out = run([cs.Check(name="weights", probe=boom, fix="re-download")], capsys)
    assert code == 1 and "disk unreadable" in out


# --- the real probes, with the outside world faked ---

def names(checks):
    return [c.name for c in checks]


def test_the_default_checks_cover_every_part_and_only_ollama_is_optional():
    checks = cs.default_checks()
    assert {"ffmpeg", "npm", "Python packages", "aligner weights", "desktop dependencies", "Ollama"} <= set(names(checks))
    assert [c.name for c in checks if not c.required] == ["Ollama"]


def test_missing_modules_are_named():
    found = {"fastapi", "uvicorn"}
    problem = cs.missing_modules(["fastapi", "torch", "uvicorn", "soundfile"], find=lambda m: m if m in found else None)
    assert "torch" in problem and "soundfile" in problem and "fastapi" not in problem
    assert cs.missing_modules(["fastapi"], find=lambda m: m) is None


def test_a_program_that_is_not_on_the_path_is_a_problem():
    assert cs.program_problem("ffmpeg", which=lambda p: None) is not None
    assert cs.program_problem("ffmpeg", which=lambda p: "/usr/bin/ffmpeg") is None


def test_desktop_dependencies_need_node_modules(tmp_path):
    assert cs.desktop_problem(tmp_path) is not None
    (tmp_path / "desktop" / "node_modules").mkdir(parents=True)
    assert cs.desktop_problem(tmp_path) is None


def test_ollama_problem_distinguishes_not_running_from_missing_model():
    assert cs.ollama_problem(dm.PRESENT) is None
    assert "ollama pull" in cs.ollama_problem(dm.MISSING)
    assert "not installed or not running" in cs.ollama_problem(dm.UNAVAILABLE)


def test_the_aligner_weights_problem_follows_the_download_status():
    assert cs.weights_problem(dm.PRESENT) is None
    assert cs.weights_problem(dm.MISSING) is not None
