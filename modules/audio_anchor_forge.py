# modules/audio_anchor_forge.py
"""
模块4：音频锚点工坊 (Audio_Anchor_Forge)
- 生成旁白和对话音频（Edge-TTS，带黑客级情绪与节奏注入）
- 下载音效（集成 11Labs 与 Jamendo 级联架构）
- 计算精确时长并回写JSON (彻底修复 NameError 崩溃 BUG)
"""
import json
import os
import sys
import asyncio
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import traceback

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from modules.voice_manager import VoiceManager
    from modules.sfx_downloader import SFXDownloader
    from modules.audio_utils import get_audio_duration, merge_audio_files
except ImportError:
    from voice_manager import VoiceManager
    from sfx_downloader import SFXDownloader
    from audio_utils import get_audio_duration, merge_audio_files

def clean_text_for_tts(raw_text: str) -> str:
    """暴力清洗器：刮除大模型可能生成的任何 XML/SSML 标签，防止机器乱读"""
    if not raw_text:
        return ""
    text = re.sub(r'<\?xml[^>]+\?>', '', raw_text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def inject_dramatic_pauses(text: str) -> str:
    """标点黑客法：强行拉长标点符号停顿，制造窒息感"""
    text = text.replace("...", "。。。")
    text = text.replace("！", "！ ")
    text = text.replace("？", "？ ")
    return text

def parse_emotion_and_get_params(text: str, is_narrator: bool = False) -> tuple:
    """情绪解析器：提取大模型的情绪标签，转为 Edge-TTS 免费参数，并剔除标签"""
    rate, pitch, volume = "+0%", "+0Hz", "+0%"
    
    if is_narrator:
        # 伪纪录片旁白：冷峻、缓慢、低沉
        return text, "-10%", "-5Hz", "+0%"

    emotion_match = re.search(r'\[(.*?)\]|\((.*?)\)|（(.*?)）|【(.*?)】', text)
    if emotion_match:
        emotion = emotion_match.group(0)
        emotion_content = emotion_match.group(1) or emotion_match.group(2) or emotion_match.group(3) or emotion_match.group(4)
        emotion_content = emotion_content.lower()
        
        if any(word in emotion_content for word in["喊", "咆哮", "激动", "惊恐", "尖叫"]):
            rate, pitch, volume = "+15%", "+10Hz", "+20%" 
        elif any(word in emotion_content for word in["低语", "虚弱", "绝望", "喘息", "喃喃"]):
            rate, pitch, volume = "-20%", "-15Hz", "-10%" 
        elif any(word in emotion_content for word in ["冷酷", "机械", "电子", "平静"]):
            rate, pitch, volume = "-5%", "-10Hz", "+0%"
        elif any(word in emotion_content for word in ["笑", "高频", "诡异"]):
            rate, pitch, volume = "+10%", "+20Hz", "+0%"
            
        clean_text = text.replace(emotion, "").strip()
        return clean_text, rate, pitch, volume
    
    return text, rate, pitch, volume

class AudioAnchorForge:
    def __init__(self, script_path: str, output_dir: str = "./data/output", 
                 audio_dir: str = "./data/audio",
                 proxy_host: str = "127.0.0.1", proxy_port: int = 7890):
        self.script_path = Path(script_path)
        self.output_dir = Path(output_dir)
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.master_script = self._load_script()
        self.voice_manager = VoiceManager()
        
        # ✅ 初始化强大的多极降级下载器
        self.sfx_downloader = SFXDownloader(
            proxy_host=proxy_host, 
            proxy_port=proxy_port,
            force_redownload=True  
        )
        
        self.stats = {"total_scenes": 0, "narration_generated": 0, "dialogue_generated": 0, "sfx_downloaded": 0, "failed": 0, "total_duration_ms": 0}
        
        print("\n" + "="*60)
        print("🎵 音频锚点工坊 (AI+电影级声学强化版) 初始化")
        print("="*60)

    def _load_script(self) -> Dict:
        if not self.script_path.exists():
            raise FileNotFoundError(f"剧本文件不存在: {self.script_path}")
        with open(self.script_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _get_character_voice(self, character_name: str) -> str:
        characters = self.master_script.get("characters",[])
        for char in characters:
            if char.get("name") == character_name:
                voice_profile = char.get("voice_profile", "")
                return self.voice_manager.select_voice_by_profile(character_name, voice_profile)
        # 未知生物默认用比较诡异的女声，调查员默认用沉稳男声
        if "未知" in character_name or "YN" in character_name:
            return "zh-CN-XiaoyiNeural"
        return "zh-CN-YunxiNeural"

    def _generate_speech(self, text: str, output_path: str, voice: str, rate: str, pitch: str, volume: str) -> bool:
        """核心生成逻辑：使用 Edge-TTS 原生参数调节取代失效的 express-as"""
        try:
            import edge_tts
            communicate = edge_tts.Communicate(
                text=text, 
                voice=voice,
                rate=rate,
                pitch=pitch,
                volume=volume
            )
            
            async def _generate():
                await communicate.save(output_path)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_generate())
            loop.close()
            
            return os.path.exists(output_path)
        except Exception as e:
            print(f"      ❌ 语音生成失败: {e}")
            return False

    def _generate_narration_audio(self, scene: Dict, scene_idx: int) -> Optional[str]:
        narration = scene.get("narration", "")
        if not narration or len(narration.strip()) < 3:
            return None
            
        output_path = self.audio_dir / f"scene_{scene_idx:03d}_narration.mp3"
        
        clean_text = clean_text_for_tts(narration)
        final_text, rate, pitch, volume = parse_emotion_and_get_params(clean_text, is_narrator=True)
        final_text = inject_dramatic_pauses(final_text)
        
        print(f"   🎤 旁白 | 音色:Yunyang | 语速:{rate} | 文本: {final_text[:30]}...")
        
        if self._generate_speech(final_text, str(output_path), "zh-CN-YunyangNeural", rate, pitch, volume):
            self.stats["narration_generated"] += 1
            return str(output_path)
        return None

    def _generate_dialogue_audio(self, scene: Dict, scene_idx: int, dialogue_idx: int, dialogue: Dict) -> Optional[str]:
        line = dialogue.get("line", "")
        character = dialogue.get("character", "未知")
        
        if not line or len(line.strip()) < 2:
            return None
            
        output_path = self.audio_dir / f"scene_{scene_idx:03d}_dialogue_{dialogue_idx:02d}_{character}.mp3"
        voice = self._get_character_voice(character)
        
        clean_text = clean_text_for_tts(line)
        final_text, rate, pitch, volume = parse_emotion_and_get_params(clean_text)
        final_text = inject_dramatic_pauses(final_text)
        
        print(f"   🎤 {character} | 音色:{voice.split('-')[-1]} | 语速:{rate} | 文本: {final_text[:30]}...")
        
        if self._generate_speech(final_text, str(output_path), voice, rate, pitch, volume):
            self.stats["dialogue_generated"] += 1
            return str(output_path)
        return None

    def _download_sfx(self, sfx_tag: str, scene_idx: int, sfx_idx: int) -> Optional[str]:
        if not sfx_tag: return None
        clean_tag = sfx_tag.replace("SFX:", "").replace("VFX:", "").strip()
        clean_tag = re.sub(r'[^\w\s]', '', clean_tag)
        if len(clean_tag) < 3: return None
        
        output_path = self.audio_dir / f"scene_{scene_idx:03d}_sfx_{sfx_idx:02d}.mp3"
        
        # 将调用交接给强大的降级引擎，指定生成的音效时长
        if self.sfx_downloader.download_sfx(clean_tag, str(output_path), duration=6):
            self.stats["sfx_downloaded"] += 1
            return str(output_path)
        return None

    def _calculate_scene_duration(self, narration_path, dialogue_paths, sfx_paths) -> float:
        total_duration = 0.0
        all_audio =[]
        if narration_path: all_audio.append(narration_path)
        all_audio.extend(dialogue_paths)
        all_audio.extend(sfx_paths)
        
        for i, audio_path in enumerate(all_audio):
            duration = get_audio_duration(audio_path)
            if duration:
                total_duration += duration
                if i < len(all_audio) - 1:
                    total_duration += 0.5  # 增加留白
        
        # 场景保底 4 秒
        return max(total_duration, 4.0)

    def process_scene(self, scene: Dict, scene_idx: int) -> Dict:
        print(f"\n{'='*50}\n🎬 处理场景 {scene_idx}: {scene.get('scene_name', '未命名')}\n{'='*50}")
        
        narration_path = self._generate_narration_audio(scene, scene_idx)
        
        dialogue_paths =[]
        for dia_idx, dialogue in enumerate(scene.get("dialogues",[])):
            path = self._generate_dialogue_audio(scene, scene_idx, dia_idx + 1, dialogue)
            if path: dialogue_paths.append(path)
            
        sfx_paths =[]
        for sfx_idx, sfx_tag in enumerate(scene.get("sfx_tags",[])):
            path = self._download_sfx(sfx_tag, scene_idx, sfx_idx + 1)
            if path: sfx_paths.append(path)

        # 🚀 核心架构级修复：必须先计算好真实 duration 才能去生成/下载对应时长的 BGM
        scene_duration = self._calculate_scene_duration(narration_path, dialogue_paths, sfx_paths)
        self.stats["total_duration_ms"] += scene_duration * 1000

        emotion = scene.get("emotion", "tension")
        bgm_path = self.audio_dir / f"scene_{scene_idx:03d}_bgm.mp3"    
        
        # 此时基于准确的时间下载电影原声带
        bgm_success = self.sfx_downloader.download_bgm(
            query=emotion,
            output_path=str(bgm_path),
            duration=int(scene_duration) + 5
        )
        
        # 将生成的音频组装返回
        scene["audio_tracks"] = {
            "narration": narration_path,
            "dialogues": dialogue_paths,
            "sfx": sfx_paths,
            "bgm": str(bgm_path) if bgm_success else None
        }
        scene["duration_ms"] = int(scene_duration * 1000)
        return scene

    def run(self) -> Path:
        scenes = self.master_script.get("scenes",[])
        self.stats["total_scenes"] = len(scenes)
        
        updated_scenes =[]
        for idx, scene in enumerate(scenes, 1):
            try:
                updated_scenes.append(self.process_scene(scene, idx))
            except Exception as e:
                print(f"   ❌ 场景 {idx} 处理失败: {e}")
                traceback.print_exc()
                updated_scenes.append(scene)
        
        timed_script = {
            **self.master_script,
            "scenes": updated_scenes,
            "total_duration_ms": self.stats["total_duration_ms"]
        }
        
        output_path = self.output_dir / "timed_script.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(timed_script, f, ensure_ascii=False, indent=2)
            
        print(f"\n✅ 音频锚点工坊完成! 总时长: {self.stats['total_duration_ms'] / 1000:.2f} 秒")
        return output_path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True)
    parser.add_argument("--output", default="./data/output")
    parser.add_argument("--audio-dir", default="./data/audio")
    args = parser.parse_args()
    AudioAnchorForge(args.script, args.output, args.audio_dir).run()