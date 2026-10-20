"""Hand-built toy fixtures (synthetic, unit-test only; never research data)."""
import numpy as np
import pandas as pd

from aquatic_xai.data.clean import clean_pond, content_hash
from aquatic_xai.data.treatments import ffill_mask

RULES = {"cleaning": {"zero_as_missing": True,
                      "physical_bounds": {"DO": [0, 30], "pH": [0, 14], "Temp": [0, 45]},
                      "timezone": {"name": "IST", "utc_offset_minutes": 330}}}
COLS = ["Date/Time (IST)", "DO (mg/L)", "pH", "Temperature (°C)", "QC_Flag_DateTime", "QC_Flag_DO", "QC_Flag_pH"]


def raw(rows):
    return pd.DataFrame(rows, columns=COLS)


def test_zero_is_masked_not_deleted():
    r = raw([["2025-12-01 00:00:00", 5.0, 8.0, 26.0, None, None, None],
             ["2025-12-01 00:15:00", 0.0, 8.0, 26.0, None, None, None]])
    out, q, cnt = clean_pond(r, RULES)
    assert len(out) == 2 and len(q) == 0
    assert out.loc[1, "DO_status"] == "zero_artifact"
    assert np.isnan(out.loc[1, "DO"]) and out.loc[1, "DO_raw"] == 0
    assert out.loc[1, "pH_status"] == "ok"          # other variables in the row are kept


def test_conflicting_duplicate_masks_only_conflicting_variable_and_quarantines_extra_row():
    r = raw([["2025-12-01 00:00:00", 16.0, 8.9, 27.0, None, None, None],
             ["2025-12-01 00:00:00", 16.0, 8.7, 27.0, None, None, None]])
    out, q, cnt = clean_pond(r, RULES)
    assert len(out) == 1 and len(q) == 1
    assert out.loc[0, "DO_status"] == "ok" and out.loc[0, "pH_status"] == "dup_conflict"
    assert np.isnan(out.loc[0, "pH"])
    assert cnt["n_raw_rows"] == cnt["n_processed_rows"] + cnt["n_quarantined_rows"]


def test_identical_duplicate_collapses_without_masking():
    r = raw([["2025-12-01 00:00:00", 6.0, 8.0, 26.0, None, None, None]] * 2)
    out, q, _ = clean_pond(r, RULES)
    assert len(out) == 1 and len(q) == 1
    assert (out.loc[0, ["DO_status", "pH_status", "Temp_status"]] == "ok").all()


def test_flags_parsed_but_value_retained():
    r = raw([["2025-12-01 00:00:00", 0.05, 8.0, 26.0, "time_gap_>20min", "DO_<0.1", None],
             ["2025-12-01 00:15:00", 9.0, 8.0, 26.0, None, "DO_jump_>2", "pH_out_of_range"]])
    out, _, _ = clean_pond(r, RULES)
    assert out.loc[0, "flag_gap"] and out.loc[0, "flag_do_lt01"]
    assert out.loc[0, "DO_status"] == "ok" and out.loc[0, "DO"] == 0.05   # critical low-DO event is kept
    assert out.loc[1, "flag_do_jump"] and out.loc[1, "flag_ph_range"]


def test_out_of_bounds_and_utc_conversion():
    r = raw([["2025-12-01 05:30:00", 5.0, 15.0, 26.0, None, None, None]])
    out, _, _ = clean_pond(r, RULES)
    assert out.loc[0, "pH_status"] == "out_of_bounds"
    assert out.loc[0, "ts_utc"] == pd.Timestamp("2025-12-01 00:00:00")


def test_unparsed_timestamp_goes_to_quarantine():
    r = raw([["not a date", 5.0, 8.0, 26.0, None, None, None],
             ["2025-12-01 00:00:00", 5.0, 8.0, 26.0, None, None, None]])
    out, q, cnt = clean_pond(r, RULES)
    assert len(out) == 1 and q.loc[0, "reason"] == "unparsed_timestamp"


def test_cleaning_is_idempotent_by_content_hash():
    r = raw([["2025-12-01 00:15:00", 5.0, 8.0, 26.0, None, "DO_jump_>2", None],
             ["2025-12-01 00:00:00", 0.0, 8.0, 26.0, None, None, None]])
    a, qa, _ = clean_pond(r, RULES)
    b, qb, _ = clean_pond(r, RULES)
    assert content_hash(a) == content_hash(b) and content_hash(qa) == content_hash(qb)
    assert a["ts_ist"].is_monotonic_increasing      # out-of-order input is sorted


def test_ffill_is_causal_and_bounded():
    v = np.array([1, 0, 0, 0, 1], dtype=bool)
    assert ffill_mask(v, 2).tolist() == [True, True, True, False, True]
    lead = np.array([0, 1, 0], dtype=bool)
    assert ffill_mask(lead, 2).tolist() == [False, True, True]   # nothing is filled from the future
