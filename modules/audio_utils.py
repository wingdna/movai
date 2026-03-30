# modules/audio_utils.py
"""
音频工具函数
"""
import os
import numpy as np
from typing import List, Optional, Tuple


def get_audio_duration(audio_path: str) -> Optional[float]:
    """获取音频时长（秒）"""
    try:
        from moviepy import AudioFileClip
        with AudioFileClip(audio_path) as audio:
            return audio.duration
    except:
        try:
            import librosa
            duration = librosa.get_duration(filename=audio_path)
            return duration
        except:
            return None


def get_audio_duration_ms(audio_path: str) -> Optional[int]:
    """获取音频时长（毫秒）"""
    duration = get_audio_duration(audio_path)
    if duration:
        return int(duration * 1000)
    return None


def create_silence(duration_sec: float, output_path: str, sample_rate: int = 22050) -> bool:
    """创建静音文件"""
    try:
        import soundfile as sf
        silence = np.zeros(int(sample_rate * duration_sec))
        sf.write(output_path, silence, sample_rate)
        return True
    except Exception as e:
        print(f"创建静音文件失败: {e}")
        return False


def normalize_audio(input_path: str, output_path: str, target_db: float = -12) -> bool:
    """归一化音频音量"""
    try:
        import soundfile as sf
        import numpy as np
        
        data, sr = sf.read(input_path)
        
        # 计算当前RMS
        rms = np.sqrt(np.mean(data ** 2))
        if rms == 0:
            return False
        
        # 计算增益
        target_rms = 10 ** (target_db / 20)
        gain = target_rms / rms
        
        # 应用增益
        data_normalized = data * gain
        
        # 限制峰值
        max_val = np.max(np.abs(data_normalized))
        if max_val > 0.95:
            data_normalized = data_normalized / max_val * 0.95
        
        sf.write(output_path, data_normalized, sr)
        return True
        
    except Exception as e:
        print(f"归一化失败: {e}")
        return False


def merge_audio_files(audio_paths: List[str], output_path: str, gap: float = 0.25) -> bool:
    """
    合并多个音频文件
    
    Args:
        audio_paths: 音频文件路径列表
        output_path: 输出路径
        gap: 间隔（秒）
    """
    try:
        from moviepy import AudioFileClip, CompositeAudioClip, concatenate_audioclips
        
        clips = []
        for path in audio_paths:
            if not os.path.exists(path):
                continue
            try:
                clip = AudioFileClip(path)
                clips.append(clip)
                if gap > 0:
                    from moviepy.audio.io.AudioFileClip import AudioFileClip as AudioClip
                    # 创建静音间隔
                    silence = AudioClip.make_empty(gap)
                    clips.append(silence)
            except Exception as e:
                print(f"      加载音频失败 {path}: {e}")
        
        if not clips:
            return False
        
        # 移除最后一个间隔
        if gap > 0 and len(clips) > 1:
            clips = clips[:-1]
        
        # 合并
        final_clip = concatenate_audioclips(clips)
        final_clip.write_audiofile(output_path, logger=None)
        
        # 清理
        for clip in clips:
            if hasattr(clip, 'close'):
                clip.close()
        
        return True
        
    except Exception as e:
        print(f"合并音频失败: {e}")
        return False


def mix_audio(background_path: str, voice_path: str, output_path: str, 
              voice_volume: float = 1.0, bg_volume: float = 0.3) -> bool:
    """混合背景音和语音"""
    try:
        from moviepy import AudioFileClip, CompositeAudioClip
        
        voice = AudioFileClip(voice_path).volumex(voice_volume)
        
        if background_path and os.path.exists(background_path):
            bg = AudioFileClip(background_path).volumex(bg_volume)
            # 循环背景音以匹配语音长度
            if bg.duration < voice.duration:
                import math
                repeat = math.ceil(voice.duration / bg.duration)
                bg = bg.loop(repeat)
            bg = bg.subclip(0, voice.duration)
            
            final = CompositeAudioClip([voice, bg])
        else:
            final = voice
        
        final.write_audiofile(output_path, logger=None)
        return True
        
    except Exception as e:
        print(f"混合音频失败: {e}")
        return False


def adjust_speed(audio_path: str, output_path: str, speed: float = 1.0) -> bool:
    """调整音频速度"""
    if speed == 1.0:
        import shutil
        shutil.copy(audio_path, output_path)
        return True
    
    try:
        import soundfile as sf
        import numpy as np
        
        data, sr = sf.read(audio_path)
        
        # 简单的速度调整（重采样）
        new_sr = int(sr * speed)
        
        # 线性插值
        from scipy import signal
        new_len = int(len(data) / speed)
        indices = np.linspace(0, len(data) - 1, new_len)
        data_resampled = signal.resample(data, new_len)
        
        sf.write(output_path, data_resampled, sr)
        return True
        
    except Exception as e:
        print(f"速度调整失败: {e}")
        return False


def get_audio_info(audio_path: str) -> Optional[dict]:
    """获取音频详细信息"""
    try:
        import soundfile as sf
        import numpy as np
        
        data, sr = sf.read(audio_path)
        duration = len(data) / sr
        
        return {
            "duration": duration,
            "duration_ms": int(duration * 1000),
            "sample_rate": sr,
            "channels": data.shape[1] if len(data.shape) > 1 else 1,
            "samples": len(data),
            "rms": float(np.sqrt(np.mean(data ** 2))),
            "peak": float(np.max(np.abs(data)))
        }
    except Exception as e:
        print(f"获取音频信息失败: {e}")
        return None