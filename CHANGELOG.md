# Changelog

## 0.2.0

- Website picker: choose EDM Ghost Production, The Ghost Production or House of
  Tracks, then the genre. New rules files `tgp-*` and `hot-*` for tech house and
  melodic house & techno, from each site's seller pages (checked 2026-10-30).
- Rules can list several allowed sample rates and bit depths, accept 32-bit
  float (`allow_float`), leave a limit open with `null`, and set lengths per
  mix (`mix_length_seconds`).
- Each profile has a `checklist` of the website's rules the bot can't check;
  the report ends with it under "Before you upload to ...".
- EDM GP files now cite the seller page. It confirms the 0 to -0.3 dB master
  peak; still a WARN until the limiter ceiling is decided (BRIEF.md 8.1).

## 0.1.0

### Engine
- `scan.py`: finds Masters, Stems Extended / Stems Radio, Main.wav, Project and
  extras, with plain messages when something is missing. Names from config.json.
- `audio.py`: RIFF chunk reader, sample peak, full-scale runs, 4x true peak,
  integrated + short-term max LUFS (BS.1770 with pyloudnorm's filters).
- 16 checks, one file each: files_format, files_naming, stems_count,
  stems_silent, stems_length, stems_forbidden, stems_clipping, mix_headroom,
  null_test, master_loudness, master_peak, master_length, mixes_present,
  privacy_metadata, privacy_names, private_files. A crashing check shows as
  FAIL and the others still run.
- Null test: sums the stems, compares with Main.wav, tries offsets up to ±64
  samples, and on a miss names the bars, the most likely stems and the likely
  causes (bus sidechain, master rack on, missing return, ...).
- Rules: `edmgp-tech-house` and `edmgp-melodic-house-techno`. Master peak is a
  WARN until the open question is answered.
- `clean.py`: WAV copies with only `fmt ` + `data`, samples bit-identical.
- `mp3.py`: 320 kbps CBR MP3 with LAME (no ffmpeg), no tags.
- `package.py`: BUYER folder + zip only with no FAILs (WARNs need a click);
  Main.wav, private files, Ableton backups and .asd files never go in; the
  folder and zip are checked again before handing over.
- Report: Markdown with a qa.md block; `history.json` per run.
- Command line `cryx-qa` with exit codes 0 / 1 / 2.

### App
- Drop zone, profile, title, BPM, key; results list (red / yellow / green)
  with fix and numbers; Run checks, Build buyer zip, Copy report for qa.md,
  Open output folder; Include project and Make MP3s switches.
- Settings (banned words, default profile, output folder, MP3, folder
  patterns, rules folder) and a run history window.
- Same dark hardware look as Cryx MIDI Vault. Portable `CryxQAData` folder.
