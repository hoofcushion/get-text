#!/usr/bin/env python3
"""
一键下载-转码-语音识别（中文）
用法: python get-text.py <URL>
"""
import hashlib
import json
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from funasr import AutoModel

# ---------- 配置 ----------
MODEL = "paraformer-zh"
VAD   = "fsmn-vad"
PUNC  = "ct-punc"
SAMPLING = 16000
JOBS_DIR   = Path("jobs")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------- 工具函数 ----------
def safe_task_dir(url: str) -> Path:
    safe = hashlib.md5(url.encode()).hexdigest()
    task_dir = JOBS_DIR / safe
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir

def download(url: str, task_dir: Path) -> tuple[Path, dict]:
    info_json = task_dir / "raw.info.json"
    raw_files = [f for f in task_dir.glob("raw.*") if f.suffix != ".json"]

    if info_json.exists() and raw_files:
        print("📦 已存在 raw 文件与 info.json，跳过下载")
        with open(info_json, encoding="utf-8") as f:
            return raw_files[0], json.load(f)

    cmd = [
        "yt-dlp",
        "--cookies-from-browser", "firefox",
        "-f", "worst*",
        "-o", "raw.%(ext)s",
        "--write-info-json",
        "--no-playlist",
        url,
    ]
    subprocess.run(cmd, cwd=task_dir, check=True)

    with open(info_json, encoding="utf-8") as f:
        info = json.load(f)
    raw_file = next(f for f in task_dir.iterdir()
                    if f.stem == "raw" and f.suffix != ".json")
    return raw_file, info

def to_wav(src: Path, dst: Path):
    if dst.exists():
        print("🎵 已存在 wav 文件，跳过转码")
        return
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-ar", str(SAMPLING),
        "-ac", "1",
        "-sample_fmt", "s16",
        str(dst),
    ]
    subprocess.run(cmd, check=True)

def asr(wav: Path, txt: Path):
    if txt.exists():
        print("📝 已存在识别结果，跳过 ASR")
        return txt.read_text(encoding="utf-8")
    model = AutoModel(model=MODEL, vad_model=VAD, punc_model=PUNC)
    res = model.generate(input=str(wav))[0]
    text = res["text"]
    txt.write_text(text, encoding="utf-8")
    return text

def export_result(task_dir: Path, info: dict, text: str) -> Path:
    """把结果文本导出到 output/，返回最终 txt 路径"""
    ts       = int(info["timestamp"])
    dt       = datetime.fromtimestamp(ts)
    uploader = info["uploader"]
    title    = info["title"]

    safe_name = "".join(c if c.isalnum() or c in " -_.,()[]【】" else "_"
                        for c in f"{dt:%y%m%d%H%M%S}-{uploader}-{title}.txt")
    final_path = OUTPUT_DIR / safe_name
    if final_path.exists():
        print("💾 已存在最终文本，跳过导出")
        return final_path
    final_path.write_text(text, encoding="utf-8")
    return final_path

# ---------- 主流程 ----------
def main(url: str):
    JOBS_DIR.mkdir(exist_ok=True)
    task_dir = safe_task_dir(url)

    raw_file, info = download(url, task_dir)

    wav_file = task_dir / "audio.wav"
    to_wav(raw_file, wav_file)

    txt_file = task_dir / "transcript.txt"
    text = asr(wav_file, txt_file)

    final_path = export_result(task_dir, info, text)
    print(f"✅ 完成：{final_path.resolve()}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python get-text.py <URL>")
        sys.exit(1)
    main(sys.argv[1])
