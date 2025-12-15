#!/usr/bin/env python3
"""
一键下载-转码-语音识别（中文）
用法: python init.py <URL或文件路径>
"""
import hashlib
import json
import sys
import subprocess
import shutil
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


def check_ffmpeg():
    """检查 ffmpeg 是否安装"""
    if shutil.which("ffmpeg") is None:
        print("错误: ffmpeg 未安装")
        print("请先安装 ffmpeg:")
        print("  Ubuntu/Debian: sudo apt install ffmpeg")
        print("  Arch: sudo pacman -S ffmpeg")
        print("  macOS: brew install ffmpeg")
        sys.exit(1)


# 延迟加载模型
_model = None

def get_model():
    """延迟加载语音识别模型"""
    global _model
    if _model is None:
        _model = AutoModel(model=MODEL, vad_model=VAD, punc_model=PUNC)
    return _model


# ---------- 工具函数 ----------
def get_task_dir(input_path: str) -> Path:
    """根据输入路径生成唯一任务目录路径"""
    safe = hashlib.md5(input_path.encode()).hexdigest()
    task_dir = JOBS_DIR / safe
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir


def download_or_use_file(input_arg: str, task_dir: Path) -> tuple[Path, dict]:
    """
    下载原始文件或使用现有文件
    返回文件路径和元信息
    """
    step_dir = task_dir / "01_download"
    step_dir.mkdir(exist_ok=True)
    done_file = step_dir / "donefile"
    info_json = step_dir / "raw.info.json"

    # 如果已存在处理过的文件，直接返回
    if done_file.exists() and info_json.exists():
        print("📦 已存在原始文件和元信息，跳过下载/复制")
        raw_file = next(f for f in step_dir.iterdir() if f.stem == "raw" and f.suffix != ".json")
        with open(info_json, encoding="utf-8") as f:
            return raw_file, json.load(f)
    
    input_path = Path(input_arg)
    
    # 如果传入的是文件路径
    if input_path.exists():
        print(f"📁 使用本地文件: {input_arg}")
        
        # 复制文件到任务目录
        from shutil import copy2
        
        # 确定文件扩展名
        ext = input_path.suffix
        
        # 创建原始文件副本
        raw_file = step_dir / f"raw{ext}"
        copy2(input_path, raw_file)
        
        # 创建元信息
        info = {
            "title": input_path.stem,
            "uploader": "local_file",
            "timestamp": datetime.now().timestamp(),
            "_input_file": str(input_path.resolve()),
            "_type": "local_file"
        }
        
        with open(info_json, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
    
    else:  # 传入的是URL
        print(f"🌐 下载URL: {input_arg}")
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
            input_arg,
        ]
        subprocess.run(cmd, cwd=step_dir, check=True)
        
        # 读取下载的元信息
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
def process(input_arg: str):
    """处理输入参数（URL或文件路径）的完整流程"""
    JOBS_DIR.mkdir(exist_ok=True)
    task_dir = get_task_dir(input_arg)

    # 1. 下载原始文件或使用现有文件
    raw_path, raw_info = download_or_use_file(input_arg, task_dir)

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
    # 1. 检查参数数量
    if len(sys.argv) != 2:
        print("用法: python init.py <URL或文件路径>")
        print("示例1: python init.py https://www.youtube.com/watch?v=example")
        print("示例2: python init.py ./video.mp4")
        sys.exit(1)
    
    # 2. 检查 ffmpeg
    check_ffmpeg()
    
    # 3. 执行主流程
    process(sys.argv[1])
