一键把任意在线视频转成中文文字，用 yt-dlp → ffmpeg → FunASR 把视频变成纯文本，方便喂给 LLM 做总结。

工作原理
```
URL → yt-dlp → 音频文件 → ffmpeg → 16 kHz WAV → FunASR → 中文文本
```

使用方法
```
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python get-text.py "https://www.youtube.com/watch?v=XXXXXXX"
```
运行后在脚本同目录生成 <视频标题>.txt（UTF-8）。

环境要求
```
Python ≥ 3.8
FFmpeg（系统包或 https://ffmpeg.org 下载）
yt-dlp（requirements.txt 自动安装）
FunASR 及模型（首次运行自动下载，约 1 GB）
```

小技巧
```
第一次运行会下载 Paraformer 模型，请保持网络畅通。
如需英文或其它语言，把脚本里的 MODEL 改成对应模型即可。
```
