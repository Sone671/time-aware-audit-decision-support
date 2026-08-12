from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from framenet_frame_formal_guard import assert_private_unlock  # noqa: E402
from run_framenet_frame_formal_confirmation import (  # noqa: E402
    _alignment_hash,
    _private_errors,
)


def _record(key: str, response: str, candidates: tuple[str, ...]) -> dict[str, object]:
    return {
        "alignment_key_hash": key,
        "unit_hash": hashlib.sha256(key.encode("ascii")).hexdigest(),
        "response": response,
        "candidate_labels": candidates,
    }


def test_private_unlock_is_explicit():
    try:
        assert_private_unlock("wrong")
    except PermissionError:
        pass
    else:
        raise AssertionError("wrong private token was accepted")


def test_exact_lu_and_fulltext_alignment(tmp_path):
    sentence_a = "They frame the question."
    key_a = _alignment_hash(sentence_a, "frame", 5, 10)
    sentence_b = "Birds fly."
    key_b = _alignment_hash(sentence_b, "fly", 6, 9)
    archive = tmp_path / "truth.zip"
    lu_xml = f'''<lexUnit frame="Frame One">
      <subCorpus><sentence><text>{sentence_a}</text><annotationSet>
      <layer name="Target"><label start="5" end="9"/></layer>
      </annotationSet></sentence></subCorpus></lexUnit>'''
    full_xml = f'''<fullTextAnnotation><sentence><text>{sentence_b}</text>
      <annotationSet frameName="Frame Two"><layer name="Target">
      <label start="6" end="8"/></layer></annotationSet></sentence>
      </fullTextAnnotation>'''
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("framenet_v17/lu/lu1.xml", lu_xml)
        handle.writestr("framenet_v17/fulltext/doc.xml", full_xml)
    records = [
        _record(key_a, "frame_one", ("frame_one", "other")),
        _record(key_a, "frame_one|other", ("frame_one", "other")),
        _record(key_b, "frame_two", ("frame_two", "other")),
    ]
    errors, audit = _private_errors(records, archive)
    assert errors is not None
    assert np.array_equal(errors, np.asarray([False, True, False]))
    assert audit["matched_key_count"] == 2
    assert audit["candidate_coverage_failure_record_count"] == 0


def test_out_of_candidate_truth_structurally_invalidates(tmp_path):
    sentence = "They frame the question."
    key = _alignment_hash(sentence, "frame", 5, 10)
    archive = tmp_path / "truth.zip"
    xml = f'''<lexUnit frame="Missing"><subCorpus><sentence><text>{sentence}</text>
      <annotationSet><layer name="Target"><label start="5" end="9"/></layer>
      </annotationSet></sentence></subCorpus></lexUnit>'''
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("framenet_v17/lu/lu1.xml", xml)
    errors, audit = _private_errors(
        [_record(key, "other", ("frame_one", "other"))], archive
    )
    assert errors is None
    assert audit["candidate_coverage_failure_record_count"] == 1
