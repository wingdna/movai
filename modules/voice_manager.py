# modules/voice_manager.py
"""
音色管理器 - 管理和分配 TTS 音色
"""
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class VoiceInfo:
    """音色信息"""
    name: str
    display_name: str
    gender: str
    style: str
    region: str
    description: str
    recommended_for: List[str]  # 适合的角色类型


class VoiceManager:
    """音色管理器"""
    
    def __init__(self):
        self.voices = self._init_voices()
    
    def _init_voices(self) -> List[VoiceInfo]:
        """初始化音色库"""
        return [
            # 女声
            VoiceInfo(
                name="zh-CN-XiaoxiaoNeural",
                display_name="晓晓",
                gender="female",
                style="affectionate",
                region="mainland",
                description="温柔自然，适合旁白、抒情",
                recommended_for=["旁白", "叙述者", "温柔女性", "母亲"]
            ),
            VoiceInfo(
                name="zh-CN-XiaoyiNeural",
                display_name="小艺",
                gender="female",
                style="cheerful",
                region="mainland",
                description="活泼开朗，适合年轻女性",
                recommended_for=["年轻女性", "活泼角色", "少女"]
            ),
            VoiceInfo(
                name="zh-CN-XiaohanNeural",
                display_name="小涵",
                gender="female",
                style="calm",
                region="mainland",
                description="温暖亲切，适合知性女性",
                recommended_for=["知性女性", "医生", "老师"]
            ),
            VoiceInfo(
                name="zh-CN-XiaomengNeural",
                display_name="小萌",
                gender="female",
                style="cheerful",
                region="mainland",
                description="可爱活泼，适合少女角色",
                recommended_for=["少女", "可爱角色", "妹妹"]
            ),
            VoiceInfo(
                name="zh-CN-XiaoqiuNeural",
                display_name="小秋",
                gender="female",
                style="sad",
                region="mainland",
                description="温柔略带忧伤",
                recommended_for=["悲伤角色", "忧郁女性", "回忆"]
            ),
            
            # 男声
            VoiceInfo(
                name="zh-CN-YunjianNeural",
                display_name="云健",
                gender="male",
                style="angry",
                region="mainland",
                description="沉稳有力，适合戏剧独白",
                recommended_for=["威严男性", "领导者", "反派"]
            ),
            VoiceInfo(
                name="zh-CN-YunxiNeural",
                display_name="云希",
                gender="male",
                style="cheerful",
                region="mainland",
                description="年轻活力，适合青年男性",
                recommended_for=["青年男性", "阳光角色", "朋友"]
            ),
            VoiceInfo(
                name="zh-CN-YunyangNeural",
                display_name="云扬",
                gender="male",
                style="calm",
                region="mainland",
                description="专业沉稳，适合新闻播报",
                recommended_for=["成熟男性", "专家", "旁白"]
            ),
            VoiceInfo(
                name="zh-CN-YunyeNeural",
                display_name="云野",
                gender="male",
                style="calm",
                region="mainland",
                description="温和自然",
                recommended_for=["温和男性", "父亲", "导师"]
            ),
            
            # 特殊角色
            VoiceInfo(
                name="zh-CN-XiaochenNeural",
                display_name="小辰",
                gender="male",
                style="cheerful",
                region="mainland",
                description="青春活力",
                recommended_for=["少年", "学生", "探险者"]
            ),
        ]
    
    def get_all_voices(self) -> List[VoiceInfo]:
        """获取所有音色"""
        return self.voices
    
    def get_voice_by_name(self, name: str) -> Optional[VoiceInfo]:
        """根据名称获取音色"""
        for voice in self.voices:
            if voice.name == name:
                return voice
        return None
    
    def select_voice_by_profile(self, character_name: str, profile: str) -> str:
        """根据角色特征选择音色"""
        profile_lower = profile.lower()
        
        # 根据关键词匹配
        if "女" in profile_lower or "female" in profile_lower:
            if "年轻" in profile_lower or "young" in profile_lower:
                return "zh-CN-XiaoyiNeural"
            elif "温柔" in profile_lower or "gentle" in profile_lower:
                return "zh-CN-XiaoxiaoNeural"
            elif "悲伤" in profile_lower or "sad" in profile_lower:
                return "zh-CN-XiaoqiuNeural"
            else:
                return "zh-CN-XiaoxiaoNeural"
        else:
            if "年轻" in profile_lower or "young" in profile_lower:
                return "zh-CN-YunxiNeural"
            elif "威严" in profile_lower or "威严" in profile_lower:
                return "zh-CN-YunjianNeural"
            else:
                return "zh-CN-YunyangNeural"
        
        # 默认
        return "zh-CN-XiaoxiaoNeural"
    
    def select_voice_by_emotion(self, emotion: str) -> str:
        """根据情感选择音色"""
        mapping = {
            "joyful": "zh-CN-XiaoyiNeural",
            "cheerful": "zh-CN-XiaoyiNeural",
            "sad": "zh-CN-XiaoqiuNeural",
            "sorrow": "zh-CN-XiaoqiuNeural",
            "angry": "zh-CN-YunjianNeural",
            "dramatic": "zh-CN-YunjianNeural",
            "calm": "zh-CN-YunyangNeural",
            "tender": "zh-CN-XiaoxiaoNeural",
            "affectionate": "zh-CN-XiaoxiaoNeural",
        }
        return mapping.get(emotion.lower(), "zh-CN-XiaoxiaoNeural")


def get_voice_for_character(character_name: str, character_desc: str = "") -> str:
    """为角色获取推荐音色"""
    manager = VoiceManager()
    return manager.select_voice_by_profile(character_name, character_desc)