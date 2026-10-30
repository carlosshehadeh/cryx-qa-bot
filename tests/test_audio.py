import numpy as np

from qabot import audio
from tests.make_fixtures import SR, info_chunk, write_wav


def test_read_info_sees_every_chunk(tmp_path):
    p = write_wav(tmp_path / "a.wav", np.zeros((100, 2)), chunks_before=[info_chunk(IART="x")],
                  chunks_after=[("id3 ", b"ID3....")])
    info = audio.read_info(p)
    assert info.ok and info.frames == 100 and info.channels == 2 and info.bit_depth == 16
    assert [c.id for c in info.chunks] == ["fmt ", "LIST", "data", "id3 "]
    assert info.extra_chunks == ["LIST", "id3 "]


def test_read_info_formats(tmp_path):
    assert audio.read_info(write_wav(tmp_path / "f.wav", np.zeros(10), float32=True)).format_tag == audio.FLOAT
    assert audio.read_info(write_wav(tmp_path / "b.wav", np.zeros(10), bits=24)).bit_depth == 24
    (tmp_path / "x.wav").write_bytes(b"not a wav")
    bad = audio.read_info(tmp_path / "x.wav")
    assert not bad.ok and bad.error


def test_stats_peak_and_clipping(tmp_path):
    x = np.zeros((1000, 1))
    x[10], x[500:504] = 0.5, 1.0
    p = write_wav(tmp_path / "c.wav", x)
    s = audio.stats(audio.load(p), audio.read_info(p))
    assert s.clipped == 4 and s.clip_run == 4
    assert abs(s.peak_db) < 0.01


def test_true_peak_sees_between_samples():
    # A sine at a quarter of the sample rate, phase-shifted: samples miss the crest.
    n = np.arange(SR)
    x = np.sin(2 * np.pi * (SR / 4) * n / SR + np.pi / 4)[:, None] * 0.5
    sample = audio.db(np.abs(x).max())
    assert audio.true_peak_db(x) > sample + 2.5


def test_loudness_of_a_sine():
    # 1 kHz sine, amplitude 0.1, both channels: about -20 LUFS (BS.1770).
    t = np.arange(SR * 5) / SR
    x = np.repeat((0.1 * np.sin(2 * np.pi * 1000 * t))[:, None], 2, axis=1)
    integrated, short_max = audio.loudness(x, SR)
    assert -20.6 < integrated < -19.4
    assert abs(short_max - integrated) < 0.5


def test_loudness_matches_pyloudnorm():
    import pyloudnorm
    rng = np.random.default_rng(5)
    x = rng.standard_normal((SR * 12, 2)) * 0.1
    x[SR * 4:SR * 6] *= 0.001          # a near-silent gap, so the gates matter
    ours, _ = audio.loudness(x, SR)
    theirs = pyloudnorm.Meter(SR).integrated_loudness(x)
    assert abs(ours - theirs) < 0.05
