# modules/writer_engine.py
"""
模块3：执笔编剧引擎 - 工业级完整版
将节拍表扩展为详细的分镜脚本，包含状态机、语言隔离、质量检查
"""
import json
import sys
import time
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import requests

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import SILICONFLOW_API_KEY, SILICONFLOW_BASE_URL, MODELS


class WriterEngine:
    """执笔编剧引擎 - 工业级实现"""
    
    def __init__(self, bible_path: str, beat_path: str, output_dir: str):
        """
        初始化编剧引擎
        
        Args:
            bible_path: project_bible.json 路径
            beat_path: beat_sheet.json 路径
            output_dir: 输出目录
        """
        self.bible_path = Path(bible_path)
        self.beat_path = Path(beat_path)
        self.output_dir = Path(output_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载数据
        self.bible = self._load_json(bible_path)
        self.beat_sheet = self._load_json(beat_path)
        
        # 初始化台账
        self.ledger = self._init_ledger()
        
        # 存储生成的所有场景
        self.scenes = []
        
        # 质量统计
        self.quality_stats = {
            "total_scenes": 0,
            "language_violations": 0,
            "camera_violations": 0,
            "hp_violations": 0,
            "fixes_applied": 0
        }
        
        # API配置
        self.api_key = SILICONFLOW_API_KEY
        self.api_url = f"{SILICONFLOW_BASE_URL}/chat/completions"
        self.model = MODELS["writer"]
        
        if not self.api_key:
            raise ValueError("未配置 SILICONFLOW_API_KEY")
        
        print(f"\n✅ WriterEngine 初始化完成")
        print(f"   - 风格: {self.bible.get('style', '未知')}")
        print(f"   - 角色数: {len(self.ledger['character_states'])}")
        print(f"   - 节拍数: {len(self.beat_sheet.get('beats', []))}")
    
    def _load_json(self, path: Path) -> Dict:
        """加载JSON文件"""
        if not Path(path).exists():
            raise FileNotFoundError(f"文件不存在: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _init_ledger(self) -> Dict[str, Any]:
        """初始化状态台账"""
        ledger = {
            "project_name": self.bible.get("project_name", "幻影卷轴"),
            "current_scene": 0,
            "completed_beats": [],
            "character_states": {},
            "hp_history": [],  # 记录HP变化历史
            "timeline": [],
        }
        
        characters = self.bible.get("character_visual_dict", [])
        
        print(f"\n📋 角色数据加载:")
        
        for char in characters:
            if isinstance(char, dict):
                name = char.get("name", "unknown")
                initial_state = char.get("initial_state", {})
                
                # 确保 initial_state 是正确格式
                if isinstance(initial_state, str):
                    initial_state = {"hp": 100, "location": initial_state, "status": "ALIVE"}
                elif not isinstance(initial_state, dict):
                    initial_state = {"hp": 100, "location": "起点", "status": "ALIVE"}
                
                # 确保必要字段存在
                initial_state.setdefault("hp", 100)
                initial_state.setdefault("location", "起点")
                initial_state.setdefault("status", "ALIVE")
                
                # 限制HP范围
                initial_state["hp"] = max(0, min(100, initial_state["hp"]))
                
                ledger["character_states"][name] = initial_state
                print(f"   - {name}: HP={initial_state['hp']}, 位置={initial_state['location']}")
        
        return ledger
    
    def _save_ledger(self):
        """保存状态台账"""
        ledger_path = self.output_dir / "production_ledger.json"
        with open(ledger_path, 'w', encoding='utf-8') as f:
            json.dump(self.ledger, f, ensure_ascii=False, indent=2)
    
    def _load_system_prompt(self) -> str:
        """加载系统提示词 - 使用最终版"""
        prompt_path = Path(__file__).parent.parent / "prompts" / "writer_system_final.txt"
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        return self._get_fallback_prompt()
    
    def _get_fallback_prompt(self) -> str:
        """备用提示词 - 强化约束"""
        return """你是专业的剧本编剧。

## ⚠️ 绝对语言隔离法则（违反将导致系统崩溃）

### 强制要求
| 字段 | 语言 | 正确示例 | 错误示例 |
|------|------|----------|----------|
| visual_action | 纯英文 | "kneeling on ground, red light" | ❌ "跪在地上，红光" |
| sfx_tags | 纯英文 | ["SFX: alarm_beeping"] | ❌ ["SFX: 警报声"] |
| vfx_tags | 纯英文 | ["VFX: static_glitch"] | ❌ ["VFX: 画面干扰"] |
| narration | 纯中文 | "监控画面显示异常" | ❌ "Monitor shows anomaly" |
| dialogues.line | 纯中文 | "生命体征出现异常" | ❌ "Vital signs abnormal" |

### 输出格式
{
  "scene_name": "场景名称",
  "visual_action": "纯英文动作和环境描述",
  "camera_movement": "STATIC/Z_DOLLY_IN/Z_DOLLY_OUT/PAN_LEFT/PAN_RIGHT/HANDHELD_SHAKE",
  "narration": "纯中文旁白，客观描述",
  "dialogues": [{"character": "角色名", "line": "纯中文对白"}],
  "sfx_tags": ["SFX: 纯英文标签"],
  "vfx_tags": ["VFX: 纯英文标签"],
  "state_updates": [{"character": "角色名", "hp_change": -5}]
}

### 状态更新规则
- hp_change: -50 到 +50
- HP低于0应改为DEAD状态

现在开始生成。
"""
    
    def _call_llm(self, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
        """调用SiliconFlow API，带重试机制"""
        system_prompt = self._load_system_prompt()
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 2048,
            "response_format": {"type": "json_object"}
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(self.api_url, json=payload, headers=headers, timeout=60)
                
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
                    
                    if attempt < max_retries - 1:
                        print(f"   ⚠️ {error_msg}，重试中 ({attempt + 1}/{max_retries})...")
                        time.sleep(2 ** attempt)
                        continue
                    raise Exception(error_msg)
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # 解析JSON
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # 尝试提取JSON
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        return json.loads(json_match.group())
                    raise Exception(f"无法解析JSON: {content[:200]}...")
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"   ⚠️ 网络错误: {e}，重试中 ({attempt + 1}/{max_retries})...")
                    time.sleep(2 ** attempt)
                    continue
                raise
        
        raise Exception(f"API调用失败，已重试{max_retries}次")
    
    def _fix_language_violations(self, scene: Dict) -> Dict:
        """修复语言隔离违反"""
        import re
        
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        english_pattern = re.compile(r'[A-Za-z]{3,}')
        
        # 修复 visual_action：移除中文
        if "visual_action" in scene:
            text = scene["visual_action"]
            if chinese_pattern.search(text):
                # 提取英文部分
                english_parts = re.findall(r'[A-Za-z0-9\s\.,!?\-_:/]+', text)
                clean_text = ' '.join(english_parts).strip()
                # 清理多余空格
                clean_text = re.sub(r'\s+', ' ', clean_text)
                if not clean_text or len(clean_text) < 5:
                    clean_text = "investigator in abandoned facility, emergency lighting"
                scene["visual_action"] = clean_text
                self.quality_stats["language_violations"] += 1
                self.quality_stats["fixes_applied"] += 1
                print(f"   🔧 修复 visual_action 中的中文")
        
        # 修复 narration：移除英文
        if "narration" in scene:
            text = scene["narration"]
            if english_pattern.search(text) and len(english_pattern.findall(text)) > 2:
                # 保留中文，移除英文
                chinese_parts = re.findall(r'[\u4e00-\u9fff\uff0c\u3002\uff01\uff1f\s]+', text)
                clean_text = ''.join(chinese_parts).strip()
                if not clean_text:
                    clean_text = "画面显示异常情况"
                scene["narration"] = clean_text
                self.quality_stats["language_violations"] += 1
                self.quality_stats["fixes_applied"] += 1
                print(f"   🔧 修复 narration 中的英文")
        
        # 修复 dialogues
        for dialogue in scene.get("dialogues", []):
            if "line" in dialogue:
                text = dialogue["line"]
                if english_pattern.search(text) and len(english_pattern.findall(text)) > 2:
                    # 严重英文，需要警告
                    print(f"   ⚠️ 对白包含大量英文: {text[:50]}...")
                    self.quality_stats["language_violations"] += 1
        
        # 修复 sfx_tags 和 vfx_tags
        for tag_list in ["sfx_tags", "vfx_tags"]:
            if tag_list in scene:
                fixed_tags = []
                for tag in scene[tag_list]:
                    # 移除中文
                    clean_tag = re.sub(r'[\u4e00-\u9fff]+', '', tag).strip()
                    clean_tag = re.sub(r'\s+', ' ', clean_tag)
                    if not clean_tag:
                        clean_tag = "SFX: ambient"
                    if not clean_tag.startswith(('SFX:', 'VFX:', 'AMBIENT:')):
                        clean_tag = f"SFX: {clean_tag}"
                    fixed_tags.append(clean_tag)
                scene[tag_list] = fixed_tags
        
        return scene
    
    def _fix_camera_movement(self, scene: Dict) -> Dict:
        """修复运镜枚举值"""
        valid_cams = [
            "STATIC", "Z_DOLLY_IN", "Z_DOLLY_OUT", "PAN_LEFT", "PAN_RIGHT",
            "TILT_UP", "TILT_DOWN", "HANDHELD_SHAKE", "STATIC_JITTER", "SLOW_PAN"
        ]
        
        if "camera_movement" in scene:
            cam = scene["camera_movement"].upper().strip()
            
            # 模糊匹配
            if cam not in valid_cams:
                for valid in valid_cams:
                    if cam in valid or valid in cam:
                        scene["camera_movement"] = valid
                        self.quality_stats["camera_violations"] += 1
                        self.quality_stats["fixes_applied"] += 1
                        print(f"   🔧 修复 camera_movement: {cam} → {valid}")
                        break
                else:
                    scene["camera_movement"] = "STATIC"
                    self.quality_stats["camera_violations"] += 1
                    print(f"   🔧 修复 camera_movement: {cam} → STATIC")
        
        return scene
    
    def _fix_hp_range(self, scene: Dict) -> Dict:
        """修复HP变化范围"""
        for update in scene.get("state_updates", []):
            if "hp_change" in update:
                hp_change = update["hp_change"]
                if hp_change < -50 or hp_change > 50:
                    old_value = hp_change
                    update["hp_change"] = max(-50, min(50, hp_change))
                    self.quality_stats["hp_violations"] += 1
                    self.quality_stats["fixes_applied"] += 1
                    print(f"   🔧 修复 hp_change: {old_value} → {update['hp_change']}")
        
        return scene
    
    def _update_ledger_from_scene(self, scene: Dict):
        """根据场景结果更新台账 - 正确累加HP变化"""
        state_updates = scene.get("state_updates", [])
        
        for update in state_updates:
            char_name = update.get("character", "")
            if char_name not in self.ledger["character_states"]:
                continue
            
            current_state = self.ledger["character_states"][char_name]
            hp_change = update.get("hp_change", 0)
            
            # 【关键】Python计算绝对值，而非LLM输出
            if hp_change != 0:
                old_hp = current_state.get("hp", 100)
                new_hp = old_hp + hp_change
                # 限制在 0-100 范围内
                new_hp = max(0, min(100, new_hp))
                current_state["hp"] = new_hp
                
                # 记录历史
                self.ledger["hp_history"].append({
                    "scene_id": scene.get("scene_id"),
                    "character": char_name,
                    "old_hp": old_hp,
                    "change": hp_change,
                    "new_hp": new_hp
                })
                
                print(f"   💔 {char_name}: HP {old_hp} → {new_hp} ({hp_change:+#d})")
                
                # HP归零时更新状态
                if new_hp <= 0:
                    current_state["status"] = "DEAD"
                    print(f"   💀 {char_name} 已死亡")
                elif new_hp <= 30 and current_state["status"] != "DEAD":
                    current_state["status"] = "CRITICAL"
                    print(f"   ⚠️ {char_name} 处于濒死状态")
                elif new_hp <= 70 and current_state["status"] == "ALIVE":
                    current_state["status"] = "INJURED"
            
            # 更新位置
            if "location_change" in update and update["location_change"]:
                current_state["location"] = update["location_change"]
            
            # 更新状态
            if "new_status" in update and update["new_status"]:
                current_state["status"] = update["new_status"]
        
        # 记录时间线
        self.ledger["timeline"].append({
            "scene_id": scene.get("scene_id"),
            "beat_id": scene.get("beat_id"),
            "scene_name": scene.get("scene_name"),
            "timestamp": datetime.now().isoformat(),
            "hp_snapshot": {
                name: state.get("hp", 100) 
                for name, state in self.ledger["character_states"].items()
            }
        })
        
        # 更新已完成的节拍
        beat_id = scene.get("beat_id")
        if beat_id and beat_id not in self.ledger["completed_beats"]:
            self.ledger["completed_beats"].append(beat_id)
    
    def _build_scene_prompt(self, beat: Dict, scene_index: int, scene_num_in_beat: int) -> str:
        """构建单个场景的提示词 - 强化约束"""
        world = self.bible.get("world_setting", {})
        style = self.bible.get("style", "赛博朋克")
        
        # 构建角色描述（只提供必要信息，不重复视觉锚点）
        characters = self.bible.get("character_visual_dict", [])
        char_desc_lines = []
        for c in characters:
            if isinstance(c, dict):
                name = c.get('name', '未知')
                identity = c.get('identity', '')
                status = self.ledger["character_states"].get(name, {}).get("status", "ALIVE")
                hp = self.ledger["character_states"].get(name, {}).get("hp", 100)
                char_desc_lines.append(f"- {name}: {identity} (状态: {status}, HP: {hp})")
        
        char_desc = "\n".join(char_desc_lines) if char_desc_lines else "无角色信息"
        
        # 当前状态台账摘要
        state_summary = []
        for name, state in self.ledger["character_states"].items():
            state_summary.append(f"{name}: HP={state.get('hp', 100)}, 位置={state.get('location', '未知')}")
        
        # 获取节拍信息
        beat_desc = f"""
节拍ID: {beat.get('beat_id')}
节拍名称: {beat.get('beat_name')}
描述: {beat.get('description')}
情绪: {beat.get('emotion', 'NEUTRAL')}
强度: {beat.get('emotion_intensity', 0.5)}
涉及角色: {beat.get('key_characters', [])}
"""
        
        return f"""
## 项目信息
- 项目名称: {self.bible.get('project_name', '未知')}
- 风格: {style}
- 当前场景序号: {scene_index}
- 本节拍内场景序号: {scene_num_in_beat}

## 世界观设定
{json.dumps(world, ensure_ascii=False, indent=2)}

## 角色列表
{char_desc}

## 当前状态台账
{chr(10).join(state_summary)}

## 当前节拍信息
{beat_desc}

## ⚠️ 生成前强制自检（必须通过）
1. [ ] visual_action 是否纯英文？如有中文，请改为英文
2. [ ] narration 是否纯中文？如有英文，请改为中文
3. [ ] dialogues.line 是否纯中文？如有英文，请改为中文
4. [ ] camera_movement 是否是枚举值？
5. [ ] hp_change 是否在 -50 到 +50 之间？

请输出JSON格式的场景分镜。
"""
    
    def _generate_scene_for_beat(self, beat: Dict, beat_index: int, scene_index: int) -> Optional[Dict]:
        """为单个节拍生成场景，带重试"""
        # 根据情绪强度决定每个节拍生成多少个场景
        emotion_intensity = beat.get("emotion_intensity", 0.5)
        num_scenes = max(1, min(4, int(emotion_intensity * 3) + 1))
        
        scenes_in_beat = []
        
        for i in range(num_scenes):
            print(f"   生成场景 {scene_index + i}...")
            
            prompt = self._build_scene_prompt(beat, scene_index + i, i + 1)
            
            try:
                # 调用LLM
                scene = self._call_llm(prompt)
                
                # 数据修复
                scene = self._fix_language_violations(scene)
                scene = self._fix_camera_movement(scene)
                scene = self._fix_hp_range(scene)
                
                # 补充元数据
                scene["scene_id"] = scene_index + i
                scene["beat_id"] = beat.get("beat_id")
                scene["generated_at"] = datetime.now().isoformat()
                
                # 更新台账
                self._update_ledger_from_scene(scene)
                self.ledger["current_scene"] = scene_index + i
                
                scenes_in_beat.append(scene)
                
                # 避免API限流
                time.sleep(0.5)
                
            except Exception as e:
                print(f"   ❌ 生成失败: {e}")
                # 尝试生成默认场景
                default_scene = self._get_default_scene(scene_index + i, beat)
                scenes_in_beat.append(default_scene)
                self._update_ledger_from_scene(default_scene)
        
        return scenes_in_beat
    
    def _get_default_scene(self, scene_id: int, beat: Dict) -> Dict:
        """返回默认场景"""
        style = self.bible.get("style", "赛博朋克")
        
        # 根据风格选择默认描述
        default_visuals = {
            "伪纪录片_异星惊悚": "investigator standing in abandoned facility, emergency lights flickering, dust particles floating",
            "赛博朋克": "hacker standing on neon-lit street, rain falling, holographic ads reflecting on wet ground",
            "武侠": "swordsman standing in bamboo forest, mist swirling, sword at side",
            "废土": "survivor walking through desert ruins, sandstorm approaching",
            "仙侠": "cultivator meditating on floating mountain, spiritual energy flowing",
            "悬疑": "detective examining crime scene, shadows cast by venetian blinds"
        }
        
        return {
            "scene_name": f"场景{scene_id}",
            "visual_action": default_visuals.get(style, "character in scene, atmospheric lighting"),
            "camera_movement": "STATIC",
            "narration": "画面显示，场景正在继续。",
            "dialogues": [],
            "sfx_tags": ["SFX: ambient"],
            "vfx_tags": [],
            "state_updates": [],
            "scene_id": scene_id,
            "beat_id": beat.get("beat_id"),
            "generated_at": datetime.now().isoformat()
        }
    
    def _generate_all_scenes(self) -> List[Dict]:
        """生成所有场景"""
        beats = self.beat_sheet.get("beats", [])
        all_scenes = []
        scene_index = 1
        
        for beat_index, beat in enumerate(beats):
            print(f"\n📝 处理节拍 {beat.get('beat_id')}: {beat.get('beat_name')}")
            
            scenes = self._generate_scene_for_beat(beat, beat_index, scene_index)
            if scenes:
                all_scenes.extend(scenes)
                scene_index += len(scenes)
        
        return all_scenes
    
    def _post_process_scenes(self, scenes: List[Dict]) -> List[Dict]:
        """后处理：确保所有场景都通过质量检查"""
        processed = []
        
        for scene in scenes:
            # 最终语言检查
            scene = self._fix_language_violations(scene)
            scene = self._fix_camera_movement(scene)
            scene = self._fix_hp_range(scene)
            
            processed.append(scene)
        
        return processed
    
    def _generate_quality_report(self) -> str:
        """生成质量报告"""
        total = self.quality_stats["total_scenes"]
        if total == 0:
            return "无场景数据"
        
        report = f"""
## 质量报告
- 总场景数: {total}
- 语言违规修复: {self.quality_stats['language_violations']}
- 运镜违规修复: {self.quality_stats['camera_violations']}
- HP违规修复: {self.quality_stats['hp_violations']}
- 总修复次数: {self.quality_stats['fixes_applied']}
- 质量评分: {max(0, 100 - self.quality_stats['fixes_applied'] * 2)}/100
"""
        return report
    
    def run(self) -> Path:
        """执行编剧引擎"""
        print("\n" + "=" * 60)
        print("✍️ 模块3：执笔编剧引擎 启动")
        print("=" * 60)
        
        beats = self.beat_sheet.get("beats", [])
        print(f"📖 节拍表加载完成，共 {len(beats)} 个节拍")
        
        # 生成所有场景
        self.scenes = self._generate_all_scenes()
        self.quality_stats["total_scenes"] = len(self.scenes)
        
        # 后处理
        self.scenes = self._post_process_scenes(self.scenes)
        
        # 构建主剧本
        master_script = {
            "project_name": self.bible.get("project_name", "幻影卷轴"),
            "style": self.bible.get("style", "赛博朋克"),
            "generated_at": datetime.now().isoformat(),
            "total_scenes": len(self.scenes),
            "characters": self.bible.get("character_visual_dict", []),
            "scenes": self.scenes,
            "ledger_snapshot": {
                "project_name": self.ledger["project_name"],
                "current_scene": self.ledger["current_scene"],
                "completed_beats": self.ledger["completed_beats"],
                "character_states": self.ledger["character_states"],
                "hp_history": self.ledger["hp_history"][-10:],  # 只保留最近10条
                "timeline": self.ledger["timeline"]
            },
            "quality_report": self._generate_quality_report()
        }
        
        # 保存主剧本
        script_path = self.output_dir / "master_script.json"
        with open(script_path, 'w', encoding='utf-8') as f:
            json.dump(master_script, f, ensure_ascii=False, indent=2)
        
        # 保存最终台账
        self._save_ledger()
        
        print(f"\n✅ 主剧本已保存: {script_path}")
        print(f"   - 总场景数: {len(self.scenes)}")
        print(f"   - 质量报告: {master_script['quality_report']}")
        
        # 打印最终HP状态
        print("\n📊 最终角色状态:")
        for name, state in self.ledger["character_states"].items():
            print(f"   - {name}: HP={state.get('hp', 100)}, 状态={state.get('status', '未知')}")
        
        return script_path


# 命令行入口
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="执笔编剧引擎")
    parser.add_argument("--bible", required=True, help="project_bible.json路径")
    parser.add_argument("--beat", required=True, help="beat_sheet.json路径")
    parser.add_argument("--output", default="./data/output", help="输出目录")
    
    args = parser.parse_args()
    
    engine = WriterEngine(args.bible, args.beat, args.output)
    engine.run()