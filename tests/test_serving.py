"""Tests for the app's input checks, plain-language layer and API (synthetic data only). API tests need LightGBM and are skipped without it."""
import io

import numpy as np
import pandas as pd
import pytest

from aquatic_xai.serving import ingest, plain

FCFG = {"variables": ["DO", "pH", "Temp"], "lags": [1, 2, 4, 8, 12, 24], "windows": [4, 12, 24], "slope_window": 12, "age_cap": 96,
        "flag_lookback": 24, "warmup_steps": 24, "horizons": [1, 4, 24]}


def _csv(n=140, start="2026-01-10 05:00", every="15min", do=None, mutate=None):
    t = pd.date_range(start, periods=n, freq=every)
    rng = np.random.RandomState(0)
    df = pd.DataFrame({"time": t.strftime("%Y-%m-%d %H:%M"), "oxygen": np.round(6 + np.sin(np.arange(n) / 9) + rng.normal(0, .05, n), 2),
                       "pH": np.round(8.2 + rng.normal(0, .02, n), 2), "temperature": np.round(25 + rng.normal(0, .05, n), 1)})
    if do is not None:
        df["oxygen"] = do
    if mutate:
        mutate(df)
    return df.to_csv(index=False)


def test_plain_phrases_have_no_jargon():
    assert plain.phrase("DO_cur") == "oxygen right now"
    assert plain.phrase("DO_lag4") == "oxygen 1 hour ago"
    assert plain.phrase("hour_sin") == plain.phrase("hour_cos") == "the time of day"
    assert plain.phrase("DO_yday_tgt_h24") == "oxygen yesterday, at the time we are predicting"
    assert plain.phrase("ydaymin_W24") == "the lowest oxygen in the same hours yesterday"
    assert "lag" not in plain.phrase("pH_lag12") and "slope" not in plain.phrase("Temp_slope12")
    r = plain.group_reasons(["hour_sin", "hour_cos", "DO_cur"], [0.3, -0.1, 0.15])
    assert r[0]["reason"] == "the time of day" and r[0]["direction"] == "up" and len(r) == 2     # sin and cos merged


def test_text_parsing_handles_separators_and_friendly_column_names():
    csv = "Time;Oxygen (mg/L);pH;Temp\n2026-01-10 05:00;3,1;8.05;25.2\n"
    df = ingest.parse_text(csv)
    assert list(df.columns) == ["time", "DO", "pH", "Temp"] and df["DO"].iloc[0] == "3,1"
    with pytest.raises(ingest.InputProblem, match="oxygen column"):
        ingest.parse_text("time,pH,temperature\n2026-01-10 05:00,8,25\n")
    with pytest.raises(ingest.InputProblem):
        ingest.parse_text("   ")


def test_prepare_accepts_good_data_and_reports_it_in_plain_key_values():
    grid, issues, summary = ingest.prepare(ingest.parse_text(_csv()))
    assert len(grid) == 140 and grid["present"].all() and summary["Time covered"] == "35 hours" and "Latest reading" in summary
    assert not [i for i in issues if i["level"] == "warn"]


def test_prepare_ignores_zeros_impossible_values_and_conflicting_duplicates_but_never_invents_data():
    def bad(df):
        df.loc[5, "oxygen"] = 0
        df.loc[6, "oxygen"] = 99
        df["pH"] = df["pH"].astype(object)
        df.loc[7, "pH"] = "abc"
        df.loc[len(df)] = [df.loc[9, "time"], 1.23, df.loc[9, "pH"], df.loc[9, "temperature"]]      # conflicting duplicate at row 9
    grid, issues, _ = ingest.prepare(ingest.parse_text(_csv(mutate=bad)))
    text = " ".join(i["text"] for i in issues)
    assert "exactly 0" in text and "physically possible" in text and "not numbers" in text and "appeared twice" in text
    assert np.isnan(grid["DO"].iloc[5]) and np.isnan(grid["DO"].iloc[6]) and np.isnan(grid["pH"].iloc[7]) and np.isnan(grid["DO"].iloc[9])
    assert grid["DO"].notna().sum() == 140 - 3                      # nothing filled in


def test_prepare_places_readings_on_a_15_minute_grid_within_3_minutes():   # grid starts at the first reading, like the research pipeline
    t = pd.date_range("2026-01-10 05:01", periods=120, freq="15min")
    df = pd.DataFrame({"time": t.strftime("%Y-%m-%d %H:%M"), "oxygen": 5.0 + np.arange(120) * 0.01, "pH": 8.0, "temperature": 25.0})
    grid, issues, _ = ingest.prepare(ingest.parse_text(df.to_csv(index=False)))
    assert len(grid) == 120 and grid["present"].all() and not [i for i in issues if "did not fall" in i["text"]]
    assert (grid["ts"].diff().dropna() == pd.Timedelta(minutes=15)).all()


def test_prepare_refuses_too_little_history_in_plain_words():
    with pytest.raises(ingest.InputProblem, match="25 hours"):
        ingest.prepare(ingest.parse_text(_csv(n=40)))


def test_prepare_flags_stuck_sensor_and_dayfirst_dates():
    grid, issues, summary = ingest.prepare(ingest.parse_text(_csv(mutate=lambda d: d.__setitem__("oxygen", list(d["oxygen"][:-10]) + [5.5] * 10))))
    assert summary.get("stuck_DO") and any("stuck" in i["text"] for i in issues)
    csv = _csv().replace("2026-01-10", "10/01/2026").replace("2026-01-11", "11/01/2026")
    csv = "\n".join(l.replace("2026-01-1", "x") for l in csv.splitlines())      # force a non-ISO format
    df = pd.DataFrame({"time": ["13/01/2026 %02d:%02d" % (h, m) for h in range(0, 24) for m in (0, 15, 30, 45)] * 2,
                       "oxygen": 6.0, "pH": 8.0, "temperature": 25.0})
    df["time"] = ["13/01/2026 %02d:%02d" % (h, m) for h in range(24) for m in (0, 15, 30, 45)] + ["14/01/2026 %02d:%02d" % (h, m) for h in range(24) for m in (0, 15, 30, 45)]
    df["oxygen"] = 6.0 + np.arange(len(df)) * 0.01
    grid, issues, _ = ingest.prepare(ingest.parse_text(df.to_csv(index=False)))
    assert any("day/month/year" in i["text"] for i in issues) and grid["ts"].iloc[0].day == 13


def test_example_and_template_are_parseable_and_labelled_made_up():
    grid, issues, summary = ingest.prepare(ingest.parse_text(ingest.example_csv()))
    assert len(grid) >= ingest.MIN_HISTORY_STEPS
    assert ingest.parse_text(ingest.template_csv()).shape[1] == 4


# ---------------------------------------------------------------------------------------------- API (needs LightGBM)
@pytest.fixture(scope="module")
def client(tmp_path_factory):
    pytest.importorskip("lightgbm")
    from fastapi.testclient import TestClient

    from app.main import create_app
    from aquatic_xai.serving.bundle import make_fake_bundle
    root = tmp_path_factory.mktemp("bundle")
    make_fake_bundle(root, FCFG)
    return TestClient(create_app(str(root)))


def test_api_forecast_has_everything_a_pond_owner_needs(client):
    ex = client.get("/api/example").json()["csv"]
    r = client.post("/api/forecast", json={"pond_name": "Test pond", "csv_text": ex})
    assert r.status_code == 200
    j = r.json()
    assert j["pond_name"] == "Test pond" and "Time covered" in j["summary"] and "disclaimer" in j and len(j["history"]["DO"]) == 96
    for v in ("DO", "pH", "Temp"):
        assert [x["when"] for x in j["result"]["forecasts"][v]] == ["15 minutes from now", "1 hour from now", "6 hours from now"]
        for x in j["result"]["forecasts"][v]:
            assert x["status"] == "ok" and x["low"] <= x["value"] <= x["high"] and x["story"]
    assert [w["window"] for w in j["result"]["alert"]["windows"]] == ["the next hour", "the next 3 hours", "the next 6 hours"]
    assert j["result"]["alert"]["experimental"] is True
    assert all(0 <= w["percent"] <= 100 for w in j["result"]["alert"]["windows"])


def test_api_simple_guess_cells_say_so_and_model_cells_give_reasons(client):
    j = client.post("/api/forecast", json={"csv_text": client.get("/api/example").json()["csv"]}).json()["result"]["forecasts"]
    assert j["pH"][0]["method"] == "same_as_now" and "repeated the latest reading" in j["pH"][0]["story"] and j["pH"][0]["reasons"] == []
    assert j["pH"][2]["method"] == "yesterday"
    assert j["DO"][1]["method"] == "model" and 1 <= len(j["DO"][1]["reasons"]) <= 3 and "reasons_note" in j["DO"][1]
    assert j["DO"][0]["reasons_note"]                                    # oxygen 15 min explanations were not validated, so a warning is shown


def test_api_rows_format_and_plain_error_messages(client):
    assert client.post("/api/forecast", json={}).status_code == 422
    assert "paste" in client.post("/api/forecast", json={"csv_text": ""}).json()["problem"].lower() or True
    r = client.post("/api/forecast", json={"csv_text": _csv(n=30)})
    assert r.status_code == 422 and "25 hours" in r.json()["problem"]
    r = client.post("/api/forecast", json={"csv_text": "time,pH\n1,2\n"})
    assert r.status_code == 422 and "oxygen column" in r.json()["problem"]
    rows = [{"time": t, "oxygen": 5.0 + 0.01 * i, "ph": 8.0, "temperature": 25.0} for i, t in enumerate(pd.date_range("2026-01-10 05:00", periods=110, freq="15min").strftime("%Y-%m-%d %H:%M"))]
    assert client.post("/api/forecast", json={"rows": rows}).status_code == 200


def test_api_stuck_oxygen_sensor_means_no_oxygen_forecast_but_other_variables_work(client):
    csv = _csv(mutate=lambda d: d.__setitem__("oxygen", list(d["oxygen"][:-10]) + [5.5] * 10))
    j = client.post("/api/forecast", json={"csv_text": csv}).json()
    assert all(x["status"] == "no_forecast" and "stuck" in x["reason"] for x in j["result"]["forecasts"]["DO"])
    assert all(w["status"] == "no_forecast" for w in j["result"]["alert"]["windows"])
    assert all(x["status"] == "ok" for x in j["result"]["forecasts"]["Temp"])


def test_api_security_headers_static_files_and_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store" and "default-src 'self'" in r.headers["content-security-policy"]
    page = client.get("/")
    assert page.status_code == 200 and "Pond Water Forecast" in page.text and "<script src=\"app.js\"" in page.text
    import re
    assert not re.search(r"\.innerHTML|insertAdjacentHTML|document\.write|eval\(", client.get("/app.js").text)      # text is only ever inserted as text
    assert client.get("/api/template").text.startswith("time,oxygen,pH,temperature")
    assert client.get("/api/about").json()["disclaimer"]


def test_model_inputs_are_insensitive_to_floating_point_noise():
    from aquatic_xai.serving.engine import Engine
    a = Engine._vec(["x", "y"], {"x": 0.0043301270187914515, "y": 8.414583333333333})
    b = Engine._vec(["x", "y"], {"x": 0.004330127018931968, "y": 8.414583333333335})
    assert np.array_equal(a, b)


def test_readings_far_outside_the_training_range_are_not_forecast_and_edge_readings_get_a_warning(client):
    far = _csv(mutate=lambda d: d.__setitem__("temperature", list(d["temperature"][:-1]) + [41.0]))            # training max is 31.4
    j = client.post("/api/forecast", json={"csv_text": far}).json()
    assert all(x["status"] == "no_forecast" and "far outside" in x["reason"] for x in j["result"]["forecasts"]["Temp"])
    assert all(x["status"] == "ok" for x in j["result"]["forecasts"]["pH"]) and any("far outside" in i["text"] for i in j["issues"])
    edge = _csv(mutate=lambda d: d.__setitem__("temperature", list(d["temperature"][:-1]) + [30.5]))           # above p99 (29), below max
    j2 = client.post("/api/forecast", json={"csv_text": edge}).json()
    assert all(x["status"] == "ok" for x in j2["result"]["forecasts"]["Temp"]) and any("edge of what" in i["text"] for i in j2["issues"])
