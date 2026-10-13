"""Static browser bundle checks; Node is present on GitHub's Ubuntu runners."""
from html.parser import HTMLParser
from pathlib import Path
import subprocess


HTML = Path(__file__).resolve().parents[1] / "web" / "index.html"


class ScriptCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.collecting = False
        self.scripts = []
        self.external = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "script":
            if "src" in attributes:
                self.external.append(attributes["src"])
            else:
                self.collecting = True
        if tag == "link" and attributes.get("rel") == "stylesheet":
            self.external.append(attributes.get("href", ""))

    def handle_endtag(self, tag):
        if tag == "script":
            self.collecting = False

    def handle_data(self, data):
        if self.collecting:
            self.scripts.append(data)


def test_browser_code_parses_with_node():
    parser = ScriptCollector()
    parser.feed(HTML.read_text(encoding="utf-8"))
    assert not parser.external, "Application must not require remote runtime assets"
    assert parser.scripts, "Application must include functional JavaScript"
    completed = subprocess.run(
        ["node", "--check"], input="\n".join(parser.scripts),
        text=True, capture_output=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_browser_has_no_simulated_audit_fallback():
    html = HTML.read_text(encoding="utf-8")
    assert "DOSSIER-SIM-" not in html
    assert "HMAC_SHA256_e83" not in html
    assert "download" in html and "lexicalSimilarity" in html
