#!/usr/bin/env python3
"""
一键下载-转码-语音识别（中文）
用法: python pipeline.py <URL>
"""
import sys
import subprocess
import tempfile
from pathlib import Path
from funasr import AutoModel

# ---------- 配置 ----------
MODEL = "paraformer-zh"
VAD   = "fsmn-vad"
PUNC  = "ct-punc"
SAMPLING = 16000

# ---------- 预加载模型 ----------
MODEL_OBJ = AutoModel(model=MODEL, vad_model=VAD, punc_model=PUNC)

# ---------- 工具函数 ----------
def download(url: str, out_dir: Path) -> Path:
    """返回下载后的音频文件路径（确保是刚刚下载的）"""
    cmd = [
        "yt-dlp",
        "-f", "bestaudio/best",
        "-o", "%(title)s.%(ext)s",
        "--no-playlist",
        url
    ]
    subprocess.run(cmd, cwd=out_dir, check=True)
    # 目录里此时只有刚下载的文件
    return next(out_dir.iterdir())


def to_wav(src: Path, dst: Path):
    """ffmpeg 转码 -> 16 kHz 单声道 s16le wav"""
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-ar", str(SAMPLING),
        "-ac", "1",
        "-sample_fmt", "s16",
        str(dst)
    ]
    subprocess.run(cmd, check=True)


def asr(wav: Path) -> str:
    """FunASR 识别，返回文本"""
    res = MODEL_OBJ.generate(input=str(wav))[0]
    return res["text"]


# ---------- 主流程 ----------
def main(url: str):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        media = download(url, tmp)
        wav = tmp / "audio.wav"
        to_wav(media, wav)
        text = asr(wav)
        out_txt = Path(media.stem + ".txt")
        out_txt.write_text(text, encoding="utf-8")
        print(f"✅ 完成：{out_txt.resolve()}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python pipeline.py <URL>")
        sys.exit(1)
    main(sys.argv[1])
