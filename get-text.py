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
VAD = "fsmn-vad"
PUNC = "ct-punc"
SAMPLING = 16000
JOBS_DIR = Path("jobs")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# 延迟加载模型
_model = None

def get_model():
    """延迟加载语音识别模型"""
    global _model
    if _model is None:
        _model = AutoModel(model=MODEL, vad_model=VAD, punc_model=PUNC)
    return _model


# ---------- 工具函数 ----------
def get_task_dir(url: str) -> Path:
    """根据URL生成唯一任务目录路径"""
    safe = hashlib.md5(url.encode()).hexdigest()
    task_dir = JOBS_DIR / safe
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir


def download_raw(url: str, task_dir: Path) -> tuple[Path, dict]:
    """下载原始文件并返回文件路径和元信息"""
    step_dir = task_dir / "01_download"
    step_dir.mkdir(exist_ok=True)
    done_file = step_dir / "donefile"
    info_json = step_dir / "raw.info.json"

    if done_file.exists():
        print("📦 已存在原始文件和元信息，跳过下载")
        raw_file = next(f for f in step_dir.iterdir() if f.stem == "raw" and f.suffix != ".json")
        with open(info_json, encoding="utf-8") as f:
            return raw_file, json.load(f)

    cmd = [
        "yt-dlp",
        "--cookies-from-browser",
        "firefox",
        "-f",
        "worst*",
        "-o",
        "raw.%(ext)s",
        "--write-info-json",
        "--no-playlist",
        url,
    ]
    subprocess.run(cmd, cwd=step_dir, check=True)

    raw_file = next(f for f in step_dir.iterdir() if f.stem == "raw" and f.suffix != ".json")
    with open(info_json, encoding="utf-8") as f:
        info = json.load(f)

    done_file.touch()
    return raw_file, info


def convert_to_wav(raw_path: Path, wav_path: Path):
    """将原始文件转换为WAV音频文件"""
    step_dir = wav_path.parent
    step_dir.mkdir(exist_ok=True)
    done_file = step_dir / "donefile"
    if done_file.exists():
        print("🎵 已存在WAV文件，跳过转码")
        return

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(raw_path),
        "-ar",
        str(SAMPLING),
        "-ac",
        "1",
        "-sample_fmt",
        "s16",
        str(wav_path),
    ]
    subprocess.run(cmd, check=True)
    done_file.touch()


def transcribe_audio(wav_path: Path, transcript_path: Path) -> str:
    """语音识别，返回转录文本"""
    step_dir = transcript_path.parent
    step_dir.mkdir(exist_ok=True)
    done_file = step_dir / "donefile"
    if done_file.exists():
        print("📝 已存在转录结果，跳过语音识别")
        return transcript_path.read_text(encoding="utf-8")

    model = get_model()
    res = model.generate(input=str(wav_path))[0]
    text = res["text"]
    transcript_path.write_text(text, encoding="utf-8")
    done_file.touch()
    return text


def export_transcript(raw_info: dict, transcript_text: str) -> Path:
    """导出最终转录文本到输出目录"""

    ts = int(raw_info["timestamp"])
    dt = datetime.fromtimestamp(ts)
    uploader = raw_info["uploader"]
    title = raw_info["title"]

    safe_name = "".join(
        c if c.isalnum() or c in " -_.,()[]【】" else "_"
        for c in f"{dt:%y%m%d%H%M%S}-{uploader}-{title}.txt"
    )
    final_path = OUTPUT_DIR / safe_name
    if final_path.exists():
        print("💾 已存在最终文本，跳过导出")
        return final_path

    final_path.write_text(transcript_text, encoding="utf-8")
    return final_path


# ---------- 主流程 ----------
def process_video(url: str):
    """处理视频URL的完整流程"""
    JOBS_DIR.mkdir(exist_ok=True)
    task_dir = get_task_dir(url)

    # 1. 下载原始文件
    raw_path, raw_info = download_raw(url, task_dir)

    # 2. 转换为音频
    wav_dir = task_dir / "02_audio"
    wav_path = wav_dir / "audio.wav"
    convert_to_wav(raw_path, wav_path)

    # 3. 语音识别
    transcript_dir = task_dir / "03_transcript"
    transcript_path = transcript_dir / "transcript.txt"
    transcript_text = transcribe_audio(wav_path, transcript_path)

    # 4. 导出结果
    final_path = export_transcript(raw_info, transcript_text)
    print(f"✅ 完成：{final_path.resolve()}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python get-text.py <URL>")
        sys.exit(1)
    process_video(sys.argv[1])
