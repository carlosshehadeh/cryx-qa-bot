import shutil
import subprocess

import numpy as np
import pytest

from qabot import mp3
from tests.make_fixtures import SR, write_wav


def test_mp3_is_320_cbr_and_right_length(tmp_path):
    t = np.arange(SR * 4) / SR
    x = np.stack([np.sin(2 * np.pi * 220 * t), np.sin(2 * np.pi * 330 * t)], axis=1) * 0.3
    src = write_wav(tmp_path / "Song (Extended Mix).wav", x)
    out = mp3.encode(src, tmp_path / "Song (Extended Mix).mp3")
    count, rates, sr = mp3.frames(out)
    assert rates == {320} and sr == SR
    assert abs(count * 1152 / SR - 4.0) < 0.1
    assert b"TIT2" not in out.read_bytes() and b"Song" not in out.read_bytes()


@pytest.mark.skipif(not shutil.which("ffprobe"), reason="ffprobe not installed")
def test_mp3_plays(tmp_path):
    t = np.arange(SR * 3) / SR
    src = write_wav(tmp_path / "a.wav", np.sin(2 * np.pi * 440 * t)[:, None] * 0.3)
    out = mp3.encode(src, tmp_path / "a.mp3")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,bit_rate",
                            "-of", "default=nw=1", str(out)], capture_output=True, text=True, check=True)
    values = dict(line.split("=") for line in probe.stdout.split())
    assert abs(float(values["duration"]) - 3.0) < 0.1
    assert int(values["bit_rate"]) // 1000 in (319, 320, 321)
