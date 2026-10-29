import hashlib

import numpy as np
import pytest

from qabot import audio, clean
from tests.make_fixtures import info_chunk, write_wav


def test_clean_copy_is_bit_identical_and_bare(tmp_path):
    rng = np.random.default_rng(1)
    x = rng.uniform(-0.9, 0.9, (5001, 2))
    for bits in (16, 24):
        src = write_wav(tmp_path / f"in{bits}.wav", x, bits=bits,
                        chunks_before=[info_chunk(IART="Carlos Test"), ("bext", b"\0" * 603)],
                        chunks_after=[("C2PA", b"jumb" * 10), ("iXML", b"<x/>")])
        before = hashlib.sha256(src.read_bytes()).hexdigest()
        dst = clean.clean_copy(src, tmp_path / "out" / f"out{bits}.wav")
        assert clean.chunk_ids(dst) == ["fmt ", "data"]
        assert np.array_equal(audio.load(src), audio.load(dst))
        assert hashlib.sha256(src.read_bytes()).hexdigest() == before   # original untouched
        assert b"Carlos" not in dst.read_bytes()


def test_clean_refuses_to_overwrite_the_original(tmp_path):
    src = write_wav(tmp_path / "a.wav", np.zeros(10))
    with pytest.raises(ValueError):
        clean.clean_copy(src, src)
