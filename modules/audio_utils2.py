# modules/audio_utils.py
"""
音频工具函数
"""
import os
import numpy as np
from typing import List, Optional

def get_audio_duration(audio_path: str) -> Optional[float]:
    """获取音频时长（秒）"""
    if not os.path.exists(audio_path):
        return None
    try:
        from moviepy.editor import AudioFileClip
        with AudioFileClip(audio_path) as audio:
            return audio.duration
    except Exception:
        try:
            import librosa
            duration = librosa.get_duration(filename=audio_path)
            return duration
        except Exception:
            return None

def merge_audio_files(audio_paths: List[str], output_path: str, gap: float = 0.25) -> bool:
    """合并多个音频文件（带间隔）"""
    try:
        from moviepy.editor import AudioFileClip, concatenate_audioclips
        clips =[]
        for path in audio_paths:
            if os.path.exists(path):
                clips.append(AudioFileClip(path))
                
        if not clips:
            return False
            
        # 这里的 gap 目前仅在计算时长时累加，实际物理音频拼接可以留给 Module 6 进行多轨混音
        final_clip = concatenate_audioclips(clips)
        final_clip.write_audiofile(output_path, logger=None)
        
        for clip in clips:
            clip.close()
        return True
    except Exception as e:
        print(f"合并音频失败: {e}")
        return False