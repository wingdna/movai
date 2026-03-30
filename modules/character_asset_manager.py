# modules/character_asset_manager.py
"""
角色资产管理器 - 确保人物形象一致性
- 生成角色四方向图（正面、背面、左侧面、右侧面）
- 使用 SiliconFlow Kolors API（与场景图生成相同）
- 提供角色一致性约束用于场景生成
"""
import json
import os
import sys
import time
import requests
import base64
import random
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import SILICONFLOW_API_KEY, SILICONFLOW_BASE_URL


class CharacterAssetManager:
    """角色资产管理器 - 完整版，支持角色一致性约束"""
    
    # 四方向定义
    DIRECTIONS = {
        "front": {"angle": 0, "description": "正面", "prompt_suffix": "facing camera, front view, full body"},
        "back": {"angle": 180, "description": "背面", "prompt_suffix": "from behind, back view, full body"},
        "left": {"angle": 90, "description": "左侧面", "prompt_suffix": "left side view, profile facing right, full body"},
        "right": {"angle": -90, "description": "右侧面", "prompt_suffix": "right side view, profile facing left, full body"}
    }
    
    # 相机角度到参考方向的映射
    CAMERA_ANGLE_MAP = {
        "front": "front",
        "back": "back",
        "left": "left",
        "right": "right",
        "three_quarter": "front",
        "close_up": "front",
        "full_body": "front",
        "side": "left",
        "profile": "left"
    }
    
    def __init__(self, project_dir: str = "./data/characters"):
        """
        初始化角色资产管理器
        """
        self.project_dir = Path(project_dir)
        self.characters_dir = self.project_dir / "characters"
        self.reference_dir = self.project_dir / "references"
        
        # 创建目录
        self.characters_dir.mkdir(parents=True, exist_ok=True)
        self.reference_dir.mkdir(parents=True, exist_ok=True)
        
        # 角色库
        self.characters = {}
        
        # API配置（与场景图生成相同，使用可图）
        self.api_key = SILICONFLOW_API_KEY
        self.base_url = SILICONFLOW_BASE_URL
        
        print("\n" + "="*60)
        print("🎭 角色资产管理器 初始化")
        print("="*60)
        print(f"📁 角色目录: {self.characters_dir}")
        print(f"📁 参考目录: {self.reference_dir}")
        print(f"🎨 使用模型: Kwai-Kolors/Kolors (可图)")
        print("="*60)
    
    # ========== 原有方法保持不变 ==========
    
    def load_characters_from_bible(self, bible_path: Path) -> List[Dict]:
        """从项目圣经加载角色信息"""
        with open(bible_path, 'r', encoding='utf-8') as f:
            bible = json.load(f)
        
        characters = bible.get("character_visual_dict", [])
        
        for char in characters:
            name = char.get("name")
            if name:
                self.characters[name] = {
                    "name": name,
                    "identity": char.get("identity", ""),
                    "personality_traits": char.get("personality_traits", []),
                    "visual_anchor": char.get("visual_anchor", ""),
                    "voice_profile": char.get("voice_profile", ""),
                    "initial_state": char.get("initial_state", {}),
                    "directions": {}
                }
        
        print(f"✅ 加载了 {len(self.characters)} 个角色")
        return list(self.characters.values())
    
    def generate_character_directions(self, character: Dict, 
                                       width: int = 512, height: int = 512,
                                       max_retries: int = 3) -> Dict[str, Path]:
        """为单个角色生成四方向图"""
        char_name = character["name"]
        visual_anchor = character.get("visual_anchor", "")
        identity = character.get("identity", "")
        
        # 创建角色专属目录
        char_dir = self.characters_dir / char_name
        char_dir.mkdir(parents=True, exist_ok=True)
        
        results = {}
        
        print(f"\n   🎨 生成角色 [{char_name}] 四方向图...")
        
        for direction, dir_info in self.DIRECTIONS.items():
            print(f"      📐 方向: {dir_info['description']}")
            
            # 构建 Prompt
            prompt, negative_prompt = self._build_character_prompt(
                character_name=char_name,
                identity=identity,
                visual_anchor=visual_anchor,
                direction=dir_info["prompt_suffix"]
            )
            
            # 生成图像
            image_path = char_dir / f"{char_name}_{direction}.png"
            
            print(f"         📝 Prompt: {prompt[:80]}...")
            
            success = self._generate_character_image(prompt, negative_prompt, image_path, width, height, max_retries)
            
            if success:
                results[direction] = image_path
                print(f"         ✅ {direction}.png 已保存")
            else:
                print(f"         ❌ {direction}.png 生成失败")
            
            # 避免限流
            time.sleep(3)
        
        # 更新角色数据
        if char_name in self.characters:
            self.characters[char_name]["directions"] = {
                dir: str(path) for dir, path in results.items()
            }
        
        return results
    
    def _build_character_prompt(self, character_name: str, identity: str,
                                 visual_anchor: str, direction: str) -> Tuple[str, str]:
        """构建角色生成 Prompt"""
        
        # 基础描述 - 使用英文提示词以获得更好效果
        prompt_parts = [
            f"full body character design of {character_name}",
            f"a {identity}" if identity else "",
            visual_anchor if visual_anchor else "",
            direction,
            "standing pose, arms relaxed at sides",
            "clean white background, character turnaround sheet style",
            "highly detailed, sharp focus, professional character design",
            "consistent features, same outfit, same hairstyle, same face"
        ]
        
        # 过滤空字符串
        prompt_parts = [p for p in prompt_parts if p]
        
        # 质量词
        quality_tags = ["8k", "photorealistic", "concept art", "character reference"]
        prompt_parts.extend(quality_tags)
        
        # 负面提示词
        negative_prompt = (
            "multiple people, different characters, blurry, low quality, "
            "distorted, bad anatomy, extra limbs, watermark, text, signature, "
            "different clothing, different hairstyle, inconsistent features, "
            "background with people, complex background, scenery"
        )
        
        return ", ".join(prompt_parts), negative_prompt
    
    def _generate_character_image(self, prompt: str, negative_prompt: str,
                                   output_path: Path, width: int, height: int,
                                   max_retries: int) -> bool:
        """生成角色图像 - 使用与场景图相同的可图 API"""
        if not self.api_key:
            print(f"         ❌ API Key 未配置")
            return False
        
        # 使用与场景图生成相同的 API 端点
        url = f"{self.base_url}/images/generations"
        
        # 确保尺寸是 16 的倍数
        width = ((width // 16) * 16)
        height = ((height // 16) * 16)
        
        # 使用与场景图生成相同的参数
        payload = {
            "model": "Kwai-Kolors/Kolors",
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "num_images": 4,
            "num_inference_steps": 50,
            "guidance_scale": 8.5,
            "seed": random.randint(0, 2**32 - 1)
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        print(f"         🎨 调用可图 API: {url}")
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=120)
                
                if response.status_code == 200:
                    data = response.json()
                    images = data.get("data", [])
                    if images:
                        img_data = images[0]
                        if "b64_json" in img_data:
                            image_bytes = base64.b64decode(img_data["b64_json"])
                            with open(output_path, 'wb') as f:
                                f.write(image_bytes)
                            return True
                        elif "url" in img_data:
                            img_response = requests.get(img_data["url"], timeout=30)
                            if img_response.status_code == 200:
                                with open(output_path, 'wb') as f:
                                    f.write(img_response.content)
                                return True
                    print(f"         ❌ 返回数据为空")
                    return False
                
                elif response.status_code == 429:
                    wait_time = 30 * (attempt + 1)
                    print(f"         ⚠️ 限流，等待 {wait_time} 秒...")
                    time.sleep(wait_time)
                    continue
                
                elif response.status_code == 401:
                    print(f"         ❌ API Key 无效")
                    return False
                
                elif response.status_code == 404:
                    print(f"         ❌ API 端点不存在: {url}")
                    print(f"         💡 尝试备用端点...")
                    return self._generate_character_image_fallback(prompt, negative_prompt, output_path, width, height, max_retries)
                
                else:
                    print(f"         ❌ API 错误: {response.status_code}")
                    print(f"         📝 响应: {response.text[:200]}")
                    if attempt < max_retries - 1:
                        time.sleep(10)
                        continue
                    return False
                    
            except requests.exceptions.Timeout:
                print(f"         ⚠️ 请求超时")
                if attempt < max_retries - 1:
                    time.sleep(10)
                    continue
                return False
            except Exception as e:
                print(f"         ❌ 请求失败: {e}")
                if attempt < max_retries - 1:
                    time.sleep(10)
                    continue
                return False
        
        return False
    
    def _generate_character_image_fallback(self, prompt: str, negative_prompt: str,
                                            output_path: Path, width: int, height: int,
                                            max_retries: int) -> bool:
        """备用端点 - 使用 v1/images/generations"""
        if not self.api_key:
            return False
        
        url = f"{self.base_url}/v1/images/generations"
        
        width = ((width // 16) * 16)
        height = ((height // 16) * 16)
        
        payload = {
            "model": "Kwai-Kolors/Kolors",
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "num_images": 4,
            "num_inference_steps": 50,
            "guidance_scale": 8.5,
            "seed": random.randint(0, 2**32 - 1)
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        print(f"         🎨 调用备用 API: {url}")
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=120)
                
                if response.status_code == 200:
                    data = response.json()
                    images = data.get("data", [])
                    if images:
                        img_data = images[0]
                        if "b64_json" in img_data:
                            image_bytes = base64.b64decode(img_data["b64_json"])
                            with open(output_path, 'wb') as f:
                                f.write(image_bytes)
                            return True
                        elif "url" in img_data:
                            img_response = requests.get(img_data["url"], timeout=30)
                            if img_response.status_code == 200:
                                with open(output_path, 'wb') as f:
                                    f.write(img_response.content)
                                return True
                    return False
                
                elif response.status_code == 429:
                    wait_time = 30 * (attempt + 1)
                    print(f"         ⚠️ 限流，等待 {wait_time} 秒...")
                    time.sleep(wait_time)
                    continue
                
                else:
                    if attempt < max_retries - 1:
                        time.sleep(10)
                        continue
                    return False
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(10)
                    continue
                return False
        
        return False
    
    # ========== 原有辅助方法 ==========
    
    def get_character_reference(self, character_name: str, direction: str = "front") -> Optional[Path]:
        """获取角色参考图路径"""
        if character_name not in self.characters:
            return None
        
        directions = self.characters[character_name].get("directions", {})
        if direction in directions:
            return Path(directions[direction])
        
        for d in directions.values():
            return Path(d)
        
        return None
    
    def get_character_consistency_prompt(self, character_name: str, scene_action: str = "") -> str:
        """获取角色一致性 Prompt 片段（简单版）"""
        if character_name not in self.characters:
            return scene_action
        
        char_data = self.characters[character_name]
        visual_anchor = char_data.get("visual_anchor", "")
        
        if scene_action:
            return f"{visual_anchor}, {scene_action}"
        
        return visual_anchor
    
    def save_character_manifest(self) -> Path:
        """保存角色清单"""
        manifest_path = self.project_dir / "character_manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self.characters, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 角色清单已保存: {manifest_path}")
        return manifest_path
    
    def load_character_manifest(self, manifest_path: Path) -> Dict:
        """加载角色清单"""
        with open(manifest_path, 'r', encoding='utf-8') as f:
            self.characters = json.load(f)
        
        print(f"✅ 加载了 {len(self.characters)} 个角色")
        return self.characters
    
    # ========== 新增：角色一致性系统核心方法 ==========
    
    def get_character_reference_base64(self, character_name: str, direction: str = "front") -> Optional[str]:
        """
        获取角色参考图的 Base64 编码（用于嵌入 Prompt）
        
        Args:
            character_name: 角色名称
            direction: 方向 (front/back/left/right)
        
        Returns:
            Base64 编码的图像数据，或 None
        """
        if character_name not in self.characters:
            return None
        
        directions = self.characters[character_name].get("directions", {})
        
        # 如果指定方向存在，使用它；否则使用第一个可用的
        target_dir = direction if direction in directions else next(iter(directions.values()), None)
        
        if not target_dir:
            return None
        
        path = Path(target_dir)
        if not path.exists():
            return None
        
        with open(path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')
        
        return f"data:image/png;base64,{img_data}"
    
    def get_character_description(self, character_name: str) -> str:
        """
        获取角色的详细文字描述（用于 Prompt 约束）
        
        Args:
            character_name: 角色名称
        
        Returns:
            角色描述文本
        """
        if character_name not in self.characters:
            return ""
        
        char_data = self.characters[character_name]
        visual_anchor = char_data.get("visual_anchor", "")
        identity = char_data.get("identity", "")
        
        return f"{identity}, {visual_anchor}"
    
    def build_consistency_prompt(self, character_name: str, 
                                   scene_action: str,
                                   camera_angle: str = "full_body") -> str:
        """
        构建角色一致性 Prompt 片段
        
        Args:
            character_name: 角色名称
            scene_action: 场景动作描述
            camera_angle: 相机角度 (front/back/left/right/three_quarter/close_up/full_body/side)
        
        Returns:
            增强的一致性 Prompt
        """
        if character_name not in self.characters:
            return scene_action
        
        char_data = self.characters[character_name]
        visual_anchor = char_data.get("visual_anchor", "")
        identity = char_data.get("identity", "")
        
        # 相机角度到参考方向的映射
        angle_to_direction = {
            "front": "front view",
            "back": "back view",
            "left": "left side view",
            "right": "right side view",
            "three_quarter": "three-quarter view",
            "close_up": "close up on face",
            "full_body": "full body shot",
            "side": "side view, profile"
        }
        
        angle_desc = angle_to_direction.get(camera_angle, "full body shot")
        
        # 获取参考方向（用于提示）
        ref_direction = self.CAMERA_ANGLE_MAP.get(camera_angle, "front")
        
        # 构建强约束 Prompt
        consistency_prompt = (
            f"{identity}, {visual_anchor}, "
            f"{angle_desc}, "
            f"same character design, same outfit, same hairstyle, same facial features, "
            f"consistent appearance, {scene_action}"
        )
        
        return consistency_prompt
    
    def get_camera_angle_from_movement(self, camera_movement: str) -> str:
        """
        从相机运镜推断视角
        
        Args:
            camera_movement: 相机运镜类型
        
        Returns:
            视角类型 (front/back/left/right/three_quarter/close_up/full_body/side)
        """
        angle_map = {
            "STATIC": "full_body",
            "Z_DOLLY_IN": "close_up",
            "Z_DOLLY_OUT": "full_body",
            "PAN_LEFT": "side",
            "PAN_RIGHT": "side",
            "TILT_UP": "three_quarter",
            "TILT_DOWN": "three_quarter",
            "HANDHELD_SHAKE": "full_body",
            "STATIC_JITTER": "full_body",
            "ZOOM_IN": "close_up",
            "ZOOM_OUT": "full_body"
        }
        return angle_map.get(camera_movement, "full_body")
    
    def get_all_character_descriptions(self, character_names: List[str]) -> str:
        """
        获取多个角色的组合描述
        
        Args:
            character_names: 角色名称列表
        
        Returns:
            组合的角色描述
        """
        descriptions = []
        for name in character_names:
            desc = self.get_character_description(name)
            if desc:
                descriptions.append(desc)
        
        if descriptions:
            return f"characters: {' and '.join(descriptions)}"
        return ""
    
    def has_character_references(self, character_name: str) -> bool:
        """
        检查角色是否有可用的参考图
        
        Args:
            character_name: 角色名称
        
        Returns:
            是否有参考图
        """
        if character_name not in self.characters:
            return False
        
        directions = self.characters[character_name].get("directions", {})
        return len(directions) > 0
    
    def get_available_directions(self, character_name: str) -> List[str]:
        """
        获取角色可用的参考方向
        
        Args:
            character_name: 角色名称
        
        Returns:
            可用方向列表
        """
        if character_name not in self.characters:
            return []
        
        directions = self.characters[character_name].get("directions", {})
        return list(directions.keys())
    
    def get_character_summary(self, character_name: str) -> Dict:
        """
        获取角色完整摘要信息
        
        Args:
            character_name: 角色名称
        
        Returns:
            角色信息字典
        """
        if character_name not in self.characters:
            return {}
        
        char_data = self.characters[character_name].copy()
        # 添加可用方向信息
        char_data["available_directions"] = self.get_available_directions(character_name)
        char_data["has_reference"] = self.has_character_references(character_name)
        
        return char_data
    
    def export_character_references(self, output_dir: Path) -> Dict[str, Dict]:
        """
        导出所有角色参考图信息（供场景生成使用）
        
        Args:
            output_dir: 输出目录
        
        Returns:
            角色参考信息字典
        """
        export_data = {}
        
        for char_name, char_data in self.characters.items():
            directions = char_data.get("directions", {})
            ref_info = {
                "name": char_name,
                "identity": char_data.get("identity", ""),
                "visual_anchor": char_data.get("visual_anchor", ""),
                "directions": {},
                "available": len(directions) > 0
            }
            
            for dir_name, path_str in directions.items():
                path = Path(path_str)
                if path.exists():
                    ref_info["directions"][dir_name] = str(path)
            
            export_data[char_name] = ref_info
        
        # 保存导出文件
        export_path = output_dir / "character_references.json"
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 角色参考信息已导出: {export_path}")
        return export_data
    
    def import_character_references(self, import_path: Path) -> bool:
        """
        导入角色参考图信息
        
        Args:
            import_path: 导入文件路径
        
        Returns:
            是否成功
        """
        if not import_path.exists():
            return False
        
        with open(import_path, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        for char_name, ref_info in import_data.items():
            if char_name not in self.characters:
                self.characters[char_name] = {
                    "name": char_name,
                    "identity": ref_info.get("identity", ""),
                    "visual_anchor": ref_info.get("visual_anchor", ""),
                    "personality_traits": [],
                    "voice_profile": "",
                    "initial_state": {},
                    "directions": {}
                }
            
            for dir_name, path_str in ref_info.get("directions", {}).items():
                path = Path(path_str)
                if path.exists():
                    self.characters[char_name]["directions"][dir_name] = str(path)
        
        print(f"✅ 导入角色参考信息: {len(import_data)} 个角色")
        return True