# modules/tts_cleaner.py
"""
TTS 文本暴力清洗器 - 彻底移除所有 SSML/XML 痕迹
"""
import re
import html


class TTSCleaner:
    """TTS 文本暴力清洗器"""
    
    # 需要移除的 XML/SSML 模式
    SSML_PATTERNS = [
        # XML 声明头
        r'<\?xml[^>]+\?>',
        # DOCTYPE 声明
        r'<!DOCTYPE[^>]+>',
        # 所有尖括号标签（包括闭合标签）
        r'<[^>]+>',
        # 自闭合标签
        r'<[^>]+/>',
    ]
    
    # 需要移除的 SSML 属性残留
    SSML_ATTRIBUTES = [
        r'xmlns[^=]*="[^"]*"',
        r'xml:lang="[^"]*"',
        r'version="[^"]*"',
        r'style="[^"]*"',
        r'styledegree="[^"]*"',
        r'rate="[^"]*"',
        r'pitch="[^"]*"',
        r'volume="[^"]*"',
        r'voice\s*=\s*"[^"]*"',
    ]
    
    # 需要移除的占位符
    PLACEHOLDERS = [
        r'\[.*?\]',           # 方括号内容
        r'\(.*?\)',           # 圆括号内容
        r'\（.*?\）',         # 中文圆括号
        r'【.*?】',           # 中文方括号
        r'\{.*?\}',           # 花括号内容
        r'纯中文旁白',
        r'纯中文对白',
        r'纯英文描述',
        r'场景名称',
        r'旁白：',
        r'对白：',
        r'对话：',
        r'叙述：',
        r'[◆◇■□▶△▽▲▼●○★☆]+',
    ]
    
    # 需要移除的标签前缀
    TAG_PREFIXES = [
        'SFX:', 'VFX:', 'AMBIENT:', 'VISUAL:',
        'CAMERA:', 'CUT:', 'TRANSITION:', 'FADE:',
        'ZOOM:', 'PAN:', 'TILT:', 'MOVE:',
        'SPEAK:', 'VOICE:', 'PROSODY:', 'MSTTS:',
    ]
    
    def __init__(self):
        # 编译正则表达式
        self.ssml_regex = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.SSML_PATTERNS]
        self.placeholder_regex = [re.compile(p, re.IGNORECASE) for p in self.PLACEHOLDERS]
        self.attr_regex = [re.compile(p, re.IGNORECASE) for p in self.SSML_ATTRIBUTES]
    
    def clean(self, text: str, context: str = "narration") -> str:
        """
        暴力清洗文本 - 确保 TTS 只得到纯文本
        
        Args:
            text: 原始文本
            context: 上下文类型 (narration/dialogue)
        
        Returns:
            清洗后的纯文本
        """
        if not text:
            return ""
        
        original = text
        cleaned = text
        
        # 1. 移除 XML/SSML 标签（最优先）
        for regex in self.ssml_regex:
            cleaned = regex.sub('', cleaned)
        
        # 2. 移除 SSML 属性残留
        for regex in self.attr_regex:
            cleaned = regex.sub('', cleaned)
        
        # 3. 移除占位符
        for regex in self.placeholder_regex:
            cleaned = regex.sub('', cleaned)
        
        # 4. 移除标签前缀
        for prefix in self.TAG_PREFIXES:
            cleaned = cleaned.replace(prefix, '')
        
        # 5. 移除各种括号残留
        cleaned = re.sub(r'[<>{}]', '', cleaned)
        
        # 6. 清理多余空白
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()
        
        # 7. 移除行首的标点
        cleaned = re.sub(r'^[，,。、；：\s]+', '', cleaned)
        
        # 8. 确保有内容
        if len(cleaned) < 2:
            if context == "narration":
                cleaned = "画面继续。"
            else:
                cleaned = "嗯。"
        
        # 调试输出
        if original != cleaned and len(original) > 20:
            print(f"      🔧 清洗: {original[:50]}... → {cleaned[:50]}...")
        
        return cleaned
    
    def is_ssml_free(self, text: str) -> bool:
        """检查文本是否已无 SSML 痕迹"""
        # 检查是否还有尖括号
        if '<' in text or '>' in text:
            return False
        # 检查是否还有 XML 关键词
        if re.search(r'\b(xml|speak|voice|prosody|mstts)\b', text, re.IGNORECASE):
            return False
        return True


# 全局实例
tts_cleaner = TTSCleaner()


def clean_for_tts(text: str, context: str = "narration") -> str:
    """快捷清洗函数"""
    return tts_cleaner.clean(text, context)