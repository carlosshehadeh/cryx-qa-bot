# Changelog

## 0.2.0

- Three websites: EDM Ghost Production, The Ghost Production and House of
  Tracks, each with Tech House and Melodic House & Techno (6 profiles).
  Rules come from each site's seller pages and are split into
  `rules/sites/*.json` and `rules/genres/*.json`.
- The buyer package follows each site's folder and file names. The unmastered
  mix (Main.wav, and an optional `Unmastered` folder for the radio mix) is now
  part of the package, as all three sites ask for it. MP3s only where the site
  wants them. House of Tracks gets masters.zip, stems.zip and midi.zip at
  24-bit, with stem numbers taken off the names.
- New check `midi_present`: the site wants the MIDI of the melodic parts
  (`MIDI` folder in the export). The bot only copies the files.
- Bit depth and sample rate rules per site, separately for stems and mixes.
- Headroom of every unmastered version, measured as each site asks.
- Master length limits per mix (extended / radio) and site.
- File names with a BPM or year get a warning.
- Report lists the site rules the bot can't measure (exclusivity, samples,
  vocals, artwork).

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
