"""The site must be installable: manifest, icons, and a service worker that caches real files."""
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "browse.html"]            # market.html is added to this when it exists
if (ROOT / "market.html").exists():
    PAGES.append("market.html")


def png_size(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    return struct.unpack(">II", data[16:24])


def test_manifest_has_what_installation_needs():
    m = json.loads((ROOT / "manifest.json").read_text())
    assert m["name"] and m["short_name"]
    assert m["display"] in ("standalone", "fullscreen", "minimal-ui")
    assert (ROOT / m["start_url"].lstrip("./")).exists()
    assert re.fullmatch(r"#[0-9a-f]{6}", m["theme_color"])
    sizes = {i["sizes"] for i in m["icons"]}
    assert {"192x192", "512x512"} <= sizes


def test_every_manifest_icon_exists_and_has_its_declared_size():
    for icon in json.loads((ROOT / "manifest.json").read_text())["icons"]:
        w, h = (int(n) for n in icon["sizes"].split("x"))
        assert png_size(ROOT / icon["src"]) == (w, h), icon["src"]


def test_there_is_a_maskable_icon():
    icons = json.loads((ROOT / "manifest.json").read_text())["icons"]
    assert any(i["purpose"] == "maskable" for i in icons)


def test_every_page_links_the_manifest_and_loads_the_shared_navigation():
    for page in PAGES:
        html = (ROOT / page).read_text()
        assert 'rel="manifest" href="manifest.json"' in html, page
        assert 'src="nav.js"' in html and 'href="style.css"' in html, page


def test_the_service_worker_is_registered_by_the_shared_script():
    assert 'register("sw.js")' in (ROOT / "nav.js").read_text()


def test_service_worker_precaches_files_that_exist():
    sw = (ROOT / "sw.js").read_text()
    shell = re.search(r"const SHELL = \[(.*?)\];", sw, re.S).group(1)
    files = re.findall(r'"([^"]+)"', shell)
    missing = [f for f in files if f != "./" and not (ROOT / f).exists()]
    # Only pages still to be built may be missing; the worker tolerates those.
    assert set(missing) <= {"market.html", "market.js"}, missing
    for needed in ["index.html", "browse.html", "data/history.csv", "data/status.json"]:
        assert needed in files


def test_service_worker_serves_the_network_first_and_falls_back_to_the_cache():
    sw = (ROOT / "sw.js").read_text()
    assert sw.index("fetch(req)") < sw.index("caches.match(req")
