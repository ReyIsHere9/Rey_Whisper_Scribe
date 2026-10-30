# Whisper Scribe

Offline transcription for **Persian, English, and mixed Persian/English** recordings, with speaker labels, playback, editing, and TXT/SRT export.

Whisper Scribe is a Windows desktop app built with PySide6, [faster-whisper](https://github.com/SYSTRAN/faster-whisper), and [pyannote.audio](https://github.com/pyannote/pyannote-audio). Audio stays on your machine. The only network use is the one-time model download.

![Whisper Scribe light theme](docs/screenshot-light.png)

<p align="center"><img src="docs/screenshot-dark.png" alt="Whisper Scribe dark theme" width="70%"></p>

## Features

- Persian (`fa`), English (`en`), mixed Persian/English, and auto-detect modes
- Whisper **large-v3** by default (optional Turbo model)
- Word-level timestamps and speaker diarization
- Global or per-job speaker library, speaker merge, and manual add
- Per-line speaker correction: select one or more transcript lines and assign them to a speaker
- Click-to-seek playback, transcript editing, and TXT/SRT export
- Live progress, elapsed time, and cancel while transcribing
- English and Persian/RTL UI, light and dark themes
- Everything runs locally after the models are downloaded

## Requirements

- Windows 11 (64-bit)
- Python 3.13
- FFmpeg on `PATH` (used to extract audio from video/audio files)
- NVIDIA GPU with a CUDA 12.6 driver **strongly recommended** (CPU works, but is much slower)
- About 8 GB free disk space for Python packages and models

## Installation

### 1. Get the code

```powershell
git clone https://github.com/ReyIsHere9/Rey_Whisper_Scribe.git
cd Rey_Whisper_Scribe
```

### 2. Create the environment and install dependencies

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip

pip install -r requirements.txt

# GPU (CUDA 12.6):
pip install torch==2.11.0 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cu126

# CPU only (slower):
# pip install torch==2.11.0 torchaudio==2.11.0

pip install -r requirements-ml.txt
```

Install FFmpeg if you do not have it:

```powershell
winget install --id Gyan.FFmpeg -e
```

Open a new terminal after installing FFmpeg so the `ffmpeg` command is found.

### 3. Get a Hugging Face token and accept the diarization model

Speaker diarization uses a gated model. You only need to do this once per Hugging Face account:

1. Create a **read** token: <https://huggingface.co/settings/tokens>
2. **Accept the terms** (click **Agree and access repository**):
   **<https://huggingface.co/pyannote/speaker-diarization-community-1>**
3. Save the token on a single line in `tokenhg.txt` at the root of this project, or set the `HF_TOKEN` environment variable.

```text
hf_your_read_token_here
```

`tokenhg.txt` is ignored by git. Never commit it. A token is required only for the first diarization download; a machine that only loads an already-copied model cache can work fully offline.

> If you do **not** need speaker labels, you can skip the token and uncheck speaker diarization in the Advanced section of the New Transcription dialog. Whisper will still transcribe the file.

### 4. Download the models

Run these commands from the project root. The easy way (Whisper + diarization, with a log in `logs/download_models.log`):

```powershell
download_models.bat
```

If the Whisper download stalls or gets interrupted, use the resumable downloader:

```powershell
powershell -ExecutionPolicy Bypass -File tools\download_whisper_curl.ps1
```

This downloads the files from the public Hugging Face repositories:

- Whisper: [`Systran/faster-whisper-large-v3`](https://huggingface.co/Systran/faster-whisper-large-v3) — about **2.9 GB**, stored in `<repo>\models\large-v3`
- Diarization: [`pyannote/speaker-diarization-community-1`](https://huggingface.co/pyannote/speaker-diarization-community-1) — stored in `<repo>\models\hf\hub`

### 5. Run

```powershell
run.bat
```

or:

```powershell
.venv\Scripts\python.exe -m app.main
```

`run.bat` creates the virtual environment and installs the lightweight UI dependencies if they are missing. The heavy ML dependencies from step 2 must be installed once manually.

## Where the models live (and copying to another PC)

Everything stays inside the project folder:

```text
<repo>\models\large-v3\model.bin
<repo>\models\hf\hub\models--pyannote--speaker-diarization-community-1
```

`models\` and `data\` are git-ignored. Copy the whole `models` folder to another checkout on another PC and the app will use it; no re-download is needed for either Whisper or diarization.

If you keep models somewhere else (for example an external drive), set `WHISPERSCRIBE_MODELS` to the folder that **contains** `large-v3`:

```powershell
setx WHISPERSCRIBE_MODELS "E:\Models\WhisperScribe"
```

The Hugging Face cache follows that folder (`<that folder>\hf\hub`). A token is only needed on a machine that has to download the diarization model for the first time.

Optional: the **Turbo** model is available in Advanced options. It is not downloaded by default; selecting it downloads `large-v3-turbo` on first use.

## Using the app

1. Click **New transcription** (or drag a file onto the window).
2. Choose an audio or video file.
3. Pick a language:
   - **Persian** — forces Persian; English words are usually kept in Latin script.
   - **Mixed (Persian + English)** — auto-detects; recommended for Persian meetings with English terms.
   - **English** — forces English.
   - **Auto detect** — Whisper decides.
   If a mixed file starts with a long English intro, Whisper may auto-detect English; in that case choose **Persian** instead.
4. Optional (Advanced): set **Expected speakers**. `Auto` (0) is the best default; set a number if you know it.
5. Click **Start**. Progress, elapsed time, and a **Cancel** button appear at the bottom.
6. When finished: play the audio, click a transcript line to seek, edit text, fix speaker labels, merge speakers, or export TXT/SRT.

Exports default to `<repo>\data\exports`.

### What diarization is

Diarization is the **“who spoke when”** pass. It splits the audio into speaker turns and labels each transcript segment with a speaker (`Speaker 00`, `Speaker 01`, …). It never combines people's text into one block and it never rewrites the transcript. It only adds a speaker label to each line.

### Fixing a wrong speaker label

**Merge mode** in the speaker panel is speaker-level: it tells the app that two labels are the same person, so all segments of one label move to the other. The text stays as separate lines.

To fix a single line (for example when someone talks between two people):

1. Click **Select** in the transcript header.
2. Click one or more transcript lines; they get a checkbox and an accent border.
3. Click **Assign N to speaker…**.
4. Choose an existing speaker or **New speaker…**.

Only the selected segments change. The timeline, text, and all other lines stay untouched. Click **Done** to leave selection mode.

Other speaker tools:

- The speaker scope can be **Global** (shared library) or **Job only**. The New Transcription dialog sets the scope for the new job.
- **Double-click a speaker** in the panel to rename it.
- **Add speaker** creates an empty speaker entry for manual labeling.
- Voice enrollment is not part of this build yet.

### Privacy and local data

- Audio and transcripts are processed locally.
- Everything is under the project: `<repo>\models`, `<repo>\data`, `<repo>\logs`.
- Database: `<repo>\data\whisper_scribe.db`
- Exports: `<repo>\data\exports`
- Delete the database file to reset the demo library and all jobs.
- `models\`, `data\`, `logs\`, and `shots\` are git-ignored.

## Performance

Whisper large-v3 is accurate but heavy. On an RTX 4070 Laptop, a 2-hour recording typically takes roughly 10–30 minutes to transcribe and another 5–15 minutes to diarize, depending on speech density and silence. The app shows live progress and elapsed time.

- Cancel works during transcription. Diarization is a single model pass and cannot be interrupted mid-stage; cancellation takes effect after it finishes.
- The first model load after launch takes a few seconds.
- CPU-only processing is much slower; GPU is strongly recommended.

## Troubleshooting

**`403 Forbidden` or “gated model”**
Accept the terms while logged in as the token owner:
<https://huggingface.co/pyannote/speaker-diarization-community-1>
Then make sure `tokenhg.txt` contains a valid read token (or set `HF_TOKEN`).

**“Transcription engine not installed”**
Install the heavy dependencies:
```powershell
pip install -r requirements-ml.txt
```

**CUDA is not used**
Check the GPU stack:
```powershell
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```
Reinstall the CUDA build of torch from the command in step 2.

**Whisper download stalls**
Use `tools\download_whisper_curl.ps1`. The app and downloader set `HF_HUB_DISABLE_XET=1` to avoid the Xet transfer path, which can stall on some networks.

**`ffmpeg` not found**
Install FFmpeg and add its `bin` folder to `PATH`, then reopen the terminal.

**Model loading is slow the first time**
Antivirus/Defender can scan the 3 GB model. Later launches are faster.

**`libtorchcodec` / FFmpeg DLL errors**
The app decodes extracted WAV files itself and passes tensors to pyannote, so diarization does not depend on torchcodec’s FFmpeg decoder. Keep `torchcodec==0.17.0` installed as required by pyannote; if you see an error, reinstall the exact versions from `requirements-ml.txt`.

**Long job and the app was closed**
On startup, a job that was processing is marked failed, unless partial transcript segments were already saved; in that case it is marked transcribed so you can still read/export them.

## Development

```powershell
pytest -q
ruff check .
```

Generated assets are committed. To rebuild them from the design masters:

```powershell
$env:WHISPERSCRIBE_ASSET_MASTERS = "X:\Assets\Whisper-Scribe"
python tools\build_assets.py
```

You can also pass `--masters "X:\Assets\Whisper-Scribe"`.

Take a screenshot (used for the README):

```powershell
python -m app.main --theme dark --lang en --screenshot shots/preview.png
```

Project layout:

```text
app/
  core/       transcription, diarization, pipeline, audio, export, normalization
  ui/         PySide6 widgets, dialog, worker thread, i18n
  db/         SQLite schema and data access
  theme/      palettes and stylesheet
  assets/     generated textures/icons
tools/        model downloaders, smoke test, asset builder
tests/        pytest suite
docs/         README screenshots
```

## شروع سریع (فارسی)

۱. پایتون ۳.۱۳ و FFmpeg را نصب کنید.
۲. محیط مجازی و وابستگی‌ها را نصب کنید (مرحله ۲ بالا).
۳. در سایت Hugging Face یک توکن Read بسازید و شرایط مدل تفکیک گوینده را بپذیرید:
<https://huggingface.co/pyannote/speaker-diarization-community-1>
سپس توکن را در فایل `tokenhg.txt` قرار دهید.
۴. مدل‌ها را دانلود کنید:
```powershell
download_models.bat
```
۵. برنامه را اجرا کنید:
```powershell
run.bat
```
۶. **New transcription** را بزنید، فایل را انتخاب کنید، زبان را روی **Mixed** برای فارسی + انگلیسی بگذارید و Start را بزنید.

## Credits

- Visual design and the Vintage Burgundy R/quill emblem: the project owner
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and [OpenAI Whisper](https://github.com/openai/whisper)
- [pyannote.audio](https://github.com/pyannote/pyannote-audio)
- [PySide6 / Qt for Python](https://doc.qt.io/qtforpython/)
- [FFmpeg](https://ffmpeg.org/)
