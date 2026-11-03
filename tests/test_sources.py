from pipeline.build import load_sources, replay
from pipeline.normalize import normalize

SAME_BOARD = ("ats", "host", "tenant", "site", "employer", "search")


def test_source_names_are_unique_and_there_are_at_least_fifteen_employers():
    import yaml
    with open("sources.yaml", encoding="utf-8") as f:
        entries = yaml.safe_load(f)["sources"]
    names = [s["name"] for s in entries]
    assert len(names) == len(set(names))
    assert len({s["employer"] for s in entries}) >= 15


def test_four_texas_sources_exist():
    tx = {n for n in load_sources() if n.endswith("_tx")}
    assert tx == {"wells_fargo_tx", "truist_tx", "fidelity_tx", "santander_tx"}


def test_each_texas_source_queries_its_national_board_with_the_texas_filter():
    sources = load_sources()
    for name, tx in sources.items():
        if not name.endswith("_tx"):
            continue
        national = sources[name[:-len("_tx")]]
        assert tx["state"] == "Texas" and "state" not in national
        for key in SAME_BOARD:
            assert tx.get(key) == national.get(key), (name, key)


RAW = {"jobPostings": [{"title": "Credit Analyst", "locationsText": "5 Locations",
                        "externalPath": "/job/DALLAS-TX/Credit-Analyst_R-7"}]}


def test_the_same_posting_gets_a_different_posting_id_under_each_source():
    sources = load_sources()
    national = normalize(sources["wells_fargo"], RAW)[0]
    texas = normalize(sources["wells_fargo_tx"], RAW)[0]
    assert national["source_id"] == texas["source_id"] == "R-7"
    assert national["employer"] == texas["employer"] == "Wells Fargo"
    assert national["url"] == texas["url"]
    assert national["posting_id"] == "wells_fargo:R-7"
    assert texas["posting_id"] == "wells_fargo_tx:R-7"


def test_overlapping_sources_are_kept_as_separate_rows_with_their_own_first_run():
    sources = load_sources()
    days = [("2026-11-03", "wells_fargo", RAW),
            ("2026-11-04", "wells_fargo", RAW),
            ("2026-11-04", "wells_fargo_tx", RAW)]
    h = replay(days, sources)
    assert set(h) == {"wells_fargo:R-7", "wells_fargo_tx:R-7"}
    assert h["wells_fargo:R-7"]["first_seen"] == "2026-11-03"
    assert h["wells_fargo_tx:R-7"]["first_seen"] == "2026-11-04"
    assert h["wells_fargo_tx:R-7"]["first_run"] is True     # the _tx copy's own first file


def test_removal_from_the_national_board_does_not_remove_the_texas_copy():
    sources = load_sources()
    empty = {"jobPostings": []}
    days = [("2026-11-04", "wells_fargo", RAW), ("2026-11-04", "wells_fargo_tx", RAW),
            ("2026-11-05", "wells_fargo", empty), ("2026-11-05", "wells_fargo_tx", RAW)]
    h = replay(days, sources)
    assert h["wells_fargo:R-7"]["status"] == "removed"
    assert h["wells_fargo_tx:R-7"]["status"] == "open"
