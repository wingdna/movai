# modules/director_engine.py
"""
模块2：总导演引擎
读取 raw_source.json，生成 project_bible.json 和 beat_sheet.json
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import requests
from typing import List, Dict, Optional, Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import SILICONFLOW_API_KEY, SILICONFLOW_BASE_URL, MODELS


class DirectorEngine:
    """总导演引擎"""
    
    def __init__(self, input_path: str, output_dir: str, style: str = "赛博朋克"):
        self.input_path = Path(input_path)
        self.output_dir = Path(output_dir)
        self.style = style
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_source = self._load_raw_source()
        
        self.api_key = SILICONFLOW_API_KEY
        self.api_url = f"{SILICONFLOW_BASE_URL}/chat/completions"
        self.model = MODELS["director"]
        
        if not self.api_key:
            raise ValueError("未配置 SILICONFLOW_API_KEY")
    
    def _load_raw_source(self) -> Dict:
        if not self.input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {self.input_path}")
        with open(self.input_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_system_prompt(self) -> str:
        """加载系统提示词 - 使用最终版"""
        prompt_path = Path(__file__).parent.parent / "prompts" / "director_system_final.txt"
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        return self._get_fallback_prompt()
    
    def _get_fallback_prompt(self) -> str:
        """备用提示词"""
        return f"""你是一位影视导演，将文学作品改编为{self.style}风格。

## 元素转换规则（强制）
- 必须将原著中的传统元素转换为{self.style}风格对应的元素
- 不得出现：书生、小姐、老媪、古装、庭院、花园、书房、姻缘、红线

## 输出格式
必须输出JSON，包含：
1. world_setting: 世界观（time_period, location, atmosphere, core_conflict, visual_style）
2. character_visual_dict: 角色列表（name, identity, personality_traits, visual_anchor, voice_profile, initial_state）
3. beat_sheet: 节拍表（beat_id, beat_name, description, emotion, emotion_intensity, key_characters）

现在开始生成。
"""
    
    def _call_llm(self, user_content: str) -> Dict:
        """调用SiliconFlow API"""
        system_prompt = self._load_system_prompt()
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"}
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        print(f"🎬 调用导演模型: {self.model}")
        print(f"   风格: {self.style}")
        
        response = requests.post(self.api_url, json=payload, headers=headers, timeout=360)
        
        if response.status_code != 200:
            error_msg = f"API调用失败: {response.status_code}"
            try:
                error_data = response.json()
                if error_data.get("code") == 30001:
                    error_msg += " - 账户余额不足，请充值"
                else:
                    error_msg += f" - {error_data.get('message', response.text)}"
            except:
                error_msg += f" - {response.text}"
            raise Exception(error_msg)
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
            raise Exception(f"无法解析JSON: {content[:200]}...")
    
    def _build_user_prompt(self) -> str:
        text_chunks = self.raw_source.get("text_chunks", [])
        full_text = "".join(text_chunks) if text_chunks else self.raw_source.get("clean_text", "")
        
        if len(full_text) > 4000:
            full_text = full_text[:4000] + "...[内容已截断]"
        
        return f"""
    ## 原著信息
    - 书名: {self.raw_source.get('title', '未知')}
    - 作者: {self.raw_source.get('author', '未知')}

    ## 原著内容
    {full_text}

    ## 改编风格
    {self.style}

    请按照系统提示词的要求，生成完整的项目圣经JSON。
    """
    
    def _fix_project_bible_structure(self, data: Dict) -> Dict:
        """修复 project_bible 的结构问题"""
    
        # 1. 修复 character_visual_dict
        if "character_visual_dict" in data:
            chars = data["character_visual_dict"]
            if isinstance(chars, dict):
                chars = list(chars.values())
                data["character_visual_dict"] = chars
            
            # 检查角色数量
            if len(data["character_visual_dict"]) < 3:
                print(f"   ⚠️ 角色数量不足（当前 {len(data['character_visual_dict'])} 个），自动补充")
                data["character_visual_dict"] = self._supplement_characters(
                    data["character_visual_dict"], 
                    data.get("style", "伪纪录片_异星惊悚")
                )
        
        # 2. 确保 beat_sheet 存在且数量足够
        if "beat_sheet" not in data or not data["beat_sheet"]:
            print("   ⚠️ beat_sheet 缺失，使用默认节拍表")
            data["beat_sheet"] = self._generate_full_beat_sheet()
        elif len(data["beat_sheet"]) < 8:
            print(f"   ⚠️ 节拍数量不足（当前 {len(data['beat_sheet'])} 个），自动补充到8个")
            data["beat_sheet"] = self._expand_beat_sheet(data["beat_sheet"])
        
        # 3. 修复每个角色的状态
        for char in data.get("character_visual_dict", []):
            if "initial_state" not in char:
                char["initial_state"] = {"hp": 100, "location": "未知", "status": "ALIVE"}
            elif not isinstance(char["initial_state"], dict):
                char["initial_state"] = {"hp": 100, "location": "未知", "status": "ALIVE"}
        
        return data

    def _supplement_characters(self, existing_chars: List, style: str) -> List:
        """补充角色到至少 3 个"""
        chars = list(existing_chars)
        
        # 根据风格定义默认角色
        default_characters = {
            "伪纪录片_异星惊悚": [
                {"name": "调查员", "identity": "火星殖民地生物异常调查员", 
                 "personality_traits": ["专业", "警惕"], 
                 "visual_anchor": "wearing orange EVA suit, carrying scanner device",
                 "voice_profile": "tense, distorted by radio static",
                 "initial_state": {"hp": 100, "location": "调查站", "status": "ALIVE"}},
                {"name": "未知生物", "identity": "废弃实验室中的异常生物信号", 
                 "personality_traits": ["神秘", "不可知"], 
                 "visual_anchor": "biomechanical, organic metal texture, pulsating light",
                 "voice_profile": "distorted electronic whisper",
                 "initial_state": {"hp": 100, "location": "实验室深处", "status": "ALIVE"}},
                {"name": "指挥中心", "identity": "殖民地指挥中心AI", 
                 "personality_traits": ["冷静", "官僚"], 
                 "visual_anchor": "holographic display, flickering screens",
                 "voice_profile": "clinical, detached",
                 "initial_state": {"hp": 100, "location": "指挥中心", "status": "ALIVE"}}
            ],
            "赛博朋克": [
                {"name": "黑客", "identity": "地下黑客", 
                 "personality_traits": ["叛逆", "技术精通"], 
                 "visual_anchor": "cybernetic arm, neon tattoos, reflective coat",
                 "voice_profile": "gravelly, electronic distortion",
                 "initial_state": {"hp": 100, "location": "霓虹巷", "status": "ALIVE"}},
                {"name": "数据幽灵", "identity": "企业AI残留", 
                 "personality_traits": ["神秘", "危险"], 
                 "visual_anchor": "floating holograms, cold metallic face",
                 "voice_profile": "perfectly modulated",
                 "initial_state": {"hp": 100, "location": "数据深渊", "status": "ALIVE"}},
                {"name": "情报贩子", "identity": "街头情报商", 
                 "personality_traits": ["精明", "生存主义"], 
                 "visual_anchor": "mismatched cybernetic parts, data jacks on neck",
                 "voice_profile": "hoarse, quick",
                 "initial_state": {"hp": 100, "location": "地下市场", "status": "ALIVE"}}
            ]
        }
        
        default = default_characters.get(style, default_characters["伪纪录片_异星惊悚"])
        
        # 补充到3个
        for i in range(len(chars), 3):
            if i < len(default):
                chars.append(default[i])
            else:
                chars.append(default[0])
        
        print(f"   ✅ 已补充到 {len(chars)} 个角色")
        return chars

    def _generate_full_beat_sheet(self) -> list:
        """生成完整的8节拍表"""
        return [
            {"beat_id": 1, "beat_name": "异常信号", "description": "调查站检测到未知生物信号", 
             "emotion": "TENSION", "emotion_intensity": 0.5, "key_characters": ["调查员"], "estimated_duration_sec": 15},
            {"beat_id": 2, "beat_name": "深入调查", "description": "调查员进入废弃实验室", 
             "emotion": "FEAR", "emotion_intensity": 0.6, "key_characters": ["调查员"], "estimated_duration_sec": 20},
            {"beat_id": 3, "beat_name": "初次接触", "description": "发现异常生物信号来源", 
             "emotion": "HORROR", "emotion_intensity": 0.7, "key_characters": ["调查员", "未知生物"], "estimated_duration_sec": 25},
            {"beat_id": 4, "beat_name": "真相浮现", "description": "揭开殖民地秘密", 
             "emotion": "MYSTERY", "emotion_intensity": 0.6, "key_characters": ["调查员", "指挥中心"], "estimated_duration_sec": 20},
            {"beat_id": 5, "beat_name": "危机升级", "description": "生物信号变得危险", 
             "emotion": "FEAR", "emotion_intensity": 0.8, "key_characters": ["调查员", "未知生物"], "estimated_duration_sec": 25},
            {"beat_id": 6, "beat_name": "对峙", "description": "人类与异星生物的对峙", 
             "emotion": "TENSION", "emotion_intensity": 0.9, "key_characters": ["调查员", "未知生物"], "estimated_duration_sec": 30},
            {"beat_id": 7, "beat_name": "抉择", "description": "调查员面临艰难选择", 
             "emotion": "DESPAIR", "emotion_intensity": 0.7, "key_characters": ["调查员", "指挥中心"], "estimated_duration_sec": 20},
            {"beat_id": 8, "beat_name": "结局", "description": "故事收尾，真相大白", 
             "emotion": "REVELATION", "emotion_intensity": 0.5, "key_characters": ["调查员", "指挥中心"], "estimated_duration_sec": 20},
        ]

    def _expand_beat_sheet(self, existing_beats: list) -> list:
        """扩展节拍表到至少8个"""
        full_beats = self._generate_full_beat_sheet()
        
        # 保留原有的节拍，用默认的补充
        result = list(existing_beats)
        for i, beat in enumerate(full_beats):
            if i >= len(result):
                # 调整 beat_id
                beat["beat_id"] = i + 1
                result.append(beat)
        
        print(f"   ✅ 已扩展到 {len(result)} 个节拍")
        return result
    
    def _generate_default_beat_sheet(self) -> list:
        """生成默认节拍表"""
        return [
            {"beat_id": 1, "beat_name": "异常信号", "description": "调查站检测到未知生物信号", 
             "emotion": "TENSION", "emotion_intensity": 0.6, "key_characters": [], "estimated_duration_sec": 15},
            {"beat_id": 2, "beat_name": "初次接触", "description": "调查员发现异常生物", 
             "emotion": "FEAR", "emotion_intensity": 0.7, "key_characters": [], "estimated_duration_sec": 20},
            {"beat_id": 3, "beat_name": "真相浮现", "description": "揭开殖民地秘密", 
             "emotion": "REVELATION", "emotion_intensity": 0.8, "key_characters": [], "estimated_duration_sec": 25},
            {"beat_id": 4, "beat_name": "结局", "description": "人类与异星生物和解或冲突", 
             "emotion": "MYSTERY", "emotion_intensity": 0.5, "key_characters": [], "estimated_duration_sec": 20},
        ]
    
    def run(self) -> tuple:
        print("\n" + "="*60)
        print("🎬 模块2：总导演引擎 启动")
        print("="*60)
        
        user_prompt = self._build_user_prompt()
        result = self._call_llm(user_prompt)
        
        # 修复数据结构
        result = self._fix_project_bible_structure(result)
        
        project_bible = {
            "project_name": self.raw_source.get('title', '幻影卷轴项目'),
            "style": self.style,
            "generated_at": datetime.now().isoformat(),
            "world_setting": result.get("world_setting", {}),
            "character_visual_dict": result.get("character_visual_dict", []),
            "beat_sheet": result.get("beat_sheet", []),
        }
        
        beat_sheet = {
            "project_name": self.raw_source.get('title', '幻影卷轴项目'),
            "style": self.style,
            "generated_at": datetime.now().isoformat(),
            "beats": result.get("beat_sheet", []),
        }
        
        bible_path = self.output_dir / "project_bible.json"
        beat_path = self.output_dir / "beat_sheet.json"
        
        with open(bible_path, 'w', encoding='utf-8') as f:
            json.dump(project_bible, f, ensure_ascii=False, indent=2)
        
        with open(beat_path, 'w', encoding='utf-8') as f:
            json.dump(beat_sheet, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 项目圣经已保存: {bible_path}")
        print(f"   - 角色数量: {len(project_bible['character_visual_dict'])}")
        print(f"✅ 节拍表已保存: {beat_path}")
        print(f"   - 节拍数量: {len(beat_sheet['beats'])}")
        
        return bible_path, beat_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="./data/output")
    parser.add_argument("--style", default="赛博朋克")
    args = parser.parse_args()
    
    engine = DirectorEngine(args.input, args.output, args.style)
    engine.run()