"""offline_audit.py fails on code that could reach the internet. It is tested on small fake trees so we know
it can fail, and then pointed at the real repo so a future change can't quietly add a call out."""

from pathlib import Path

import offline_audit as audit

REPO_ROOT = Path(__file__).resolve().parents[2]


def tree(tmp_path, files):
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return tmp_path


def test_a_clean_tree_has_no_problems(tmp_path):
    root = tree(tmp_path, {"engine/app/ok.py": 'URL = "http://127.0.0.1:11434"\nOTHER = "http://localhost:5173"\n'})
    assert audit.find_problems(root) == []


def test_an_external_url_is_reported_with_its_file_and_line(tmp_path):
    root = tree(tmp_path, {"engine/app/bad.py": 'x = 1\nAPI = "https://api.example.com/v1"\n'})
    problems = audit.find_problems(root)
    assert len(problems) == 1
    assert "engine/app/bad.py:2" in problems[0] and "api.example.com" in problems[0]


def test_look_alike_hosts_are_not_local(tmp_path):
    root = tree(tmp_path, {"ai/x.py": 'a = "http://localhost.evil.com/x"\nb = "http://127.0.0.1.evil.com"\n'})
    assert len(audit.find_problems(root)) == 2


def test_network_client_libraries_are_reported(tmp_path):
    root = tree(
        tmp_path,
        {
            "engine/app/a.py": "import requests\n",
            "ai/b.py": "from aiohttp import ClientSession\n",
            "scripts/c.py": "import httpx\n",
        },
    )
    problems = audit.find_problems(root)
    assert len(problems) == 3
    assert any("requests" in p for p in problems)


def test_tests_are_not_audited(tmp_path):
    # Tests may mention external names (look-alike origins) and may use httpx.
    root = tree(tmp_path, {"engine/tests/t.py": 'import httpx\nX = "https://example.com"\n'})
    assert audit.find_problems(root) == []


def test_only_the_shipped_folders_are_audited(tmp_path):
    root = tree(tmp_path, {"docs/notes.py": 'X = "https://example.com"\n', "desktop/x.py": "import requests\n"})
    assert audit.find_problems(root) == []


def test_the_real_repo_has_no_outbound_urls_or_network_clients():
    assert audit.find_problems(REPO_ROOT) == []


def test_the_engines_local_only_origin_pattern_is_allowed(tmp_path):
    root = tree(tmp_path, {"engine/app/main.py": 'allow_origin_regex=r"http://(localhost|127\\.0\\.0\\.1):\\d+",\n'})
    assert audit.find_problems(root) == []


def test_a_similar_looking_pattern_that_lets_other_hosts_in_is_still_flagged(tmp_path):
    root = tree(
        tmp_path,
        {
            "engine/app/a.py": 'p = r"http://(localhost|evil\\.com):\\d+"\n',
            "engine/app/b.py": 'p = r"http://(.*)"\n',
        },
    )
    assert len(audit.find_problems(root)) == 2
