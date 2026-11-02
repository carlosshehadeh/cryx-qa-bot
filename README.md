# Cryx QA Bot

A private Windows desktop app for Cryx. Drop a finished Ableton export folder
on it and in under a minute it checks every stem and master against the
marketplace rules, proves the stems rebuild the mix (the null test), strips
personal info and hidden tags, makes 320 kbps MP3s, and builds a clean buyer
zip, with a pass/fail report to paste into the track's `qa.md`.

It only reads the export. It never touches the Ableton project, never writes
or changes music, and never edits the original files: cleaned copies go to a
new `<Title> BUYER` folder. Everything runs offline. Read [BRIEF.md](BRIEF.md) first.

## Build the .exe (Windows)

1. Python 3.12+ from python.org with "Add to PATH" ticked (the same install as MIDI Vault).
2. Double-click `build_exe.bat`. It makes a build environment, installs the
   libraries, runs the automated checks (a few minutes), and builds
   `dist\Cryx QA Bot.exe` (the window) and `dist\cryx-qa.exe` (the command line).
3. Keep both in one folder. On first run they create `CryxQAData` next to themselves.

## The export folder

```
<Track Title> EXPORT\
  Masters\
    <Title> (Extended Mix).wav        mastered, rack ON
    <Title> (Radio Mix).wav           mastered, rack ON
  Stems Extended\
    01 Kick.wav, 02 Bass Sub.wav ...   rack OFF, all individual tracks
    A Reverb Short.wav, B Delay.wav... returns as their own stems
    Main.wav                           the unmastered mix (rack OFF): null test, then packed renamed
  Stems Radio\                         same, if radio stems are delivered
  Unmastered\                          <Title> (Radio Mix).wav: the unmastered radio mix (rack OFF)
  MIDI\                                one .mid per melodic part (Bass.mid, Lead.mid ...)
  Project\                             optional: the .als + samples
```

`Main.wav` is the unmastered extended mix. All three sites want the unmastered
mix in the package, so the bot puts it in under the name each site asks for.

Folder and file name patterns can be changed in Settings.

## Using it

- Drop the export folder on the window (or click the drop zone). The checks run
  straight away: red = FAIL, yellow = WARN, green = PASS. Click a row for the
  fix and the numbers.
- Pick the profile: the website you're uploading to plus the genre
  (EDM GP, The Ghost Production or House of Tracks, each with Tech House or
  Melodic House & Techno). BPM comes from the genre; change it to your track's
  BPM so the null test names the right bars.
- **Build buyer zip** is greyed out while anything fails. Warnings need one
  click: "I checked these".
- **Copy report for qa.md** puts the Markdown report on the clipboard.
- **History** shows past runs per track, so you can see it go from FAIL to PASS.
- **Settings**: fill in the banned words (real name, old and new artist names,
  email, `C:\Users\...`) once. Until then `privacy_names` warns.

Output, next to the export folder (or the folder set in Settings):

```
<Title> BUYER\              clean WAV copies (only fmt + data), MP3s, stems, optional Project
<Title> BUYER.zip
<Title> QA REPORT.md        stays with you, never in the zip
```

An earlier `<Title> BUYER` folder made by the bot is replaced on the next build.

## Command line

```
cryx-qa check "D:\...\My Track EXPORT" --profile edmgp-tech-house
cryx-qa check "D:\...\My Track EXPORT" --build --ok-warnings --report "D:\...\qa-run.md"
cryx-qa profiles
```

Exit code: 0 = all pass, 1 = warnings only, 2 = at least one fail, 3 = folder or
profile not usable. From source: `python -m qabot check ...`.

## Rules

A profile = one website file (`rules/sites/edmgp.json`, `tgp.json`, `hot.json`)
+ one genre file (`rules/genres/tech-house.json`, `melodic-house-techno.json`).
The website file holds every number and the zip layout; the genre file holds
BPM and the planned length. A new genre is one small file and shows up for
every website. The bundled files are copied to `CryxQAData\rules` on first run;
edit those (Settings > Open rules folder) when a platform changes a number.
Your edits are kept across updates.

Main differences (from the sites' seller pages, checked 2026-10-30; the
`source` field in each file links them):

| | EDM GP | The Ghost Production | House of Tracks |
|---|---|---|---|
| WAV | 44.1 kHz / 16-bit | 44.1 kHz / 16 or 24-bit | 44.1 or 48 kHz / 24 or 32-bit |
| Master loudness | -9 to -2 LUFS | no target | -9 to -5 LUFS |
| Master peak | -0.3 to 0 dB | -0.1 dB or lower | -2 to 0 dB |
| Unmastered peak | -3 to -6 dB true peak, same for every version | -3 dB or lower | no rule |
| Length | 2:00 to 8:00 | extended 4-8 min, radio 2-3 min (recommended) | 2:30 to 8:00 |
| Stems | 10 or more, no groups/buses | no minimum | buses wanted; names say only the sound |
| MP3 320 | masters | masters and unmastered | none |
| Zip | Extended mix / Radio mix / Unmastered mixes / Stems / MIDI | Mastered / Unmastered / Stems / MIDI / DAW_Project | masters.zip, stems.zip, midi.zip |
| Exclusive | sold only on EDM GP | | 4 months |

Rules the bot can't measure (exclusivity, samples, vocals, artwork) are listed
in each report under "Site rules to remember".

## Portable mode

Everything the app writes lives in `CryxQAData` beside the .exe, never in AppData:

| File | What |
|---|---|
| `config.json` | banned words, default profile, output folder, MP3 on/off, folder patterns |
| `rules\*.json` | marketplace rules |
| `history.json` | one line per run |

Copy the .exe files and `CryxQAData` to another PC and it works offline.

## Adding a check

1. New file in `qabot/checks/` with `ID` and `run(ctx)` returning `Result`s.
2. One line in the `CHECKS` list in `qabot/checks/__init__.py`.
3. A test with a fixture that should PASS and one that should FAIL
   (`tests/make_fixtures.py` makes fake exports from tones, noise and clicks).

Numbers belong in `rules/*.json`, never in the check. A check that crashes shows
as FAIL "check crashed: ..." and the others still run.

## Run from source / develop

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python main.py                 # the window
python -m qabot check "..."    # the command line
python -m tests.make_fixtures  # fake exports in test_output\ to try the app
pytest
```

Never upload sale-track audio to Claude: build and test with the generated
fixtures, and run real exports locally.
