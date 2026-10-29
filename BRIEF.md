# Cryx QA Bot: project brief and build plan

Written 2026-10-29. Feed this file into a new code project. Save it in the repo as `BRIEF.md` so every future session reads it first. It's the second private tool after Cryx MIDI Vault and follows the same style, so the two stay easy to maintain side by side.

---

## 1. What we're building

A private Windows desktop app (.exe) for Carlos (artist name Cryx). It's for his use only, never sold.

**The job:** after Carlos exports a finished track from Ableton Live 12, he drops the export folder on the QA Bot. In under a minute it:

1. Checks every stem and master against the marketplace specs (EDM Ghost Production first).
2. Adds up all the stems and compares them to the unmastered mix, to prove the stems really rebuild the track (the "null test").
3. Strips personal info and hidden tags from every file.
4. Makes the 320 kbps MP3s from the master WAVs.
5. Builds a clean buyer zip, and refuses if anything private (Splice license, sample log, project notes) is inside.
6. Prints a pass/fail report Carlos can paste into the track's `qa.md`.

**Why:** today this is 30 to 45 minutes of manual checking per track, and mistakes cost sales. Track one shipped bass stems without the sidechain pump because the sidechain sat on the bus. The null test would have failed that automatically and pointed at the bass stems.

**What it never does:** it doesn't touch the Ableton project, doesn't write or change any music, and never edits the original export files. It only reads them and writes cleaned copies into a new output folder. Everything runs offline on Carlos's PC. No audio ever leaves the computer.

## 2. Setup Carlos does once

1. Create an empty **private GitHub repo**, for example `cryx-qa-bot`.
2. Create the new Claude code project, add the repo, and upload this brief.
3. Python 3.12+ is already needed for MIDI Vault. Same install works here.
4. Make a test folder, for example `D:\Kryx.wav\QA BOT TEST`. **Never upload sale-track WAVs to Claude** (see section 7). Claude builds and tests with fake test sounds it generates itself (sine waves, noise, clicks). Carlos tests on real exports locally with the .exe.

## 3. Tech decisions

| Topic | Decision | Why |
|---|---|---|
| App type | Native desktop .exe + a command-line version of the same engine | Carlos uses the window; Cryx Conductor (next tool) can call the command line after an export |
| Language | Python | Same as MIDI Vault, fast to change |
| Interface | Qt (PySide6) | Same as MIDI Vault, real drag-and-drop of folders |
| Audio reading | `soundfile` (libsndfile) + `numpy` | Reads WAV headers and samples exactly |
| Loudness | `pyloudnorm` (ITU BS.1770, same standard as Youlean) | Integrated LUFS that matches what Carlos sees in Youlean |
| True peak | 4x oversampling with `scipy.signal.resample_poly` | Same method as true peak meters |
| MP3 | `lameenc` (LAME encoder as a Python package, no ffmpeg install) | 320 kbps CBR MP3 straight from the master WAV |
| Rules | One JSON file per marketplace and genre in `rules/` | When a platform changes a number, Carlos (or Claude) edits a JSON file, no code change |
| Checks | One file per check in `checks/`, all registered in one list | New checks plug in without touching old ones. This is how the app keeps improving |
| Reports | Markdown + a run history in `history.json` | Paste into `qa.md`, see past runs per track |
| Packaging | PyInstaller, built on his Windows PC with `build_exe.bat` | Same as MIDI Vault |
| Portable | Settings, rules and history in one folder next to the .exe | Copy to a laptop and it works |
| Versions | Git, version number in the window title, `CHANGELOG.md` | Know what changed, roll back if needed |

Suggested layout:

```
cryx-qa-bot/
  BRIEF.md              this file
  CHANGELOG.md
  README.md
  config.json           banned words (personal info), default rules profile, output folder
  main.py               starts the window
  cli.py                command line: cryx-qa check "<folder>" --profile edmgp-tech-house
  rules/
    edmgp-tech-house.json
    edmgp-melodic-house-techno.json
    edmgp-drum-and-bass.json        (later)
    the-ghost-production.json       (later, second marketplace)
  qabot/
    scan.py             finds masters, stems, Main file and extras in the folder
    audio.py            read WAV, peak, true peak, LUFS, silence, length
    report.py           Result objects, Markdown report, history.json
    clean.py            rewrites WAV copies with only the audio (no metadata)
    mp3.py              WAV to 320 kbps MP3
    package.py          builds the buyer zip
    checks/
      __init__.py       the registry: list of all checks, in order
      files_format.py
      files_naming.py
      stems_count.py
      stems_silent.py
      stems_length.py
      stems_forbidden.py
      stems_clipping.py
      mix_headroom.py
      null_test.py
      master_loudness.py
      master_peak.py
      master_length.py
      mixes_present.py
      privacy_metadata.py
      privacy_names.py
      private_files.py
  ui/
    main_window.py      drop zone, profile picker, results list, buttons
  tests/
    make_fixtures.py    generates fake test exports (tones, noise, clicks)
    test_*.py
  build_exe.bat
```

### How a check looks (keep every check this simple)

Each check is one function that gets the scanned folder and the rules, and returns a list of results:

```python
@dataclass
class Result:
    check_id: str      # "stems_silent"
    level: str         # "PASS", "WARN" or "FAIL"
    message: str       # plain English: "Stem 'Perc 2.wav' is silent"
    fix: str = ""      # plain English: "Delete it, or unmute the track and re-export"
    files: list[str] = field(default_factory=list)
```

The registry in `checks/__init__.py` is just an ordered list. Adding a check is: new file, one line in the list, one test. Nothing else changes. A check that crashes shows as FAIL "check crashed: ..." and the other checks still run.

## 4. The export folder the bot expects

The bot finds files by name and folder, so Carlos keeps one simple habit when exporting. The bot tells him clearly if something is missing.

```
<Track Title> EXPORT\
  Masters\
    <Title> (Extended Mix).wav        mastered, rack ON
    <Title> (Radio Mix).wav           mastered, rack ON
  Stems Extended\
    01 Kick.wav, 02 Bass Sub.wav, ...  rack OFF, Selected/All Individual Tracks
    A Reverb Short.wav, B Delay.wav... returns as their own stems
    Main.wav                           the unmastered mix (rack OFF), used for the null test only
  Stems Radio\                         same as above for the radio mix (if delivered)
  Project\                             optional: the .als + samples if the project is sold
```

**About `Main.wav`:** when Ableton exports individual tracks, it can also render the Main track. That file is the unmastered mix with the master chain off. The bot uses it for the null test and the -3 to -6 dB headroom check, and **never** puts it in the zip. If Ableton didn't write it, Carlos exports the Main track alone with the rack off, same render range.

Folder and file name patterns live in `config.json`, so they can change without code.

## 5. Every check, with the rules it uses

All numbers come from the rules JSON. These are EDM Ghost Production's current numbers from the project references. Platform rules change, so Carlos checks the seller guidelines now and then and updates the JSON.

### Files and format
| Check | FAIL when | Notes |
|---|---|---|
| `files_format` | Any stem not WAV, 44.1 kHz, 16-bit | Masters: WAV 44.1 kHz/16-bit too |
| `files_naming` | Name has a number-only name, "Audio 12", "MIDI 3" or similar Ableton default | WARN only. Stems should be named by instrument (`Kick.wav`, `Arp.wav`) |

### Stems
| Check | FAIL when | Notes |
|---|---|---|
| `stems_count` | Fewer than 10 stems (after excluding Main) | Per stem folder |
| `stems_silent` | A stem's peak is below -80 dBFS for the whole file | "No empty stems" |
| `stems_length` | Stems differ in length by more than 1 sample | Every stem must cover the whole track |
| `stems_forbidden` | A file name matches REF, SC TRIG, Sidechain, BUS, GROUP, Master | Names from `rules` JSON. Main.wav is allowed but never zipped |
| `stems_clipping` | Any stem has samples at 0 dBFS (16-bit full scale) | Several in a row = clipped render |

### The mix (from Main.wav, master chain off)
| Check | FAIL / WARN | Notes |
|---|---|---|
| `mix_headroom` | FAIL if peak above -3 dBFS. WARN if below -6 dBFS | EDM GP: master peaking -3 to -6 dB when exporting stems |
| `null_test` | See below | The most important check |

**Null test, in detail:**
1. Load every stem (not Main), convert to float, add them together sample by sample.
2. Subtract that sum from `Main.wav`. What's left is the "residual".
3. Report how loud the residual is compared to the mix, in dB.
   - **PASS**: residual at or below -40 dB (only dither noise left)
   - **WARN**: -40 to -25 dB
   - **FAIL**: louder than -25 dB. The stems don't rebuild the mix.
   (Starting thresholds. Tune them on Carlos's first real exports and save in the rules JSON.)
4. When it fails, be useful:
   - Show **where**: split the track into bars using the BPM (from the rules or typed in) and list the bars with the biggest residual, like "bars 89 to 120 (Drop 1)".
   - Show **what**: correlate the residual with each stem and name the 1 to 3 most likely stems, like "Bass Sub, Bass Mid".
   - Show **why** with a hint list: sidechain or effects on a bus (buses render without their devices), the master rack left on during stem export, a missing return stem, a track muted in one export and not the other, "Include Return and Main Effects" turned on.
5. Small time offsets: if the residual is high, try shifting the sum by up to ±64 samples and use the best match before deciding. Report the offset if it isn't 0.

### Masters
| Check | FAIL when | Notes |
|---|---|---|
| `master_loudness` | Integrated LUFS outside -9 to -2 | Also shows short-term max, so it can be compared with Youlean |
| `master_peak` | Outside the range in the rules JSON | **Open question, see section 8.** |
| `master_length` | Shorter than 2:00 or longer than 8:00 | Also WARN if the extended mix is far from the genre's plan (tech house 6:30, melodic techno 6:58) |
| `mixes_present` | Extended or radio master missing when the profile needs both | Tech house and Melodic House & Techno need both on EDM GP |

### Privacy and private files
| Check | FAIL when | Notes |
|---|---|---|
| `privacy_metadata` | Any WAV has chunks other than `fmt ` and `data` (LIST/INFO, bext, iXML, id3, and any C2PA/JUMBF content-credential chunk) | Not a FAIL on the originals: the cleaned copies have none. The report says what was found and removed |
| `privacy_names` | A banned word from `config.json` appears in any file name, folder name, zip name, or inside a .als file (Carlos's real name, old and new artist name, email, Windows user path like `C:\Users\Carlos`) | Carlos fills the banned words list himself in Settings |
| `private_files` | Anything that looks private is in the folder: a file with "license", "Splice", "splice-log", "qa", "brief" in the name, PDFs, .txt or .md notes | Those files are never copied to the zip, and the report lists them |

## 6. What the bot produces

In a new folder next to the export, `<Title> BUYER\`:

```
<Title> BUYER\
  <Title> (Extended Mix).wav
  <Title> (Extended Mix).mp3        320 kbps, made by the bot
  <Title> (Radio Mix).wav
  <Title> (Radio Mix).mp3
  Stems Extended\  ...cleaned copies, Main.wav left out
  Stems Radio\     ...
  Project\         only if Carlos ticks "include project"
<Title> BUYER.zip
<Title> QA REPORT.md                  stays with Carlos, never in the zip
```

- Cleaned copies are rewritten from the audio data only, so no metadata or hidden tags survive. The audio samples must be bit-identical to the originals (a test checks this).
- The zip is built only if there are **no FAILs**. WARNs need one click: "I checked these".
- The report lists every check with PASS/WARN/FAIL, the fix hint, the numbers (LUFS, peaks, residual, lengths, stem count) and a ready-to-paste block for `qa.md`.
- `history.json` keeps one line per run (date, title, profile, results summary), so Carlos can see how a track went from FAIL to PASS.

## 7. Rules that every session must follow

- **Never write or suggest notes, melodies, basslines or chords.** This tool is pure checking and file handling.
- **Never ask Carlos to upload sale-track audio to Claude.** Build and test with generated fixtures only (`tests/make_fixtures.py` makes tones, noise and clicks). If something only shows up on real files, Carlos runs the .exe or the command line locally and pastes the report text. Audio that passes through Claude can come back with a content-credential tag, which is exactly what the privacy check looks for.
- Never modify the original export files. Read only, write copies.
- Keep the number rules in `rules/*.json`, never hard-coded in a check.
- Every new check gets its own file and at least one test with a fixture that should PASS and one that should FAIL.
- Plain English in every message and fix hint. Carlos reads them mid-session.
- Not legal advice. Platform rules change; check seller guidelines before each submission.

## 8. Open questions for Carlos (answer in the code project when asked)

1. **Master peak.** The melodic techno reference says EDM GP wants the master peak between **0 and -0.3 dB**. The CRYX MASTER rack sets the limiter ceiling at **-1.0 dB true peak**, which would fail that. Check EDM GP's current seller guidelines and set `master_peak` in the rules JSON to match. If they really want -0.3 to 0, raise the limiter ceiling to about -0.2 dB in the rack.
2. **Does EDM GP want MP3s uploaded,** or do they make their own previews? The melodic techno reference says a 320 kbps MP3 per mix. If not needed, switch MP3 off in Settings.
3. **Radio stems:** are radio stems delivered, or only extended stems + both masters? The profile has a switch for it.
4. **Project file:** will Carlos ever sell the .als project? If not, skip the Project folder checks.

## 9. Step-by-step build list

### Phase 0: Foundations
1. Repo structure, `README.md`, `CHANGELOG.md`, `.gitignore` (venv, build, dist, test output).
2. `report.py`: the `Result` class, PASS/WARN/FAIL, Markdown report writer.
3. `rules/edmgp-tech-house.json` and `rules/edmgp-melodic-house-techno.json` with every number from section 5 (BPM 128 and 124, plan lengths, LUFS range, peak ranges, stem minimum, forbidden names, radio required).
4. `tests/make_fixtures.py`: generates a fake export folder: 12 "stems" of tones and noise (16-bit, 44.1 kHz), a `Main.wav` that is their exact sum, and fake masters at about -8 LUFS. Plus broken variants: one silent stem, one 48 kHz stem, one 24-bit stem, a REF stem, stems of different length, a Main that doesn't match (one stem with a "pump" missing), a master at -12 LUFS, a WAV with metadata, a "Splice License.pdf".

### Phase 1: Engine (command line, no window)
5. `scan.py`: find Masters, Stems Extended, Stems Radio, Main.wav, extras. Clear messages when a folder is missing.
6. `audio.py`: read WAV (format, rate, bit depth, length), sample peak, true peak, integrated + short-term LUFS, silence check.
7. Checks for files and stems (section 5), one file each, with tests.
8. `null_test.py` with the where/what/why output. Test it with the "missing pump" fixture: it must FAIL and name the right stem and bars.
9. Master checks.
10. `cli.py`: `cryx-qa check "<folder>" --profile edmgp-tech-house` prints the report and returns exit code 0 (pass), 1 (warns) or 2 (fails). Conductor will use this later.

### Phase 2: Clean, MP3 and zip
11. `clean.py`: rewrite each WAV with only `fmt ` + `data`. Test that audio is bit-identical and no other chunk is left.
12. Privacy checks (metadata, banned words, private files).
13. `mp3.py`: 320 kbps CBR from each master WAV. Test that it plays and has the right length.
14. `package.py`: build the BUYER folder and zip only when there are no FAILs. Test that Main.wav, licenses, logs and notes never end up in the zip.

### Phase 3: Desktop app v0.1
15. Main window: big drop zone ("Drop your export folder here"), profile picker (tech house, melodic techno), track title, BPM, key.
16. Results list: green / yellow / red rows, click a row to see the fix hint and the numbers.
17. Buttons: **Run checks**, **Build buyer zip** (greyed out while there are FAILs), **Copy report for qa.md**, **Open output folder**.
18. Settings: banned words, default profile, folder name patterns, MP3 on/off, rules folder.
19. Portable mode: settings, rules and history next to the .exe, never in AppData.

### Phase 4: Make it an .exe and try it for real
20. `build_exe.bat`: venv, install requirements, build `Cryx QA Bot.exe` with an icon.
21. Carlos's first real test, locally: **track one, old bass stems vs new bass stems.** The old export (sidechain on the bus) should FAIL the null test and name the bass stems. The fixed export should PASS. That's the proof the tool works.
22. Tune the null test thresholds from what real exports show. Tag v0.1 on GitHub.

### Phase 5: Superpowers (one module each, in this order)
23. **Read the Ableton project (.als is gzipped XML):** list tracks that have clips and compare with the stems. "Track 'Perc 2' has clips but no stem" or "stem 'FX Noise' has no track". Also check the saved state: master rack off, REF and SC TRIG present but not exported.
24. **Auto Splice log:** the .als lists every sample file path. Pull every sample from the Splice folder and from KRYX SOUND VAULT, and write the track's Splice log table (file name, pack folder, which track it's on). Carlos only adds the Splice links. Saves 10 minutes per track and nothing gets forgotten.
25. **Folder watcher:** watch the Ableton export folder and run the checks the moment an export finishes. A Windows notification says PASS or FAIL.
26. **Pack-clip check hook:** when MIDI Vault's pack-clip checker exists, the QA Bot calls it on the .als and adds its result to the report (sketch-then-rewrite safety net).
27. **Listing helper:** fills title, BPM, key, both lengths and loudness into the track's `listing.md` template.
28. **More profiles:** melodic house, drum and bass (174 BPM), The Ghost Production marketplace.

## 10. Definition of done for v0.1

Carlos exports a track from Ableton into the folder layout above, double-clicks the .exe, drops the folder in, and within a minute sees a green/yellow/red list. Track one's old bass stems fail the null test and the bot names the bass stems as the cause. After the fix, everything passes, the bot builds `<Title> BUYER.zip` with clean WAVs and MP3s and nothing private inside, and the report pastes straight into `qa.md`. The .exe + its folder copied to another PC with no internet still works.
