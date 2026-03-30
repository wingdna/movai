# modules/visual_asset_foundry.py
"""
模块5：视觉资产铸造厂 (Visual_Asset_Foundry)
- 优先使用 HuggingFace 免费推理 API
- 备选 SiliconFlow Kolors API
- 使用 Depth-Anything-V2 生成深度图
- 支持异步请求和 429 限流重试
- 生成海报封面
"""
import json
import os
import sys
import time
import asyncio
import aiohttp
import requests
import base64
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
import traceback
import hashlib
import random
from PIL import Image
import io

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入配置
try:
    from config.settings import SILICONFLOW_API_KEY, SILICONFLOW_BASE_URL, HUGGINGFACE_API_KEY
except ImportError:
    from config.settings import SILICONFLOW_API_KEY, SILICONFLOW_BASE_URL
    HUGGINGFACE_API_KEY = None
    print("⚠️ HUGGINGFACE_API_KEY 未配置，将使用 SiliconFlow 作为备选")

# 错误日志文件路径
ERROR_LOG_FILE = Path(__file__).parent.parent / "data" / "error_log.json"

# 在 VisualAssetFoundry 类中添加角色资产管理器

from modules.character_asset_manager import CharacterAssetManager

class VisualAssetFoundry:
    # 图像尺寸配置
    IMAGE_SIZES = {
        "standard": {"width": 1920, "height": 1080},
        "poster": {"width": 1920, "height": 1080},
        "landscape": {"width": 1920, "height": 1080},
        "portrait": {"width": 720, "height": 1280},
    }    
    
    def __init__(self, script_path: str, output_dir: str = "./data/output", 
                 visuals_dir: str = "./data/output/visuals",
                 max_retries: int = 5):
        """
        初始化视觉资产铸造厂
        """
        self.script_path = Path(script_path)
        self.output_dir = Path(output_dir)
        self.visuals_dir = Path(visuals_dir)
        self.max_retries = max_retries
        
        # 创建目录
        self.visuals_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载剧本
        self.timed_script = self._load_script()
        
        # 初始化图像生成器
        self.image_generator = ImageGenerator()
        
        # 初始化深度图生成器
        self.depth_generator = DepthGenerator()  # 会自动查找本地模型
        
        # 图像尺寸
        self.image_width = 1920
        self.image_height = 1080
        
        # 速率限制
        self.last_generation_time = 0
        self.min_interval = 35
        
        # 初始化角色资产管理器（延迟初始化，不立即加载）
        self.character_asset_manager = None
        
        # 统计
        self.stats = {
            "total_scenes": 0,
            "images_generated": 0,
            "depth_maps_generated": 0,
            "depth_maps_real": 0,
            "depth_maps_fallback": 0,
            "failed": 0,
            "model_type": self.image_generator.active_model_type,
            "model_name": self.image_generator.active_model_name
        }
        
        print("\n" + "="*60)
        print("🎨 视觉资产铸造厂 初始化")
        print("="*60)
        print(f"📖 剧本：{self.script_path}")
        print(f"📁 视觉输出：{self.visuals_dir}")
        print(f"🤖 图像模型：{self.stats['model_type']} - {self.stats['model_name']}")
        print(f"🗺️ 深度图: 真实模型可用" if self.depth_generator.available else "🗺️ 深度图: 将使用降级方案")
        print(f"🔄 重试机制：最多 {max_retries} 次")
        print("="*60)
    
    def generate_character_references(self):
        """生成所有角色的四方向参考图"""
        print("\n" + "="*60)
        print("🎭 生成角色四方向参考图")
        print("="*60)
        
        # 检查角色管理器是否已初始化
        if self.character_asset_manager is None:
            from modules.character_asset_manager import CharacterAssetManager
            self.character_asset_manager = CharacterAssetManager()
        
        # 从项目圣经加载角色
        bible_path = self.output_dir / "project_bible.json"
        if not bible_path.exists():
            # 尝试从上级目录查找
            bible_path = Path(self.output_dir).parent / "output" / "project_bible.json"
        
        if bible_path.exists():
            characters = self.character_asset_manager.load_characters_from_bible(bible_path)
            print(f"📖 从圣经加载了 {len(characters)} 个角色")
        else:
            print(f"❌ 未找到 project_bible.json: {bible_path}")
            return
        
        if not self.character_asset_manager.characters:
            print("⚠️ 没有角色需要生成")
            return
        
        # 生成每个角色的四方向图
        for char_name, char_data in self.character_asset_manager.characters.items():
            print(f"\n🎨 处理角色: {char_name}")
            results = self.character_asset_manager.generate_character_directions(char_data)
            
            success_count = len([p for p in results.values() if p])
            print(f"   ✅ 完成 {success_count}/4 个方向")
        
        # 保存角色清单
        manifest_path = self.character_asset_manager.save_character_manifest()
        print(f"\n✅ 角色参考图生成完成")
        print(f"   📁 角色目录: {self.character_asset_manager.characters_dir}")
        print(f"   📄 角色清单: {manifest_path}")
    
    def _get_character_consistency_prompt(self, character_name: str, scene_action: str = "") -> str:
        """获取角色一致性 Prompt（安全版本）"""
        if self.character_asset_manager is None:
            return scene_action
        
        try:
            return self.character_asset_manager.get_character_consistency_prompt(character_name, scene_action)
        except Exception:
            return scene_action
    
    def _build_prompt_with_consistency(self, scene: Dict) -> Tuple[str, str]:
        """构建带角色一致性的 Prompt"""
        visual_action = scene.get("visual_action", "")
        
        # 获取场景中的角色
        character_anchors = []
        character_names = []
        
        for dialogue in scene.get("dialogues", []):
            character = dialogue.get("character", "")
            if character and character not in character_names:
                character_names.append(character)
                
                # 获取角色一致性 Prompt
                consistency_prompt = self._get_character_consistency_prompt(character, visual_action)
                if consistency_prompt and consistency_prompt != visual_action:
                    character_anchors.append(consistency_prompt)
        
        # 去重
        character_anchors = list(dict.fromkeys(character_anchors))
        
        # 构建完整 Prompt
        prompt_parts = []
        
        # 角色一致性约束（最重要）
        if character_anchors:
            prompt_parts.append(f"consistent character design: {' and '.join(character_anchors)}")
        
        # 视觉动作
        if visual_action:
            prompt_parts.append(visual_action)
        
        # 质量词
        quality_tags = ["8k", "photorealistic", "detailed", "dramatic lighting", "cinematic"]
        import random
        prompt_parts.extend(random.sample(quality_tags, min(3, len(quality_tags))))
        
        final_prompt = ", ".join(prompt_parts)
        negative_prompt = "different character, inconsistent features, wrong outfit, blurry, low quality, watermark"
        
        return final_prompt, negative_prompt
    
    def _load_script(self) -> Dict:
        """加载剧本"""
        if not self.script_path.exists():
            raise FileNotFoundError(f"剧本文件不存在：{self.script_path}")
        with open(self.script_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _wait_for_rate_limit(self):
        """速率限制等待"""
        current_time = time.time()
        time_since_last = current_time - self.last_generation_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            print(f"      ⏸️ 速率限制，等待 {wait_time:.1f} 秒...")
            time.sleep(wait_time)
        
        self.last_generation_time = time.time()
    
    def _save_image(self, image_data: str, output_path: Path) -> bool:
        """保存图像"""
        try:
            if image_data.startswith("http"):
                response = requests.get(image_data, timeout=30)
                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    return True
            else:
                image_bytes = base64.b64decode(image_data)
                with open(output_path, 'wb') as f:
                    f.write(image_bytes)
                return True
            return False
        except Exception as e:
            print(f"      ❌ 保存图像失败：{e}")
            return False
    
    def _generate_fallback_depth(self, rgb_path: Path, depth_path: Path) -> bool:
        """降级方案：生成径向渐变深度图"""
        try:
            from PIL import Image
            img = Image.open(rgb_path)
            width, height = img.size

            y, x = np.ogrid[:height, :width]
            center_y, center_x = height / 2, width / 2
            distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
            max_distance = np.sqrt(center_x**2 + center_y**2)
            depth = 1 - (distance / max_distance)
            depth = (depth * 255).astype(np.uint8)

            depth_img = Image.fromarray(depth, mode='L')
            depth_img.save(depth_path)
            return True
        except Exception as e:
            print(f"      ❌ 降级深度图生成失败: {e}")
            return False
    
    def _build_prompt(self, scene: Dict, is_outdoor: bool = True, is_epic: bool = True) -> Tuple[str, str]:
        """构建史诗级图像生成 Prompt - 黑暗惊悚版"""
        visual_action = scene.get("visual_action", "")
        
         # 获取场景中的相机角度（从 camera_movement 推断）
        camera = scene.get("camera_movement", "STATIC")
        camera_angle = self._get_camera_angle(camera)
        
        # ========== 核心：角色一致性约束 ==========
        character_descriptions = []
        character_names = []
        
        for dialogue in scene.get("dialogues", []):
            character = dialogue.get("character", "")
            # 从角色库中查找该角色的视觉锚点
            for char in self.timed_script.get("characters", []):
                if char.get("name") == character:
                    visual_anchor = char.get("visual_anchor", "")
                    identity = char.get("identity", "")
                    if visual_anchor:
                        # 直接使用已有的角色特征描述
                        character_descriptions.append(f"{identity}, {visual_anchor}")
                    break  
        # 去重
        character_descriptions = list(dict.fromkeys(character_descriptions))
        
        # 光影效果关键词
        lighting_keywords = [
            "dramatic lighting", "chiaroscuro", "volumetric lighting", "god rays",
            "crepuscular rays", "rim lighting", "backlight", "golden hour",
            "blue hour", "low key lighting", "high contrast", "deep shadows",
            "soft shadows", "ambient occlusion", "specular highlights",
            "lens flare", "bokeh", "cinematic lighting", "moody lighting"
        ]
        
        # 纹理细节关键词
        texture_keywords = [
            "intricate details", "fine texture", "highly detailed", "hyperrealistic",
            "photorealistic", "sharp focus", "crisp details", "surface detail",
            "micro details", "rich texture", "complex patterns", "fine grain",
            "detailed skin texture", "material fidelity", "subsurface scattering"
        ]
        
        # 黑暗惊悚风格关键词
        dark_keywords = [
            "dark atmosphere", "ominous lighting", "shadowy", "gloomy",
            "low key lighting", "deep shadows", "moody", "eerie",
            "foreboding", "sinister", "dark and gritty", "bleak",
            "cold color palette", "desaturated", "storm clouds", "overcast sky"
        ]
        
        # 太空歌剧风格关键词
        space_opera_keywords = [
            "epic scale", "vast landscape", "sweeping vista", "cosmic grandeur",
            "alien horizon", "distant mountains", "sense of wonder", "solitude",
            "cinematic wide shot", "ultra wide angle"
        ]
        
        # 室外场景引导词（黑暗版）
        outdoor_keywords = [
            "alien horizon at dusk", "distant mountains in shadow", "vast dark plain",
            "storm clouds gathering", "under alien twilight sky", "dark wasteland"
        ]
        
        # 随机选择关键词
        selected_dark = random.sample(dark_keywords, min(4, len(dark_keywords)))
        selected_epic = random.sample(space_opera_keywords, min(3, len(space_opera_keywords)))
        selected_outdoor = random.sample(outdoor_keywords, min(2, len(outdoor_keywords)))
        selected_lighting = random.sample(lighting_keywords, min(3, len(lighting_keywords)))
        selected_texture = random.sample(texture_keywords, min(3, len(texture_keywords)))                
        
        prompt_parts = [
            "epic wide shot, cinematic composition, ultra wide angle lens",
            *selected_dark,
            *selected_lighting,
            *selected_texture,
            *selected_epic,
            *selected_outdoor
        ]
        
         # 【核心】添加角色特征描述（直接从剧本中获取，不额外调用API）
        if character_descriptions:
            prompt_parts.append(f"characters: {' and '.join(character_descriptions)}")
            
        
        # 室外场景特殊处理
        if is_outdoor:
            outdoor_lighting = [
                "dramatic sky", "cloud shadows", "sun rays through clouds",
                "atmospheric perspective", "distant haze"
            ]
            prompt_parts.append(random.choice(outdoor_lighting))
        
        # 视觉动作
        if visual_action:
            prompt_parts.append(visual_action)
        
        # 质量提示词
        quality_tags = [
            "8k resolution", "masterpiece", "best quality", "ultra detailed",
            "sharp focus", "crisp details", "highly detailed", "photorealistic"
        ]
        prompt_parts.extend(random.sample(quality_tags, 4))
        
        final_prompt = ", ".join(prompt_parts)
        
        # 增强版负面提示词
        negative_prompt = (
             "different character, inconsistent features, wrong outfit, different hairstyle, "
            "different face, multiple characters, blurry, low quality, pixelated, "
            "watermark, text, signature, bright, sunny, colorful, vibrant, "
            "cartoon, anime, illustration, sketch, drawing,"
            "blurry, low quality, jpeg artifacts, pixelated, distorted, ugly, "
            "bad anatomy, extra limbs, missing fingers, watermark, text, signature, "
            "oversaturated, underexposed, flat lighting, no shadows, "
            "cartoon, anime, illustration, painting, sketch, drawing, "
            "bright, sunny, cheerful, colorful, vibrant"            
        )
        
        print(f"      🎨 增强光影/纹理 Prompt 构建完成")
        print(f"      💡 光影关键词: {len(selected_lighting)} 个")
        print(f"      🔍 纹理关键词: {len(selected_texture)} 个")
        
        return final_prompt, negative_prompt
    
    def _get_camera_angle(self, camera_movement: str) -> str:
        """根据相机运镜推断视角"""
        angle_map = {
            "STATIC": "full_body",
            "Z_DOLLY_IN": "close_up",
            "Z_DOLLY_OUT": "full_body",
            "PAN_LEFT": "side",
            "PAN_RIGHT": "side",
            "TILT_UP": "three_quarter",
            "TILT_DOWN": "three_quarter",
            "HANDHELD_SHAKE": "full_body",
            "STATIC_JITTER": "full_body"
        }
        return angle_map.get(camera_movement, "full_body")
    
    def generate_scene_image_only(self, scene: Dict, scene_idx: int) -> Optional[Path]:
        """只生成 RGB 图像"""
        print(f"\n   🎨 生成场景 {scene_idx} RGB 图像...")
        
        # 速率限制
        self._wait_for_rate_limit()
        
        # 构建 Prompt
        prompt, negative_prompt = self._build_prompt(scene)
        print(f"      📝 Prompt: {prompt[:120]}...")
        
        # 调用 API 生成图像
        images = self.image_generator.generate_image(
            prompt, negative_prompt,
            width=self.image_width,
            height=self.image_height,
            num_images=1,
            max_retries=self.max_retries
        )
        
        if not images:
            print(f"      ❌ 图像生成失败")
            self.stats["failed"] += 1
            return None
        
        # 保存 RGB 图像
        rgb_path = self.visuals_dir / f"scene_{scene_idx:03d}_rgb.png"
        if not self._save_image(images[0], rgb_path):
            print(f"      ❌ 图像保存失败")
            return None
        
        print(f"      ✅ RGB 图像已保存")
        self.stats["images_generated"] += 1
        
        return rgb_path
    
    def generate_depth_for_scene(self, rgb_path: Path, scene_idx: int) -> Optional[Path]:
        """为已存在的 RGB 图像生成深度图"""
        print(f"\n   🗺️ 为场景 {scene_idx} 生成深度图...")
        
        depth_path = self.visuals_dir / f"scene_{scene_idx:03d}_depth.png"
        
        # 使用真实深度图模型
        if self.depth_generator.available:
            success = self.depth_generator.generate_depth(rgb_path, depth_path)
            if success:
                self.stats["depth_maps_generated"] += 1
                self.stats["depth_maps_real"] += 1
                print(f"      ✅ 真实深度图已保存")
                return depth_path
            else:
                print(f"      ⚠️ 真实深度图失败，使用降级方案")
        
        # 降级方案
        if self._generate_fallback_depth(rgb_path, depth_path):
            self.stats["depth_maps_generated"] += 1
            self.stats["depth_maps_fallback"] += 1
            print(f"      📦 使用降级深度图")
            return depth_path
        
        print(f"      ❌ 深度图生成失败")
        return None
    
    def generate_poster(self) -> Optional[Path]:
        """生成海报封面"""
        print("\n" + "="*60)
        print("🎬 生成海报封面")
        print("="*60)
        
        scenes = self.timed_script.get("scenes", [])
        if scenes:
            climax_scene = max(scenes, key=lambda s: s.get("emotion_intensity", 0))
            prompt, negative_prompt = self._build_prompt(climax_scene)
        else:
            project_name = self.timed_script.get("project_name", "幻影卷轴")
            style = self.timed_script.get("style", "科幻")
            prompt = f"cinematic movie poster for '{project_name}', {style} style, epic composition, dramatic lighting"
            negative_prompt = "text, watermark, low quality"
        
        print(f"   📝 Prompt: {prompt[:100]}...")
        
        images = self.image_generator.generate_image(
            prompt, negative_prompt,
            width=self.IMAGE_SIZES["poster"]["width"],
            height=self.IMAGE_SIZES["poster"]["height"],
            num_images=1,
            max_retries=self.max_retries
        )
        
        if not images:
            print(f"   ❌ 海报生成失败")
            return None
        
        poster_path = self.visuals_dir / "raw_poster.png"
        if self._save_image(images[0], poster_path):
            print(f"   ✅ 海报已保存")
            return poster_path
        
        return None
    
    def run(self) -> Tuple[Path, Optional[Path]]:
        """运行视觉资产铸造厂"""
        print("\n" + "="*60)
        print("🎨 模块5：视觉资产铸造厂 启动")
        print("="*60)
        
        scenes = self.timed_script.get("scenes", [])
        self.stats["total_scenes"] = len(scenes)
        print(f"📖 共 {len(scenes)} 个场景需要生成图像\n")
        
        # 第一阶段：生成所有 RGB 图像
        print("\n" + "="*60)
        print("📸 第一阶段：生成所有 RGB 图像")
        print("="*60)
        
        for idx, scene in enumerate(scenes, 1):
            try:
                rgb_path = self.generate_scene_image_only(scene, idx)
                scene["rgb_image"] = str(rgb_path) if rgb_path else None
            except Exception as e:
                print(f"   ❌ 场景 {idx} RGB 生成失败: {e}")
                traceback.print_exc()
                self.stats["failed"] += 1
        
        print(f"\n✅ RGB 图像生成完成: {self.stats['images_generated']}/{self.stats['total_scenes']}")
        
        # 第二阶段：生成所有深度图
        print("\n" + "="*60)
        print("🗺️ 第二阶段：生成所有深度图")
        print("="*60)
        
        for idx, scene in enumerate(scenes, 1):
            rgb_path = scene.get("rgb_image")
            if not rgb_path or not Path(rgb_path).exists():
                print(f"   ⚠️ 场景 {idx} 没有 RGB 图像，跳过深度图")
                continue
            
            try:
                depth_path = self.generate_depth_for_scene(Path(rgb_path), idx)
                scene["depth_map"] = str(depth_path) if depth_path else None
            except Exception as e:
                print(f"   ❌ 场景 {idx} 深度图生成失败: {e}")
                self.stats["failed"] += 1
        
        print(f"\n✅ 深度图生成完成: {self.stats['depth_maps_generated']}/{self.stats['total_scenes']}")
        
        # 第三阶段：生成海报
        poster_path = self.generate_poster()
        
        # 更新剧本数据
        self.timed_script["visual_metadata"] = {
            "generated_at": datetime.now().isoformat(),
            "visuals_dir": str(self.visuals_dir),
            "stats": self.stats,
            "poster": str(poster_path) if poster_path else None,
            "model_used": {
                "type": self.stats["model_type"],
                "name": self.stats["model_name"]
            }
        }
        
        # 保存更新的剧本
        output_path = self.output_dir / "timed_script.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.timed_script, f, ensure_ascii=False, indent=2)
        
        # 打印统计
        print("\n" + "="*60)
        print("📊 视觉资产生成统计")
        print("="*60)
        print(f"总场景数: {self.stats['total_scenes']}")
        print(f"图像生成: {self.stats['images_generated']}")
        print(f"深度图生成: {self.stats['depth_maps_generated']}")
        print(f"  - 真实深度图: {self.stats['depth_maps_real']}")
        print(f"  - 降级深度图: {self.stats['depth_maps_fallback']}")
        print(f"失败数量: {self.stats['failed']}")
        print(f"使用模型: {self.stats['model_type']} - {self.stats['model_name']}")        
        if poster_path:
            print(f"📸 海报: {poster_path.name}")
        
        print(f"\n✅ 视觉资产铸造厂完成")
        print(f"   📁 输出目录: {self.visuals_dir}")
        
        return self.visuals_dir, poster_path    

class DepthGenerator:
    """本地深度图生成器 - 使用本地 Depth-Anything-V2 模型"""
    
    def __init__(self, model_path: str = None):
        """
        初始化深度图生成器
        
        Args:
            model_path: 本地模型路径，默认使用项目目录下的模型
        """
        self.model = None
        self.processor = None
        self.device = None
        self.available = False
        
        # 查找本地模型路径
        if model_path is None:
            # 尝试多个可能的路径
            possible_paths = [
                r"F:\scd\render\ai_models\Depth-Anything-V2-Small-hf",
                Path(__file__).parent.parent / "models" / "Depth-Anything-V2-Small-hf",
                Path(__file__).parent.parent / "models" / "depth_anything_v2",
            ]
            for path in possible_paths:
                if Path(path).exists():
                    model_path = str(path)
                    break
        
        if model_path and Path(model_path).exists():
            self._load_model(model_path)
        else:
            print(f"      ⚠️ 未找到本地深度图模型，将使用降级方案")
            print(f"      💡 请将模型放在: {possible_paths[0]}")
    
    def _load_model(self, model_path: str):
        """加载本地深度图模型"""
        try:
            import torch
            from transformers import pipeline, AutoImageProcessor, AutoConfig, AutoModelForDepthEstimation
            
            print(f"      🚀 正在加载本地深度图模型: {model_path}")
            
            # 检测设备
            self.device = 0 if torch.cuda.is_available() else -1
            hardware = 'GPU (CUDA)' if self.device == 0 else 'CPU'
            print(f"      ⚙️ 算力引擎: {hardware}")
            
            # 加载配置并修复
            config = AutoConfig.from_pretrained(model_path)
            
            # 修复配置（解决 12!=4 报错）
            if hasattr(config, "backbone_config"):
                config.backbone_config.out_indices = [2, 5, 8, 11]
                config.backbone_config.reshape_hidden_states = False
            
            if hasattr(config, "reshape_hidden_states"):
                config.reshape_hidden_states = False
            
            # 加载模型
            self.model = AutoModelForDepthEstimation.from_pretrained(
                model_path, 
                config=config
            )
            
            # 加载图像处理器
            self.processor = AutoImageProcessor.from_pretrained(
                model_path, 
                backend="torchvision"
            )
            
            # 移动到设备
            if self.device == 0:
                self.model = self.model.cuda()
            
            self.model.eval()
            self.available = True
            print(f"      ✅ 本地深度图模型加载成功")
            
        except Exception as e:
            print(f"      ❌ 模型加载失败: {e}")
            self.available = False
    
    def generate_depth(self, rgb_image_path: Path, depth_output_path: Path) -> bool:
        """
        生成深度图
        
        Args:
            rgb_image_path: RGB 图像路径
            depth_output_path: 深度图输出路径
        
        Returns:
            是否成功
        """
        if not self.available:
            return self._generate_fallback_depth(rgb_image_path, depth_output_path)
        
        try:
            from PIL import Image
            import torch
            
            # 读取图像
            image = Image.open(rgb_image_path).convert('RGB')
            
            # 预处理
            inputs = self.processor(images=image, return_tensors="pt")
            
            # 移动到设备
            if self.device == 0:
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # 推理
            with torch.no_grad():
                outputs = self.model(**inputs)
                depth = outputs.predicted_depth
            
            # 后处理
            depth = depth.squeeze().cpu().numpy()
            
            # 归一化到 0-255
            depth_min = depth.min()
            depth_max = depth.max()
            if depth_max - depth_min > 1e-6:
                depth_normalized = (depth - depth_min) / (depth_max - depth_min) * 255
            else:
                depth_normalized = depth * 255
            
            depth_img = Image.fromarray(depth_normalized.astype('uint8'), mode='L')
            depth_img.save(depth_output_path)
            
            print(f"      ✅ 深度图已生成")
            return True
            
        except Exception as e:
            print(f"      ❌ 深度图生成失败: {e}")
            return self._generate_fallback_depth(rgb_image_path, depth_output_path)
    
    def _generate_fallback_depth(self, rgb_path: Path, depth_path: Path) -> bool:
        """降级方案：本地增强深度图"""
        try:
            from PIL import Image, ImageFilter
            import numpy as np
            from scipy.ndimage import gaussian_filter, sobel
            
            img = Image.open(rgb_path)
            width, height = img.size
            gray = np.array(img.convert('L')).astype(np.float32)
            
            # 边缘检测深度
            sobel_x = sobel(gray, axis=0)
            sobel_y = sobel(gray, axis=1)
            edge_magnitude = np.hypot(sobel_x, sobel_y)
            edge_magnitude = edge_magnitude / (edge_magnitude.max() + 1e-6)
            edge_depth = 1 - edge_magnitude
            
            # 亮度深度
            brightness_depth = gray / 255.0
            
            # 径向深度
            y, x = np.ogrid[:height, :width]
            center_y, center_x = height / 2, width / 2
            distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
            max_distance = np.sqrt(center_x**2 + center_y**2)
            radial_depth = 1 - (distance / max_distance)
            
            # 融合
            depth_map = 0.4 * edge_depth + 0.3 * brightness_depth + 0.3 * radial_depth
            
            # 平滑
            depth_map = gaussian_filter(depth_map, sigma=1.5)
            depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min() + 1e-6)
            depth_map = (depth_map * 255).astype(np.uint8)
            
            depth_img = Image.fromarray(depth_map, mode='L')
            depth_img = depth_img.filter(ImageFilter.UnsharpMask(radius=1, percent=50, threshold=0))
            depth_img.save(depth_path)
            
            print(f"      📦 使用增强本地深度图")
            return True
            
        except Exception as e:
            print(f"      ❌ 降级深度图失败: {e}")
            return False
         
class ImageGenerator:
    """智能图像生成器 - 支持自动降级和错误记录"""
    
    # 模型优先级列表（按推荐顺序）
    # 第一顺位：HuggingFace FLUX 模型
    # 其次：HuggingFace 其他可用模型
    # 最后：硅基流动可图 (Kolors)
    MODEL_ROUTER = [
        {
            "name": "FLUX.1-schnell",
            "path": "black-forest-labs/FLUX.1-schnell",
            "type": "huggingface",
            "priority": 1,
            "description": "FLUX 快速版 - 最佳细节和真实感",
            "params": {
                "num_inference_steps": 4,
                "guidance_scale": 3.5,
            }
        },
        {
            "name": "SDXL",
            "path": "stabilityai/stable-diffusion-xl-base-1.0",
            "type": "huggingface",
            "priority": 2,
            "description": "SDXL - 高质量通用模型",
            "params": {
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
            }
        },
        {
            "name": "Realistic Vision",
            "path": "SG161222/Realistic_Vision_V5.1_noVAE",
            "type": "huggingface",
            "priority": 3,
            "description": "Realistic Vision - 真实感人像",
            "params": {
                "num_inference_steps": 25,
                "guidance_scale": 7.0,
            }
        },
        {
            "name": "DreamShaper XL",
            "path": "dreamshaper/dreamshaper-xl-1-0",
            "type": "huggingface",
            "priority": 4,
            "description": "DreamShaper - 艺术风格",
            "params": {
                "num_inference_steps": 25,
                "guidance_scale": 7.0,
            }
        },
        {
            "name": "OpenJourney",
            "path": "prompthero/openjourney-v4",
            "type": "huggingface",
            "priority": 5,
            "description": "OpenJourney - 艺术插画风格",
            "params": {
                "num_inference_steps": 25,
                "guidance_scale": 7.0,
            }
        },
        {
            "name": "Animagine XL",
            "path": "cagliostrolab/animagine-xl-3.1",
            "type": "huggingface",
            "priority": 6,
            "description": "Animagine - 动漫风格",
            "params": {
                "num_inference_steps": 28,
                "guidance_scale": 7.0,
            }
        },
        {
            "name": "Kolors",
            "path": "Kwai-Kolors/Kolors",
            "type": "siliconflow",
            "priority": 7,
            "description": "快手可图 - 硅基流动备选方案",
            "params": {
                "num_inference_steps": 50,
                "guidance_scale": 7.5,
            }
        }
    ]
    
    def __init__(self, hf_api_key: str = None, siliconflow_api_key: str = None):
        self.hf_api_key = hf_api_key or HUGGINGFACE_API_KEY
        self.siliconflow_api_key = siliconflow_api_key or SILICONFLOW_API_KEY
        
        if self.hf_api_key:
            self.hf_api_key = "".join(c for c in self.hf_api_key if ord(c) < 128).strip()
        if self.siliconflow_api_key:
            self.siliconflow_api_key = self.siliconflow_api_key.strip()
        
        # 当前激活的模型
        self.active_model = None
        self.active_model_config = None
        self.active_model_type = None
        self.active_model_name = None
        
        # 可用模型列表（每次生成前刷新）
        self.available_models = []
        
        # 加载今日错误记录
        self.today_errors = self._load_today_errors()
        
        # 初始化时检测一次
        self._refresh_available_models()
    
    def _load_today_errors(self) -> Dict:
        """加载今日错误记录"""
        today_str = date.today().isoformat()
        default = {"date": today_str, "errors": {}}
        
        if ERROR_LOG_FILE.exists():
            try:
                with open(ERROR_LOG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("date") == today_str:
                        return data
            except:
                pass
        
        return default
    
    def _reload_errors(self):
        """重新加载错误记录（每天刷新）"""
        today_str = date.today().isoformat()
        if self.today_errors["date"] != today_str:
            self.today_errors = self._load_today_errors()
            self._refresh_available_models()
            print(f"      📅 新的一天，已重置错误记录")
    
    def _is_model_blocked(self, model_name: str) -> bool:
        """检查模型是否被今日错误阻塞"""
        self._reload_errors()  # 每次检查前刷新
        
        if model_name not in self.today_errors["errors"]:
            return False
        
        errors = self.today_errors["errors"][model_name]
        # 402(支付问题) 或 429(限流) 阻塞当天
        if 402 in errors or 429 in errors:
            return True
        
        # 连续失败3次也阻塞
        if len(errors) >= 3:
            return True
        
        return False
    
    def _refresh_available_models(self):
        """刷新可用模型列表（跳过今日已阻塞的）"""
        self.available_models = []
        
        for model in self.MODEL_ROUTER:
            if self._is_model_blocked(model["name"]):
                continue
            
            if model["type"] == "huggingface":
                if self._test_hf_model(model["path"]):
                    self.available_models.append(model)
            elif model["type"] == "siliconflow":
                if self._test_kolors_model():
                    self.available_models.append(model)
        
        if self.available_models:
            first = self.available_models[0]
            self.active_model = first["path"]
            self.active_model_config = first
            self.active_model_type = first["type"]
            self.active_model_name = first["name"]
    
    def _test_hf_model(self, model_path: str) -> bool:
        """测试 HuggingFace 模型是否可用"""
        if not self.hf_api_key:
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.hf_api_key}"}
            api_url = f"https://router.huggingface.co/hf-inference/models/{model_path}"
            response = requests.head(api_url, headers=headers, timeout=5)
            return response.status_code in [200, 302, 405]
        except Exception:
            return False
    
    def _test_kolors_model(self) -> bool:
        """测试 Kolors 模型是否可用"""
        return bool(self.siliconflow_api_key)
    
    def generate_image(self, prompt: str, negative_prompt: str = "",
                       width: int = 1920, height: int = 1080,
                       num_images: int = 1,
                       max_retries: int = 3) -> Optional[List[str]]:
        """生成图像 - 每次调用前刷新可用模型列表"""
        # 【关键修复】每次生成前刷新可用模型（跳过今日已阻塞的）
        self._refresh_available_models()
        
        if not self.available_models:
            print(f"      ❌ 没有可用的图像生成模型（今日所有模型均已失败）")
            return None
        
        # 尝试所有可用模型
        for model_idx, model_config in enumerate(self.available_models):
            # 设置当前激活模型
            self.active_model = model_config["path"]
            self.active_model_config = model_config
            self.active_model_type = model_config["type"]
            self.active_model_name = model_config["name"]
            
            print(f"\n      🚀 尝试模型 {model_idx+1}/{len(self.available_models)}: {model_config['name']}")
            
            # 根据类型调用
            if model_config["type"] == "huggingface":
                result = self._generate_with_hf(
                    prompt, negative_prompt, width, height, num_images, max_retries
                )
            else:
                result = self._generate_with_kolors(
                    prompt, negative_prompt, width, height, num_images, max_retries
                )
            
            # 如果成功，返回结果
            if result:
                return result
            
            # 失败，继续下一个模型
            print(f"      ⚠️ {model_config['name']} 失败，尝试下一个模型...")
        
        print(f"      ❌ 所有可用模型均失败")
        return None
    
    def _save_error(self, model_name: str, error_code: int):
        """保存错误记录"""
        today_str = date.today().isoformat()
        
        if self.today_errors["date"] != today_str:
            self.today_errors = {"date": today_str, "errors": {}}
        
        if model_name not in self.today_errors["errors"]:
            self.today_errors["errors"][model_name] = []
        
        if error_code not in self.today_errors["errors"][model_name]:
            self.today_errors["errors"][model_name].append(error_code)
        
        try:
            ERROR_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(ERROR_LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.today_errors, f, ensure_ascii=False, indent=2)
        except:
            pass
        
        # 记录后立即刷新可用模型列表
        self._refresh_available_models()
        
    def _generate_with_hf(self, prompt: str, negative_prompt: str,
                          width: int, height: int, num_images: int,
                          max_retries: int) -> Optional[List[str]]:
        """
        使用 HuggingFace Router API 生成图像
        """
        if not self.hf_api_key:
            return None
        
        headers = {
            "Authorization": f"Bearer {self.hf_api_key}",
            "Content-Type": "application/json"
        }
        
        # 使用 router 地址
        api_url = f"https://router.huggingface.co/hf-inference/models/{self.active_model}"
        
        # 获取模型参数
        params = self.active_model_config.get("params", {})
        
        # 确保宽高是 16 的倍数
        width = ((width // 16) * 16)
        height = ((height // 16) * 16)
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "width": width,
                "height": height,
                "num_inference_steps": params.get("num_inference_steps", 25),
                "guidance_scale": params.get("guidance_scale", 7.0),
            }
        }
        
        # 添加负面提示词（如果模型支持）
        if negative_prompt and "FLUX" not in self.active_model:
            payload["parameters"]["negative_prompt"] = negative_prompt
        
        print(f"      📐 尺寸：{width}x{height} | 步数：{params.get('num_inference_steps', 25)}")
        
        for attempt in range(max_retries):
            try:
                response = requests.post(api_url, headers=headers, json=payload, timeout=120)
                
                if response.status_code == 200:
                    image_bytes = response.content
                    b64_image = base64.b64encode(image_bytes).decode('utf-8')
                    return [b64_image]
                
                # 记录需要阻塞的错误（402 支付问题，429 限流）
                if response.status_code in [402, 429]:
                    self._save_error(self.active_model_name, response.status_code)
                    print(f"      ⚠️ 错误码 {response.status_code}，今日将不再使用此模型")
                    return None
                
                elif response.status_code == 401:
                    print(f"      ❌ API Key 无效")
                    return None
                
                elif response.status_code == 503:
                    wait_time = 10 * (attempt + 1)
                    print(f"      ⏳ 模型加载中，等待 {wait_time} 秒...")
                    time.sleep(wait_time)
                    continue
                
                else:
                    error_msg = response.text[:200]
                    print(f"      ❌ API 错误：{response.status_code}")
                    if attempt < max_retries - 1:
                        print(f"      ⚠️ 重试 {attempt + 1}/{max_retries}...")
                        time.sleep(5)
                        continue
                    return None
                    
            except Exception as e:
                print(f"      ❌ 请求失败：{e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                return None
        
        return None
    
    def _generate_with_kolors(self, prompt: str, negative_prompt: str,
                               width: int, height: int, num_images: int,
                               max_retries: int) -> Optional[List[str]]:
        """
        使用 SiliconFlow Kolors API 生成图像 - 极限精细版
        - 步数最大化（50-80步）
        - 自动计时 + 动态暂停
        """
        if not self.siliconflow_api_key:
            return None
        
        # SiliconFlow Kolors API 地址
        url = "https://api.siliconflow.cn/v1/images/generations"
        
        # 确保宽高是 16 的倍数
        width = ((width // 16) * 16)
        height = ((height // 16) * 16)
        
        # ========== 极限精细参数 ==========
        # 步数：50步（极限精细，约需要60-90秒）
        num_steps = 50
        
        # 引导比例：提高以更严格遵循 Prompt
        guidance_scale = 6.5
        
        # 采样器：使用高质量采样器
        scheduler = "dpm++_2m_sde"  # DPM++ 2M 多步采样器，质量更高
        
        payload = {
            "model": "Kwai-Kolors/Kolors",
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "num_images": 4,
            "seed": random.randint(0, 2**32 - 1),
            "num_inference_steps": num_steps,
            "guidance_scale": guidance_scale,
            "scheduler": scheduler,
            # 额外精细参数
            "strength": 0.85,
            "clip_skip": 2,              # 跳过 CLIP 层，增加多样性
        }
        
        headers = {
            "Authorization": f"Bearer {self.siliconflow_api_key}",
            "Content-Type": "application/json"
        }
        
        print(f"      📐 尺寸: {width}x{height}")
        print(f"      🎨 步数: {num_steps} (极限精细模式)")
        print(f"      🎭 引导强度: {guidance_scale}")
        print(f"      ⏱️ 预计时间: {num_steps * 1.2:.0f} 秒")
        
        # 记录开始时间
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=180)
                
                # 计算生成时间
                elapsed_time = time.time() - start_time
                print(f"      ⏱️ 生成耗时: {elapsed_time:.1f} 秒")
                
                if response.status_code == 200:
                    data = response.json()
                    images = data.get("data", [])
                    if images:
                        img_data = images[0]
                        result = None
                        if "b64_json" in img_data:
                            result = [img_data["b64_json"]]
                        elif "url" in img_data:
                            img_response = requests.get(img_data["url"], timeout=60)
                            if img_response.status_code == 200:
                                result = [base64.b64encode(img_response.content).decode('utf-8')]
                        
                        # 如果生成时间少于 30 秒，主动等待（避免限流）
                        if elapsed_time < 30:
                            wait_time = 30 - elapsed_time
                            print(f"      ⏸️ 生成太快 ({elapsed_time:.0f}秒)，主动等待 {wait_time:.0f} 秒...")
                            time.sleep(wait_time)
                        
                        return result
                    return None
                
                elif response.status_code == 429:
                    # 限流 - 等待更长时间
                    wait_time = min(180, 45 * (2 ** attempt))
                    print(f"      ⚠️ 限流，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                
                else:
                    error_text = response.text[:200]
                    print(f"      ❌ API 错误 {response.status_code}: {error_text}")
                    if attempt < max_retries - 1:
                        wait_time = 15 * (attempt + 1)
                        time.sleep(wait_time)
                        continue
                    return None
                    
            except requests.exceptions.Timeout:
                print(f"      ⚠️ 请求超时，重试 {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(15)
                    continue
                return None
            except Exception as e:
                print(f"      ❌ 请求失败: {e}")
                if attempt < max_retries - 1:
                    time.sleep(15)
                    continue
                return None
        
        return None
        
        


# 异步版本
class AsyncVisualAssetFoundry(VisualAssetFoundry):
    """异步版本的视觉资产铸造厂"""
    
    def __init__(self, script_path: str, output_dir: str = "./data/output", 
                 visuals_dir: str = "./data/output/visuals",
                 max_retries: int = 5):
        """初始化异步版本"""
        super().__init__(script_path, output_dir, visuals_dir, max_retries)
    
    async def run_async(self) -> Tuple[Path, Optional[Path]]:
        """异步运行"""
        print("\n" + "="*60)
        print("🎨 模块5：视觉资产铸造厂 (异步模式) 启动")
        print("="*60)
        
        scenes = self.timed_script.get("scenes", [])
        self.stats["total_scenes"] = len(scenes)
        print(f"📖 共 {len(scenes)} 个场景需要生成图像\n")
        
        loop = asyncio.get_event_loop()
        
        # 第一阶段：生成所有 RGB 图像
        print("\n" + "="*60)
        print("📸 第一阶段：生成所有 RGB 图像")
        print("="*60)
        
        for idx, scene in enumerate(scenes, 1):
            try:
                rgb_path = await loop.run_in_executor(
                    None, self.generate_scene_image_only, scene, idx
                )
                scene["rgb_image"] = str(rgb_path) if rgb_path else None
            except Exception as e:
                print(f"   ❌ 场景 {idx} RGB 生成失败: {e}")
                self.stats["failed"] += 1
        
        print(f"\n✅ RGB 图像生成完成: {self.stats['images_generated']}/{self.stats['total_scenes']}")
        
        # 第二阶段：生成所有深度图
        print("\n" + "="*60)
        print("🗺️ 第二阶段：生成所有深度图")
        print("="*60)
        
        for idx, scene in enumerate(scenes, 1):
            rgb_path = scene.get("rgb_image")
            if not rgb_path or not Path(rgb_path).exists():
                print(f"   ⚠️ 场景 {idx} 没有 RGB 图像，跳过深度图")
                continue
            
            try:
                depth_path = await loop.run_in_executor(
                    None, self.generate_depth_for_scene, Path(rgb_path), idx
                )
                scene["depth_map"] = str(depth_path) if depth_path else None
            except Exception as e:
                print(f"   ❌ 场景 {idx} 深度图生成失败: {e}")
                self.stats["failed"] += 1
        
        print(f"\n✅ 深度图生成完成: {self.stats['depth_maps_generated']}/{self.stats['total_scenes']}")
        
        # 第三阶段：生成海报
        poster_path = self.generate_poster()
        
        # 更新剧本
        self.timed_script["visual_metadata"] = {
            "generated_at": datetime.now().isoformat(),
            "visuals_dir": str(self.visuals_dir),
            "stats": self.stats,
            "poster": str(poster_path) if poster_path else None,
            "model_used": {
                "type": self.stats["model_type"],
                "name": self.stats["model_name"]
            }
        }
        
        output_path = self.output_dir / "timed_script.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.timed_script, f, ensure_ascii=False, indent=2)
        
        print("\n" + "="*60)
        print("📊 视觉资产生成统计")
        print("="*60)
        print(f"图像生成: {self.stats['images_generated']}")
        print(f"深度图生成: {self.stats['depth_maps_generated']}")
        print(f"  - 真实深度图: {self.stats['depth_maps_real']}")
        print(f"  - 降级深度图: {self.stats['depth_maps_fallback']}")
        print(f"失败数量: {self.stats['failed']}")
        print(f"使用模型: {self.stats['model_type']} - {self.stats['model_name']}")
        
        return self.visuals_dir, poster_path

# 命令行入口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="视觉资产铸造厂")
    parser.add_argument("--script", default="./data/output/timed_script.json", help="timed_script.json 路径")
    parser.add_argument("--output", default="./data/output", help="输出目录")
    parser.add_argument("--visuals-dir", default="./data/output/visuals", help="视觉资产输出目录")
    parser.add_argument("--async-mode", action="store_true", help="使用异步模式")
    
    args = parser.parse_args()
    
    if args.async_mode:
        foundry = AsyncVisualAssetFoundry(args.script, args.output, args.visuals_dir)
        import asyncio
        asyncio.run(foundry.run_async())
    else:
        foundry = VisualAssetFoundry(args.script, args.output, args.visuals_dir)
        foundry.run()