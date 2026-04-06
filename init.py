import hashlib
import json
import sys
import subprocess
import shutil
import argparse
import time
from datetime import datetime
from pathlib import Path
import model
from process import to_word_timestamp_list

SPEECH_MODEL_ID = "paraformer-zh"
VAD_MODEL_ID = "fsmn-vad"
PUNC_MODEL_ID = "ct-punc"
AUDIO_SAMPLING_RATE = 16000
TEMPORARY_JOBS_DIRECTORY = Path("jobs")
TEMPORARY_JOBS_DIRECTORY.mkdir(exist_ok=True)
FINAL_OUTPUT_DIRECTORY = Path("output")
FINAL_OUTPUT_DIRECTORY.mkdir(exist_ok=True)
FORCE_CPU_INFERENCE = False


def import_srt_generator_class():
    from srt import SRTGenerator

    return SRTGenerator


def verify_ffmpeg_installation():
    if shutil.which("ffmpeg") is None:
        print("[错误] ffmpeg 未安装，请先安装 ffmpeg 并添加到系统环境变量")
        sys.exit(1)


def get_initialized_speech_model(logger_callback=print):
    """使用 model.py 提供的接口获取模型实例"""
    compute_device = "cpu" if FORCE_CPU_INFERENCE else "cuda"
    logger_callback(
        f"[模型初始化] 正在加载语音识别模型 (设备: {'CPU' if FORCE_CPU_INFERENCE else 'GPU'})..."
    )
    start_timestamp = time.time()

    speech_model = model.request_model(
        SPEECH_MODEL_ID,
        lambda AutoModel: AutoModel(
            model=SPEECH_MODEL_ID,
            vad_model=VAD_MODEL_ID,
            punc_model=None,
            device=compute_device,
        ),
    )

    logger_callback(
        f"[模型初始化] 加载完成，耗时: {time.time() - start_timestamp:.2f}s"
    )
    return speech_model


def get_initialized_punc_model(logger_callback=print):
    """使用 model.py 提供的接口获取模型实例"""
    compute_device = "cpu" if FORCE_CPU_INFERENCE else "cuda"
    logger_callback(
        f"[模型初始化] 正在加载标点恢复模型 (设备: {'CPU' if FORCE_CPU_INFERENCE else 'GPU'})..."
    )
    start_timestamp = time.time()

    speech_model = model.request_model(
        PUNC_MODEL_ID,
        lambda AutoModel: AutoModel(
            model=PUNC_MODEL_ID,
            device=compute_device,
        ),
    )

    logger_callback(
        f"[模型初始化] 加载完成，耗时: {time.time() - start_timestamp:.2f}s"
    )
    return speech_model


def generate_task_unique_directory(input_source_string: str) -> Path:
    unique_hash = hashlib.md5(input_source_string.encode()).hexdigest()
    task_specific_dir = TEMPORARY_JOBS_DIRECTORY / unique_hash
    task_specific_dir.mkdir(parents=True, exist_ok=True)
    return task_specific_dir


def acquire_input_resource(
    input_argument: str, task_directory: Path, logger_callback=print
) -> tuple[Path, dict]:
    download_step_dir = task_directory / "01_download"
    download_step_dir.mkdir(exist_ok=True)
    completion_flag_file = download_step_dir / "donefile"
    metadata_json_file = download_step_dir / "raw.info.json"

    if completion_flag_file.exists() and metadata_json_file.exists():
        logger_callback("检测到已存在缓存资源，跳过下载或复制环节")
        raw_resource_file = next(
            f
            for f in download_step_dir.iterdir()
            if f.stem == "raw" and f.suffix != ".json"
        )
        with open(metadata_json_file, encoding="utf-8") as f:
            return raw_resource_file, json.load(f)

    potential_local_path = Path(input_argument)
    if potential_local_path.exists():
        logger_callback(f"正在处理本地文件: {potential_local_path.name}")
        file_extension = potential_local_path.suffix
        raw_resource_file = download_step_dir / f"raw{file_extension}"
        shutil.copy2(potential_local_path, raw_resource_file)
        resource_metadata = {
            "title": potential_local_path.stem,
            "uploader": "local_user",
            "timestamp": datetime.now().timestamp(),
        }
    else:
        logger_callback(f"正在尝试从网络获取资源: {input_argument}")
        yt_dlp_command = [
            "yt-dlp",
            "--cookies-from-browser",
            "firefox",
            "-f",
            "worst*",
            "-o",
            "raw.%(ext)s",
            "--write-info-json",
            "--no-playlist",
            input_argument,
        ]
        execution_result = subprocess.run(
            yt_dlp_command, cwd=download_step_dir, capture_output=True, text=True
        )
        if execution_result.returncode != 0:
            logger_callback(f"[错误] 下载失败详情: {execution_result.stderr}")
            raise RuntimeError(f"无法获取网络资源: {input_argument}")

        raw_resource_file = next(
            f
            for f in download_step_dir.iterdir()
            if f.stem == "raw" and f.suffix != ".json"
        )

        yt_dlp_info_file = download_step_dir / "raw.info.json"
        if yt_dlp_info_file.exists():
            with open(yt_dlp_info_file, encoding="utf-8") as f:
                yt_dlp_info = json.load(f)
        else:
            yt_dlp_info = {}

        resource_metadata = {
            "title": yt_dlp_info.get("title", "unknown"),
            "uploader": yt_dlp_info.get("uploader", "unknown"),
            "timestamp": yt_dlp_info.get("timestamp", datetime.now().timestamp()),
            "original_url": input_argument,
        }

    with open(metadata_json_file, "w", encoding="utf-8") as f:
        json.dump(resource_metadata, f, ensure_ascii=False, indent=2)

    completion_flag_file.touch()
    logger_callback("资源定位成功")
    return raw_resource_file, resource_metadata


def extract_standard_audio_wav(
    raw_media_path: Path, target_wav_path: Path, logger_callback=print
):
    step_completion_flag = target_wav_path.parent / "donefile"
    if step_completion_flag.exists():
        logger_callback("检测到已转换的音频缓存，跳过转码")
        return
    logger_callback(f"正在执行音频标准化 (采样率: {AUDIO_SAMPLING_RATE}Hz)...")
    target_wav_path.parent.mkdir(exist_ok=True)
    start_timestamp = time.time()
    ffmpeg_command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(raw_media_path),
        "-ar",
        str(AUDIO_SAMPLING_RATE),
        "-ac",
        "1",
        "-sample_fmt",
        "s16",
        str(target_wav_path),
    ]
    subprocess.run(ffmpeg_command, check=True)
    step_completion_flag.touch()
    logger_callback(f"音频转码完成，耗时: {time.time() - start_timestamp:.2f}s")


def perform_speech_recognition(
    wav_file_path: Path, result_storage_path: Path, logger_callback=print
) -> dict:
    recognition_completion_flag = result_storage_path.parent / "donefile"
    if recognition_completion_flag.exists():
        logger_callback("检测到语音识别缓存结果，直接读取")
        with open(result_storage_path, "r", encoding="utf-8") as f:
            return json.load(f)
    speech_model = get_initialized_speech_model(logger_callback=logger_callback)
    logger_callback("开始语音识别推理 (此过程取决于硬件性能)...")
    start_timestamp = time.time()
    inference_result = speech_model.generate(input=str(wav_file_path))[0]
    formatted_result_data = {
        "text": inference_result["text"],
        "timestamp": inference_result.get("timestamp", []),
        "raw_inference_output": inference_result,
    }
    result_storage_path.parent.mkdir(exist_ok=True)
    with open(result_storage_path, "w", encoding="utf-8") as f:
        json.dump(formatted_result_data, f, ensure_ascii=False, indent=2)
    recognition_completion_flag.touch()
    logger_callback(f"识别完毕，推理引擎耗时: {time.time() - start_timestamp:.2f}s")
    return formatted_result_data


def generate_text_with_punctuation(
    recognition_data: dict, task_directory: Path, logger_callback=print
) -> Path:
    """第四步：生成带标点的文本文件（保存在任务目录中）"""
    text_output_dir = task_directory / "04_text_output"
    text_output_dir.mkdir(exist_ok=True)
    txt_file_path = text_output_dir / "text_with_punctuation.txt"
    
    completion_flag = text_output_dir / "donefile"
    if completion_flag.exists():
        logger_callback("检测到已生成的文本文件缓存，跳过标点恢复")
        return txt_file_path
    
    punc_model = get_initialized_punc_model(logger_callback=logger_callback)
    logger_callback("开始标点恢复推理...")
    start_timestamp = time.time()
    text_with_punctuation = punc_model.generate(input=recognition_data["text"])[0]["text"]
    logger_callback(f"标点恢复完成，耗时: {time.time() - start_timestamp:.2f}s")
    
    txt_file_path.write_text(text_with_punctuation, encoding="utf-8")
    completion_flag.touch()
    return txt_file_path


def generate_srt_file(
    recognition_data: dict, task_directory: Path, logger_callback=print
) -> Path:
    """第四步：生成SRT文件（保存在任务目录中）"""
    srt_output_dir = task_directory / "04_srt_output"
    srt_output_dir.mkdir(exist_ok=True)
    srt_file_path = srt_output_dir / "subtitles.srt"

    completion_flag = srt_output_dir / "donefile"
    if completion_flag.exists():
        logger_callback("检测到已生成的SRT文件缓存，跳过SRT生成")
        return srt_file_path

    logger_callback("正在生成带有时间轴的SRT字幕文件...")

    # 确定推理设备
    device = "cpu" if FORCE_CPU_INFERENCE else "cuda"

    # 音频文件路径（用于强制对齐）
    audio_path = task_directory / "02_audio" / "audio.wav"
    if not audio_path.exists():
        logger_callback(f"错误：音频文件不存在 {audio_path}")
        raise FileNotFoundError(f"音频文件缺失: {audio_path}")

    SRTGeneratorClass = import_srt_generator_class()
    srt_engine = SRTGeneratorClass(use_cpu=FORCE_CPU_INFERENCE)

    # 检查是否需要补全时间戳
    if not recognition_data.get("timestamp"):
        logger_callback("识别结果缺少时间戳，正在进行强制对齐以生成时间戳...")
        word_timestamps = to_word_timestamp_list(
            str(audio_path), recognition_data, device=device
        )
        if word_timestamps is None:
            logger_callback("错误：无法生成时间戳，SRT文件生成失败")
            raise RuntimeError("时间戳生成失败")

        # 转换为 SRTGenerator 期望的格式（将 'end' 改为 'finish'）
        word_list_for_srt = [
            {"text": w["text"], "start": w["start"], "finish": w["end"]}
            for w in word_timestamps
        ]

        # 直接使用单词级时间戳生成 SRT
        srt_engine.generate_srt_from_word_timestamps(
            word_list_for_srt, output_file_path=srt_file_path
        )
    else:
        # 已有时间戳，使用原始识别结果生成
        srt_engine.generate_srt_from_recognition_result(
            [recognition_data["raw_inference_output"]], output_file_path=srt_file_path
        )

    completion_flag.touch()
    return srt_file_path


def copy_to_final_output(
    raw_info: dict, 
    task_dir: Path, 
    output_format_choice: str, 
    logger_callback=print
) -> list[Path]:
    """第五步：复制到最终输出目录"""
    original_timestamp = int(raw_info.get("timestamp", 0))
    formatted_date = datetime.fromtimestamp(original_timestamp)
    uploader_name = raw_info.get("uploader", "unknown")
    content_title = raw_info.get("title", "video")
    
    final_files = []
    
    if output_format_choice in ["text", "both"]:
        source_txt = task_dir / "04_text_output" / "text_with_punctuation.txt"
        if source_txt.exists():
            safe_txt_filename = "".join(
                c if c.isalnum() or c in " -_." else "_"
                for c in f"{formatted_date:%y%m%d%H%M}-{uploader_name}-{content_title}.txt"
            )
            target_txt_path = FINAL_OUTPUT_DIRECTORY / safe_txt_filename
            shutil.copy2(source_txt, target_txt_path)
            final_files.append(target_txt_path)
            logger_callback(f"文本文件已复制到: {target_txt_path.name}")
    
    if output_format_choice in ["srt", "both"]:
        source_srt = task_dir / "04_srt_output" / "subtitles.srt"
        if source_srt.exists():
            safe_srt_filename = "".join(
                c if c.isalnum() or c in " -_." else "_"
                for c in f"{formatted_date:%y%m%d%H%M}-{uploader_name}-{content_title}.srt"
            )
            target_srt_path = FINAL_OUTPUT_DIRECTORY / safe_srt_filename
            shutil.copy2(source_srt, target_srt_path)
            final_files.append(target_srt_path)
            logger_callback(f"SRT文件已复制到: {target_srt_path.name}")
    
    return final_files


def run_full_transcription_pipeline(
    input_source: str, output_format_choice: str = "both", logger_callback=print
):
    verify_ffmpeg_installation()
    
    task_working_dir = generate_task_unique_directory(input_source)
    
    raw_file_path, resource_info = acquire_input_resource(
        input_source, task_working_dir, logger_callback=logger_callback
    )
    
    standard_audio_path = task_working_dir / "02_audio" / "audio.wav"
    extract_standard_audio_wav(
        raw_file_path, standard_audio_path, logger_callback=logger_callback
    )
    
    json_result_path = task_working_dir / "03_result" / "result.json"
    recognition_output = perform_speech_recognition(
        standard_audio_path, json_result_path, logger_callback=logger_callback
    )
    
    if output_format_choice in ["text", "both"]:
        generate_text_with_punctuation(
            recognition_output, task_working_dir, logger_callback=logger_callback
        )
    
    if output_format_choice in ["srt", "both"]:
        generate_srt_file(
            recognition_output, task_working_dir, logger_callback=logger_callback
        )
    
    final_produced_files = copy_to_final_output(
        resource_info, task_working_dir, output_format_choice, logger_callback=logger_callback
    )
    
    logger_callback("[任务状态] 所有流程均已成功执行完毕")
    return final_produced_files


def process(input_arg: str, logger_func=print):
    """兼容旧版调用的包装函数"""
    return run_full_transcription_pipeline(input_arg, "both", logger_func)


if __name__ == "__main__":
    cli_parser = argparse.ArgumentParser(description="语音转文字处理工具")
    cli_parser.add_argument("input_path", help="本地文件路径或在线视频URL")
    cli_parser.add_argument("--cpu", action="store_true", help="强制使用 CPU 进行推理")
    cli_parser.add_argument(
        "--format", choices=["text", "srt", "both"], default="both", help="设置输出格式"
    )
    cli_args = cli_parser.parse_args()
    FORCE_CPU_INFERENCE = cli_args.cpu
    try:
        results = run_full_transcription_pipeline(cli_args.input_path, cli_args.format)
        for path in results:
            print(f"生成文件: {path}")
    except Exception as error:
        print(f"[致命错误] 流程被中断: {error}")
        sys.exit(1)
