"""What every check gets: the scanned folder, the rules, the settings, and
cached measurements so each file is read only as often as needed."""

from qabot import audio


class Context:
    def __init__(self, export, rules, config, bpm=None, include_project=False):
        self.export = export
        self.include_project = include_project
        self.rules = rules
        self.config = config
        self.bpm = float(bpm or rules.get("bpm") or 120)
        self.numbers = {}         # section -> {label: value}, shown in the report
        self._info = {}
        self._stats = {}
        self._master = {}

    def info(self, path):
        if path not in self._info:
            self._info[path] = audio.read_info(path)
        return self._info[path]

    def readable(self, path):
        """Audio we can measure (a WAV with a valid header, or another format
        soundfile reads). Format problems are reported by files_format."""
        return path.suffix.lower() in (".wav", ".wave") and self.info(path).ok

    def stats(self, path):
        if path not in self._stats:
            self._stats[path] = audio.stats(audio.load(path), self.info(path))
        return self._stats[path]

    def master(self, path):
        """Loudness, true peak, sample peak and length of a master (cached)."""
        if path not in self._master:
            info = self.info(path)
            data = audio.load(path)
            lufs, short_max = audio.loudness(data, info.sample_rate)
            self._master[path] = {
                "lufs": lufs, "short_max": short_max,
                "true_peak": audio.true_peak_db(data),
                "sample_peak": audio.stats(data, info).peak_db,
                "seconds": info.seconds,
            }
        return self._master[path]

    def note(self, section, label, value):
        self.numbers.setdefault(section, {})[label] = value
