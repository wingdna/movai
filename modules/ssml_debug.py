# modules/ssml_debug.py
"""
SSML 调试工具
"""
import re


def validate_ssml(ssml: str) -> tuple:
    """
    验证 SSML 格式
    
    Returns:
        (is_valid, error_message)
    """
    # 检查是否有未转义的标签
    text_content = re.search(r'<prosody[^>]*>(.*?)</prosody>', ssml, re.DOTALL)
    if text_content:
        text = text_content.group(1)
        if '<' in text or '>' in text:
            return False, f"文本中包含未转义的标签字符: {text[:50]}"
    
    # 检查标签是否闭合
    stack = []
    tag_pattern = re.compile(r'<(\/?)([^>\s]+)')
    for match in tag_pattern.finditer(ssml):
        is_close = match.group(1) == '/'
        tag_name = match.group(2)
        
        if is_close:
            if not stack or stack[-1] != tag_name:
                return False, f"标签闭合错误: 多余的 </{tag_name}>"
            stack.pop()
        else:
            stack.append(tag_name)
    
    if stack:
        return False, f"未闭合的标签: {stack}"
    
    return True, "OK"


def preview_ssml(ssml: str, max_len: int = 200) -> str:
    """预览 SSML"""
    # 提取文本内容
    text = re.sub(r'<[^>]+>', ' ', ssml)
    text = re.sub(r'\s+', ' ', text)
    return text[:max_len]