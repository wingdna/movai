# modules/sfx_downloader.py
"""
音效与背景音乐下载器 - 增强版
- 从 Freesound.org 下载真实音效
- 从多个免费音源获取背景音乐
- 智能匹配故事剧情
"""
import os
import hashlib
import numpy as np
import requests
import json
import random
import time
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

# 尝试加载环境变量
try:
    from dotenv import load_dotenv
    # 加载项目根目录的 .env 文件
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 已加载配置文件: {env_path}")
except ImportError:
    pass


class EmotionType(Enum):
    """情绪类型"""
    TENSION = "tension"      # 紧张
    HORROR = "horror"        # 恐怖
    MYSTERY = "mystery"      # 神秘
    SAD = "sad"              # 悲伤
    ACTION = "action"        # 动作
    CALM = "calm"            # 平静
    EPIC = "epic"            # 史诗
    JOYFUL = "joyful"        # 欢乐
    DESPAIR = "despair"      # 绝望
    FEAR = "fear"            # 恐惧


@dataclass
class SFXInfo:
    """音效信息"""
    name: str
    description: str
    tags: List[str]
    emotions: List[EmotionType]
    duration_range: Tuple[float, float]  # 秒
    source_type: str  # freesound / local / generated


class SFXDownloader:
    """增强版音效与背景音乐下载器"""
    
    # 免费 BGM 源（使用公共领域音乐）
    BGM_SOURCES = {
        "freesound": {
            "url": "https://freesound.org/apiv2/search/text/",
            "license": "Creative Commons 0",
        },
        "incompetech": {
            "url": "https://incompetech.com/music/royalty-free/music.html",
            "license": "Creative Commons Attribution",
        }
    }
    
    # 预设音效库
    SFX_LIBRARY = {
        # 环境音
        "wind": SFXInfo(
            name="风声",
            description="荒凉的风声，适合废土、荒野场景",
            tags=["wind", "ambient", "nature", "desert"],
            emotions=[EmotionType.CALM, EmotionType.DESPAIR, EmotionType.TENSION],
            duration_range=(3.0, 8.0),
            source_type="freesound"
        ),
        "rain": SFXInfo(
            name="雨声",
            description="淅淅沥沥的雨声，适合伤感、悬疑场景",
            tags=["rain", "water", "ambient", "storm"],
            emotions=[EmotionType.SAD, EmotionType.MYSTERY, EmotionType.CALM],
            duration_range=(4.0, 10.0),
            source_type="freesound"
        ),
        "thunder": SFXInfo(
            name="雷声",
            description="远处雷鸣，适合恐怖、紧张场景",
            tags=["thunder", "storm", "dramatic"],
            emotions=[EmotionType.HORROR, EmotionType.TENSION, EmotionType.FEAR],
            duration_range=(1.0, 4.0),
            source_type="freesound"
        ),
        "forest": SFXInfo(
            name="森林",
            description="森林环境音，虫鸣鸟叫",
            tags=["forest", "nature", "birds", "ambient"],
            emotions=[EmotionType.CALM, EmotionType.MYSTERY],
            duration_range=(5.0, 12.0),
            source_type="freesound"
        ),
        "city": SFXInfo(
            name="城市",
            description="城市街道环境音",
            tags=["city", "traffic", "urban", "ambient"],
            emotions=[EmotionType.TENSION, EmotionType.ACTION],
            duration_range=(4.0, 10.0),
            source_type="freesound"
        ),
        
        # 恐怖/惊悚音效
        "creepy_whisper": SFXInfo(
            name="诡异低语",
            description="无法辨认的诡异低语声",
            tags=["whisper", "creepy", "horror", "mysterious"],
            emotions=[EmotionType.HORROR, EmotionType.FEAR, EmotionType.MYSTERY],
            duration_range=(2.0, 5.0),
            source_type="freesound"
        ),
        "alien_laughter": SFXInfo(
            name="异星笑声",
            description="扭曲变形的电子笑声，适合异星生物",
            tags=["laugh", "alien", "distorted", "creepy"],
            emotions=[EmotionType.HORROR, EmotionType.MYSTERY],
            duration_range=(1.5, 3.0),
            source_type="generated"
        ),
        "heartbeat": SFXInfo(
            name="心跳声",
            description="紧张加速的心跳声",
            tags=["heartbeat", "tension", "fear"],
            emotions=[EmotionType.TENSION, EmotionType.FEAR, EmotionType.DESPAIR],
            duration_range=(2.0, 5.0),
            source_type="generated"
        ),
        "static_noise": SFXInfo(
            name="静电噪音",
            description="无线电静电干扰声",
            tags=["static", "radio", "interference", "glitch"],
            emotions=[EmotionType.TENSION, EmotionType.MYSTERY],
            duration_range=(2.0, 6.0),
            source_type="generated"
        ),
        
        # 动作/紧张音效
        "alarm": SFXInfo(
            name="警报声",
            description="紧急警报声",
            tags=["alarm", "alert", "warning", "emergency"],
            emotions=[EmotionType.TENSION, EmotionType.ACTION, EmotionType.FEAR],
            duration_range=(1.0, 3.0),
            source_type="generated"
        ),
        "footsteps": SFXInfo(
            name="脚步声",
            description="在金属/混凝土上的脚步声",
            tags=["footsteps", "walk", "run", "tense"],
            emotions=[EmotionType.TENSION, EmotionType.ACTION],
            duration_range=(1.0, 3.0),
            source_type="generated"
        ),
        "door_creak": SFXInfo(
            name="门吱呀声",
            description="老旧金属门打开的声音",
            tags=["door", "creak", "suspense"],
            emotions=[EmotionType.TENSION, EmotionType.MYSTERY],
            duration_range=(1.0, 2.5),
            source_type="generated"
        ),
        
        # 科幻/未来音效
        "computer_hum": SFXInfo(
            name="电脑嗡鸣",
            description="服务器/电脑设备的嗡鸣声",
            tags=["computer", "hum", "tech", "scifi"],
            emotions=[EmotionType.CALM, EmotionType.TENSION],
            duration_range=(3.0, 8.0),
            source_type="generated"
        ),
        "data_transfer": SFXInfo(
            name="数据传输",
            description="科幻风格的数据传输音效",
            tags=["data", "tech", "scifi", "digital"],
            emotions=[EmotionType.MYSTERY, EmotionType.TENSION],
            duration_range=(1.5, 3.0),
            source_type="generated"
        ),
    }
    
    # 预设 BGM 库（情绪驱动）
    BGM_LIBRARY = {
        EmotionType.TENSION: {
            "name": "紧张氛围",
            "description": "悬疑、紧张场景的背景音乐",
            "tempo": 90,
            "key": "Dm",
            "instruments": ["strings", "synth pads", "pizzicato"],
            "mood": ["tense", "suspenseful", "uneasy"]
        },
        EmotionType.HORROR: {
            "name": "恐怖氛围",
            "description": "惊悚、恐怖场景的背景音乐",
            "tempo": 60,
            "key": "Cm",
            "instruments": ["strings", "low brass", "drone"],
            "mood": ["dark", "ominous", "scary"]
        },
        EmotionType.MYSTERY: {
            "name": "神秘氛围",
            "description": "神秘、未知场景的背景音乐",
            "tempo": 70,
            "key": "Em",
            "instruments": ["piano", "harp", "ethereal pads"],
            "mood": ["mysterious", "curious", "ethereal"]
        },
        EmotionType.SAD: {
            "name": "悲伤氛围",
            "description": "悲伤、绝望场景的背景音乐",
            "tempo": 65,
            "key": "Am",
            "instruments": ["piano", "cello", "strings"],
            "mood": ["sad", "melancholic", "mournful"]
        },
        EmotionType.ACTION: {
            "name": "动作氛围",
            "description": "追逐、战斗场景的背景音乐",
            "tempo": 120,
            "key": "Fm",
            "instruments": ["drums", "brass", "electric guitar"],
            "mood": ["intense", "energetic", "dramatic"]
        },
        EmotionType.CALM: {
            "name": "平静氛围",
            "description": "平静、思考场景的背景音乐",
            "tempo": 80,
            "key": "C",
            "instruments": ["piano", "acoustic guitar", "ambient pads"],
            "mood": ["calm", "peaceful", "contemplative"]
        },
        EmotionType.EPIC: {
            "name": "史诗氛围",
            "description": "宏大、壮丽场景的背景音乐",
            "tempo": 100,
            "key": "D",
            "instruments": ["orchestra", "choir", "brass"],
            "mood": ["epic", "majestic", "triumphant"]
        },
        EmotionType.JOYFUL: {
            "name": "欢乐氛围",
            "description": "欢乐、温馨场景的背景音乐",
            "tempo": 110,
            "key": "G",
            "instruments": ["piano", "strings", "flute"],
            "mood": ["joyful", "hopeful", "bright"]
        },
        EmotionType.DESPAIR: {
            "name": "绝望氛围",
            "description": "绝望、无力场景的背景音乐",
            "tempo": 50,
            "key": "Em",
            "instruments": ["cello", "low strings", "ambient"],
            "mood": ["hopeless", "dark", "heavy"]
        },
        EmotionType.FEAR: {
            "name": "恐惧氛围",
            "description": "恐惧、惊慌场景的背景音乐",
            "tempo": 85,
            "key": "C#m",
            "instruments": ["high strings", "percussion", "atonal"],
            "mood": ["fearful", "panicked", "anxious"]
        },
    }
    
    def __init__(self, api_key: str = None, cache_dir: str = "./cache/sfx"):
        """
        初始化音效下载器
        
        Args:
            api_key: Freesound API Key（可选，不设置则从环境变量读取）
            cache_dir: 缓存目录
        """
        # 优先使用传入的 api_key，否则从环境变量读取
        if api_key is None:
            self.api_key = os.environ.get("FREESOUND_API_KEY") or os.environ.get("FREESOUND_TOKEN")
        else:
            self.api_key = api_key
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # BGM 缓存目录
        self.bgm_cache_dir = self.cache_dir / "bgm"
        self.bgm_cache_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🎵 音效下载器初始化完成")
        print(f"   📁 缓存目录: {self.cache_dir}")
        print(f"   🌐 Freesound API: {'✅ 已配置' if self.api_key else '❌ 未配置（将使用本地生成）'}")
        if self.api_key:
            print(f"   🔑 API Key: {self.api_key[:8]}...{self.api_key[-4:]}")
        print(f"   🎼 预设音效: {len(self.SFX_LIBRARY)} 种")
        print(f"   🎵 预设BGM: {len(self.BGM_LIBRARY)} 种情绪")
    
    def search_freesound(self, query: str, max_duration: int = 10, 
                          min_duration: int = 1, page_size: int = 5) -> List[Dict]:
        """
        搜索 Freesound 音效
        
        Args:
            query: 搜索关键词
            max_duration: 最大时长（秒）
            min_duration: 最小时长（秒）
            page_size: 返回结果数量
        
        Returns:
            音效信息列表，每个包含 url, name, duration
        """
        if not self.api_key:
            return []
        
        try:
            url = "https://freesound.org/apiv2/search/text/"
            params = {
                "query": query,
                "fields": "id,name,previews,duration,tags",
                "page_size": page_size,
                "token": self.api_key  # Freesound 使用 token 参数
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"      ⚠️ Freesound API 返回错误: {response.status_code}")
                return []
            
            data = response.json()
            results = []
            
            for result in data.get("results", []):
                duration = result.get("duration", 0)
                if min_duration <= duration <= max_duration:
                    previews = result.get("previews", {})
                    preview_url = previews.get("preview-hq-mp3")
                    if preview_url:
                        results.append({
                            "id": result.get("id"),
                            "name": result.get("name"),
                            "duration": duration,
                            "url": preview_url,
                            "tags": result.get("tags", [])
                        })
            
            return results
            
        except Exception as e:
            print(f"      ⚠️ Freesound 搜索失败: {e}")
            return []
    
    def get_sfx_for_emotion(self, emotion: str, tags: List[str] = None) -> Optional[SFXInfo]:
        """
        根据情绪获取合适的音效
        
        Args:
            emotion: 情绪类型字符串
            tags: 额外的标签匹配
        
        Returns:
            音效信息
        """
        try:
            emotion_enum = EmotionType(emotion.lower())
        except ValueError:
            emotion_enum = EmotionType.TENSION
        
        # 匹配音效
        candidates = []
        for sfx in self.SFX_LIBRARY.values():
            if emotion_enum in sfx.emotions:
                weight = 1
                if tags:
                    for tag in tags:
                        if tag.lower() in sfx.tags:
                            weight += 2
                candidates.append((weight, sfx))
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    
    def get_bgm_for_emotion(self, emotion: str) -> Dict:
        """
        根据情绪获取 BGM 配置
        
        Args:
            emotion: 情绪类型字符串
        
        Returns:
            BGM 配置字典
        """
        try:
            emotion_enum = EmotionType(emotion.lower())
        except ValueError:
            emotion_enum = EmotionType.TENSION
        
        return self.BGM_LIBRARY.get(emotion_enum, self.BGM_LIBRARY[EmotionType.CALM])
    
    def download_sfx(self, query: str, output_path: str, 
                      duration: int = 3, emotion: str = "tension") -> bool:
        """
        下载或生成音效
        
        Args:
            query: 搜索关键词或 SFX 名称
            output_path: 输出路径
            duration: 期望时长（秒）
            emotion: 情绪类型（用于匹配）
        
        Returns:
            是否成功
        """
        try:
            import soundfile as sf
            
            # 检查缓存
            cache_key = hashlib.md5(f"{query}_{duration}_{emotion}".encode()).hexdigest()
            cache_path = self.cache_dir / f"{cache_key}.mp3"
            
            if cache_path.exists():
                import shutil
                shutil.copy(cache_path, output_path)
                print(f"      📦 使用缓存音效")
                return True
            
            # 1. 尝试从 Freesound 下载
            if self.api_key:
                results = self.search_freesound(query, max_duration=duration+2, min_duration=1)
                if results:
                    best = results[0]
                    try:
                        response = requests.get(best["url"], timeout=15)
                        if response.status_code == 200:
                            with open(cache_path, 'wb') as f:
                                f.write(response.content)
                            import shutil
                            shutil.copy(cache_path, output_path)
                            print(f"      🌐 从 Freesound 下载: {best['name']} ({best['duration']:.1f}秒)")
                            return True
                    except Exception as e:
                        print(f"      ⚠️ 下载失败: {e}")
            
            # 2. 根据情绪生成音效
            sfx_info = self.get_sfx_for_emotion(emotion, tags=[query])
            if sfx_info:
                return self._generate_sfx_by_type(sfx_info.name, output_path, duration, cache_path)
            
            # 3. 回退到通用生成
            return self._generate_generic_sfx(query, output_path, duration, cache_path)
            
        except Exception as e:
            print(f"      ❌ 音效下载失败: {e}")
            return False
    
    def _generate_sfx_by_type(self, sfx_type: str, output_path: str, 
                               duration: int, cache_path: Path) -> bool:
        """根据类型生成特定音效"""
        try:
            import soundfile as sf
            
            sr = 22050
            samples = int(sr * duration)
            t = np.linspace(0, duration, samples)
            
            if "wind" in sfx_type.lower():
                noise = np.random.randn(samples) * 0.15
                envelope = 0.3 + 0.2 * np.sin(2 * np.pi * 0.5 * t)
                signal = noise * envelope
                
            elif "rain" in sfx_type.lower():
                noise = np.random.randn(samples) * 0.12
                from scipy.signal import butter, filtfilt
                nyquist = sr / 2
                b, a = butter(4, 3000 / nyquist, btype='high')
                signal = filtfilt(b, a, noise)
                
            elif "alien_laughter" in sfx_type.lower():
                base_freq = 440 * (1 + 0.3 * np.sin(2 * np.pi * 3 * t))
                signal = 0.4 * np.sin(2 * np.pi * base_freq * t)
                signal += 0.2 * np.sin(2 * np.pi * base_freq * 2 * t)
                envelope = np.exp(-t * 3) * (0.5 + 0.5 * np.sin(2 * np.pi * 8 * t))
                signal = signal * envelope
                
            elif "heartbeat" in sfx_type.lower():
                signal = np.zeros(samples)
                beat_interval = int(sr * 0.6)
                for i in range(0, samples, beat_interval):
                    beat_len = min(sr//15, samples - i)
                    if beat_len > 0:
                        beat = np.exp(-np.linspace(0, 0.08, beat_len) * 80)
                        signal[i:i+beat_len] += 0.5 * beat
                        
            elif "static_noise" in sfx_type.lower():
                noise = np.random.randn(samples) * 0.2
                from scipy.signal import butter, filtfilt
                nyquist = sr / 2
                b, a = butter(4, 4000 / nyquist, btype='high')
                signal = filtfilt(b, a, noise)
                envelope = 0.3 + 0.2 * np.random.randn(samples) * 0.5
                signal = signal * envelope
                
            elif "alarm" in sfx_type.lower():
                signal = 0.5 * np.sin(2 * np.pi * 880 * t)
                envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 4 * t)
                signal = signal * envelope
                
            elif "footsteps" in sfx_type.lower():
                signal = np.zeros(samples)
                step_interval = int(sr * 0.5)
                for i in range(0, samples, step_interval):
                    step_len = min(sr//10, samples - i)
                    if step_len > 0:
                        step = np.exp(-np.linspace(0, 0.1, step_len) * 50)
                        signal[i:i+step_len] += 0.3 * step
                        
            elif "computer_hum" in sfx_type.lower():
                signal = 0.2 * np.sin(2 * np.pi * 60 * t)
                signal += 0.1 * np.sin(2 * np.pi * 120 * t)
                noise = np.random.randn(samples) * 0.05
                signal += noise
                
            elif "data_transfer" in sfx_type.lower():
                signal = np.zeros(samples)
                data_rate = 8
                for i in range(0, samples, int(sr / data_rate)):
                    pulse_len = min(sr//50, samples - i)
                    if pulse_len > 0:
                        pulse = np.random.randn(pulse_len) * 0.3
                        signal[i:i+pulse_len] += pulse
                        
            else:
                noise = np.random.randn(samples) * 0.08
                signal = noise * np.exp(-t / duration)
            
            if np.max(np.abs(signal)) > 0:
                signal = signal / np.max(np.abs(signal)) * 0.5
            
            sf.write(cache_path, signal, sr)
            import shutil
            shutil.copy(cache_path, output_path)
            return True
            
        except Exception as e:
            print(f"      ⚠️ 音效生成失败: {e}")
            return False
    
    def _generate_generic_sfx(self, query: str, output_path: str, 
                                duration: int, cache_path: Path) -> bool:
        """生成通用音效"""
        try:
            import soundfile as sf
            
            sr = 22050
            samples = int(sr * duration)
            t = np.linspace(0, duration, samples)
            
            if "wind" in query.lower():
                noise = np.random.randn(samples) * 0.15
                envelope = 0.3 + 0.2 * np.sin(2 * np.pi * 0.5 * t)
                signal = noise * envelope
            elif "alarm" in query.lower():
                signal = 0.5 * np.sin(2 * np.pi * 880 * t)
                envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 4 * t)
                signal = signal * envelope
            elif "foot" in query.lower() or "step" in query.lower():
                signal = np.zeros(samples)
                step_interval = int(sr * 0.5)
                for i in range(0, samples, step_interval):
                    step_len = min(sr//10, samples - i)
                    if step_len > 0:
                        step = np.exp(-np.linspace(0, 0.1, step_len) * 50)
                        signal[i:i+step_len] += 0.3 * step
            else:
                noise = np.random.randn(samples) * 0.08
                signal = noise * np.exp(-t / duration)
            
            if np.max(np.abs(signal)) > 0:
                signal = signal / np.max(np.abs(signal)) * 0.5
            
            sf.write(cache_path, signal, sr)
            import shutil
            shutil.copy(cache_path, output_path)
            return True
            
        except Exception as e:
            print(f"      ⚠️ 通用音效生成失败: {e}")
            return False
    
    def generate_bgm(self, emotion: str, duration: float, output_path: str) -> bool:
        """
        根据情绪生成背景音乐
        
        Args:
            emotion: 情绪类型
            duration: 时长（秒）
            output_path: 输出路径
        
        Returns:
            是否成功
        """
        try:
            import soundfile as sf
            
            bgm_config = self.get_bgm_for_emotion(emotion)
            
            # 检查缓存
            cache_key = hashlib.md5(f"bgm_{emotion}_{duration}".encode()).hexdigest()
            cache_path = self.bgm_cache_dir / f"{cache_key}.mp3"
            
            if cache_path.exists():
                import shutil
                shutil.copy(cache_path, output_path)
                print(f"      📦 使用缓存 BGM: {bgm_config['name']}")
                return True
            
            sr = 44100
            samples = int(sr * duration)
            t = np.linspace(0, duration, samples)
            
            # 根据情绪生成音乐
            if emotion in ["tension", "紧张"]:
                base_freq = 220
                melody = np.sin(2 * np.pi * base_freq * t) * 0.3
                melody += np.sin(2 * np.pi * (base_freq * 1.5) * t) * 0.2
                pulse = np.zeros(samples)
                pulse_interval = int(sr * 0.8)
                for i in range(0, samples, pulse_interval):
                    pulse_len = min(sr//10, samples - i)
                    pulse[i:i+pulse_len] = np.exp(-np.linspace(0, 0.1, pulse_len) * 30) * 0.4
                signal = melody + pulse
                
            elif emotion in ["horror", "恐怖"]:
                sub = 0.3 * np.sin(2 * np.pi * 30 * t) * np.exp(-t / 3)
                scratch = np.random.randn(samples) * 0.1
                scratch = scratch * np.sin(2 * np.pi * 2000 * t) * 0.3
                signal = sub + scratch
                
            elif emotion in ["mystery", "神秘"]:
                signal = np.zeros(samples)
                bell_interval = int(sr * 3)
                for i in range(0, samples, bell_interval):
                    bell_len = min(sr//2, samples - i)
                    t_bell = np.linspace(0, 1, bell_len)
                    bell = np.sin(2 * np.pi * 440 * t_bell) * np.exp(-t_bell * 8)
                    bell += 0.5 * np.sin(2 * np.pi * 880 * t_bell) * np.exp(-t_bell * 12)
                    signal[i:i+bell_len] += bell * 0.3
                noise = np.random.randn(samples) * 0.05
                signal += noise
                
            elif emotion in ["sad", "悲伤"]:
                base_freq = 165
                signal = 0.4 * np.sin(2 * np.pi * base_freq * t) * np.exp(-t / 5)
                signal += 0.2 * np.sin(2 * np.pi * (base_freq * 1.2) * t) * np.exp(-t / 4)
                envelope = 0.3 + 0.2 * np.sin(2 * np.pi * 0.1 * t)
                signal = signal * envelope
                
            elif emotion in ["action", "动作"]:
                signal = np.zeros(samples)
                beat_interval = int(sr * 0.25)
                for i in range(0, samples, beat_interval):
                    beat_len = min(sr//20, samples - i)
                    beat = np.random.randn(beat_len) * 0.4
                    signal[i:i+beat_len] += beat
                bass = 0.3 * np.sin(2 * np.pi * 60 * t)
                signal += bass
                
            elif emotion in ["epic", "史诗"]:
                signal = 0.5 * np.sin(2 * np.pi * 110 * t) * np.exp(-t / 10)
                signal += 0.3 * np.sin(2 * np.pi * 220 * t) * np.exp(-t / 8)
                drum_interval = int(sr * 1)
                for i in range(0, samples, drum_interval):
                    drum_len = min(sr//10, samples - i)
                    drum = np.exp(-np.linspace(0, 0.2, drum_len) * 20)
                    signal[i:i+drum_len] += 0.2 * drum
                    
            elif emotion in ["joyful", "欢乐"]:
                signal = 0.3 * np.sin(2 * np.pi * 440 * t) * (1 + 0.2 * np.sin(2 * np.pi * 2 * t))
                signal += 0.2 * np.sin(2 * np.pi * 880 * t) * (1 + 0.1 * np.sin(2 * np.pi * 4 * t))
                envelope = 0.4 + 0.2 * np.sin(2 * np.pi * 0.5 * t)
                signal = signal * envelope
                
            else:  # calm / 平静
                signal = 0.2 * np.sin(2 * np.pi * 110 * t) * np.exp(-t / 8)
                signal += 0.1 * np.sin(2 * np.pi * 220 * t) * np.exp(-t / 6)
                noise = np.random.randn(samples) * 0.02
                signal += noise
            
            if np.max(np.abs(signal)) > 0:
                signal = signal / np.max(np.abs(signal)) * 0.3
            
            sf.write(cache_path, signal, sr)
            import shutil
            shutil.copy(cache_path, output_path)
            print(f"      🎵 生成 BGM: {bgm_config['name']} ({duration:.1f}秒)")
            return True
            
        except Exception as e:
            print(f"      ⚠️ BGM 生成失败: {e}")
            return False
    
    def download_bgm(self, emotion: str, duration: float, output_path: str) -> bool:
        """
        下载或生成背景音乐（对外接口）
        
        Args:
            emotion: 情绪类型
            duration: 时长（秒）
            output_path: 输出路径
        
        Returns:
            是否成功
        """
        return self.generate_bgm(emotion, duration, output_path)
    
    def clear_cache(self):
        """清理缓存"""
        import shutil
        for cache_dir in [self.cache_dir, self.bgm_cache_dir]:
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)
        print("🗑️ 音效缓存已清理")


# 便捷函数
def get_sfx(query: str, output_path: str, duration: int = 3, emotion: str = "tension") -> bool:
    """获取音效"""
    downloader = SFXDownloader()
    return downloader.download_sfx(query, output_path, duration, emotion)


def get_bgm(emotion: str, duration: float, output_path: str) -> bool:
    """获取背景音乐"""
    downloader = SFXDownloader()
    return downloader.download_bgm(emotion, duration, output_path)


# 测试
if __name__ == "__main__":
    print("测试音效下载器...")
    downloader = SFXDownloader()
    
    print(f"API Key 状态: {'已配置' if downloader.api_key else '未配置'}")
    if downloader.api_key:
        print(f"API Key: {downloader.api_key[:8]}...{downloader.api_key[-4:]}")
    
    # 测试音效
    test_sfx = "wind"
    print(f"\n测试音效: {test_sfx}")
    downloader.download_sfx(test_sfx, "test_sfx.mp3", duration=3, emotion="calm")
    
    # 测试 BGM
    print(f"\n测试 BGM: 紧张情绪")
    downloader.download_bgm("tension", 10, "test_bgm.mp3")
    
    print("\n✅ 测试完成")