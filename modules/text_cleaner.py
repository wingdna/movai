# modules/text_cleaner.py (完整修复版)

import re
import html
from typing import Dict, List, Optional


class TextCleaner:
    """文本清洗器 - 彻底清理 TTS 文本"""
    
    def __init__(self):
        # 需要移除的占位符模式
        self.placeholder_patterns = [
            r'纯中文旁白',
            r'纯中文对白',
            r'纯英文描述',
            r'场景名称',
            r'旁白：',
            r'对白：',
            r'对话：',
            r'叙述：',
        ]
        
        # 需要清理的标签前缀
        self.tag_prefixes = [
            'SFX:', 'VFX:', 'AMBIENT:', 'VISUAL:',
            'CAMERA:', 'CUT:', 'TRANSITION:', 'FADE:',
            'ZOOM:', 'PAN:', 'TILT:', 'MOVE:'
        ]
        
        # 需要移除的无效文本模式
        self.invalid_patterns = [
            r'^[A-Z_]+:\s*$',           # 只有标签的行
            r'^[\s]*$',                  # 空行
            r'^[0-9]+[\.\)]\s*$',        # 只有数字的行
            r'^[◆◇■□▶△▽▲▼●○★☆]+$',    # 只有符号的行
        ]
    
    def clean_for_tts(self, text: str, context: str = "narration") -> str:
        """
        清洗文本用于 TTS 生成
        
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
        
        # 1. 移除所有 XML/HTML 标签
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        # 2. 移除占位符
        for pattern in self.placeholder_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # 3. 移除标签前缀
        for prefix in self.tag_prefixes:
            cleaned = cleaned.replace(prefix, '')
        
        # 4. 移除方括号、花括号等内容
        cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
        cleaned = re.sub(r'\{[^\}]*\}', '', cleaned)
        cleaned = re.sub(r'【[^】]*】', '', cleaned)
        cleaned = re.sub(r'（[^）]*）', '', cleaned)
        
        # 5. 移除无效行
        lines = cleaned.split('\n')
        valid_lines = []
        for line in lines:
            is_invalid = False
            for pattern in self.invalid_patterns:
                if re.match(pattern, line.strip()):
                    is_invalid = True
                    break
            if not is_invalid:
                line = line.strip()
                if len(line) > 0:
                    valid_lines.append(line)
        
        cleaned = ' '.join(valid_lines)
        
        # 6. 清理多余空格和标点
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'[，,]+$', '', cleaned)
        cleaned = re.sub(r'^[，,]+', '', cleaned)
        cleaned = re.sub(r'[！？。]{2,}', '。', cleaned)
        
        # 7. 移除英文标点后保留中文
        cleaned = re.sub(r'[a-zA-Z]+', '', cleaned)
        
        # 8. 转义 XML 特殊字符
        cleaned = html.escape(cleaned)
        
        # 9. 确保有内容
        if len(cleaned) < 3:
            if context == "narration":
                cleaned = "画面继续。"
            else:
                cleaned = "嗯。"
        
        # 调试输出
        if original != cleaned and len(original) > 10:
            print(f"      🔧 清洗: {original[:40]}... → {cleaned[:40]}...")
        
        return cleaned.strip()
    
    def extract_dialogues(self, scene: Dict) -> List[Dict]:
        """从场景中提取并清洗对话"""
        dialogues = scene.get("dialogues", [])
        cleaned = []
        
        for dia in dialogues:
            line = dia.get("line", "")
            character = dia.get("character", "未知")
            
            if line:
                cleaned_line = self.clean_for_tts(line, "dialogue")
                if cleaned_line and len(cleaned_line) > 1:
                    cleaned.append({
                        "character": character,
                        "original": line,
                        "cleaned": cleaned_line
                    })
        
        return cleaned
    
    def extract_narration(self, scene: Dict) -> Optional[str]:
        """提取并清洗旁白"""
        narration = scene.get("narration", "")
        if narration:
            return self.clean_for_tts(narration, "narration")
        return None


# 全局实例
text_cleaner = TextCleaner()


def clean_for_tts(text: str, context: str = "narration") -> str:
    """快捷清洗函数"""
    return text_cleaner.clean_for_tts(text, context)