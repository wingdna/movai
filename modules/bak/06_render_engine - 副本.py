# modules/06_render_engine.py
"""
模块6：2.5D 动态渲染与合成器 - 完整音频对齐版
"""
import json
import sys
import math
import numpy as np
import cv2
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from abc import ABC, abstractmethod  
from PIL import Image, ImageOps
import random

# ---------------------------------------------------------
# 🛡️ 架构师强力修复：双重绝对寻址防线
# 不管从哪里动态导入，强行把根目录和 modules 目录焊死在系统路径里！
# ---------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent)) # 添加根目录
sys.path.insert(0, str(Path(__file__).parent))        # 添加 modules 目录

# 尝试导入 Taichi
try:
    import taichi as ti
    ti.init(arch=ti.cpu, cpu_max_num_threads=8, fast_math=True, verbose=False)
    # 双保险导入：先尝试绝对路径，再尝试相对路径
    try:
        from modules.physics_engine import TitaniumRenderer
    except ImportError:
        from physics_engine import TitaniumRenderer
    USE_TAICHI = True
    print("✅ Taichi 物理引擎已启用")
except ImportError:
    USE_TAICHI = False
    try:
        from modules.simple_engine import SimpleRenderer
    except ImportError:
        from simple_engine import SimpleRenderer
    print("⚠️ Taichi 未安装或找不到引擎，使用简化渲染器")


import random # 确保文件顶部有这个导入

# ============================================================
# 动态多阶段运镜系统 (解决长场景缓慢定格问题)
# ============================================================
# ============================================================
# 动态多阶段运镜系统 (微动态/无瑕疵版)
# ============================================================
class DynamicCameraPath:
    def __init__(self, duration: float, movement_tag: str):
        self.duration = max(duration, 0.1)
        self.waypoints =[]
        
        # 【重要修改】将整体运镜强度大幅度压缩 (原先是 1.0，现在降为 0.25)
        # 确保不会因为大动作导致边缘像素被撕裂/拉伸
        intensity = 0.5 
        if "SLOW" in movement_tag: intensity = 0.15
        if "FAST" in movement_tag: intensity = 0.4
        
        # 更慢的动作切换频率（每 5~6 秒才换一次方向）
        interval = 5.0 
        num_phases = max(2, int(duration / interval) + 1)
        
        # 起点更靠近绝对中心
        start_cx = random.uniform(-0.5, 0.5) * intensity
        start_cy = random.uniform(-0.3, 0.3) * intensity
        start_cz = 0.0
        start_sway = 0.0
        
        self.waypoints.append({
            "cx": start_cx, "cy": start_cy, "cz": start_cz, "sway": start_sway
        })
        
        for i in range(1, num_phases):
            prev = self.waypoints[-1]
            # 简化动作：去掉了剧烈的旋转和扫视，保留极其平滑的缓推和微平移
            action = random.choice([0, 1]) 
            
            cx, cy, cz, sway = prev["cx"], prev["cy"], prev["cz"], prev["sway"]
            
            if action == 0: # 极其轻微的呼吸推拉
                cz = random.uniform(0.05, 0.15) * intensity if prev["cz"] < 0.1 else random.uniform(-0.05, 0.05)
                cx += random.uniform(-0.5, 0.5) * intensity
                cy += random.uniform(-0.2, 0.2) * intensity
            elif action == 1: # 极其微弱的视差平移 (类似参考图的右移)
                cx = random.uniform(1.0, 2.5) * intensity if prev["cx"] < 0 else random.uniform(-2.5, -1.0) * intensity
                cy += random.uniform(-0.5, 0.5) * intensity
                cz += random.uniform(-0.02, 0.02)
                sway = random.uniform(-0.01, 0.01) # 微乎其微的歪头
            
            # 【重要修改】严苛的安全阀值，彻底杜绝穿模和拉扯黑边
            cx = max(-1.5, min(1.5, cx))
            cy = max(-0.8, min(0.8, cy))
            cz = max(-0.05, min(0.15, cz)) 
            sway = max(-0.02, min(0.02, sway))
            
            self.waypoints.append({"cx": cx, "cy": cy, "cz": cz, "sway": sway})
            
        self.phase_duration = self.duration / (num_phases - 1)
        
    def get_camera_state(self, time_sec: float) -> tuple:
        if time_sec >= self.duration:
            last = self.waypoints[-1]
            return last["cx"], last["cy"], last["cz"], last["sway"]
            
        current_idx = int(time_sec / self.phase_duration)
        next_idx = min(current_idx + 1, len(self.waypoints) - 1)
        
        local_t = (time_sec % self.phase_duration) / self.phase_duration
        # Sine ease-in-out，比 cubic 更柔和的启动
        ease_t = 0.5 * (1 - math.cos(math.pi * local_t))
        
        p1 = self.waypoints[current_idx]
        p2 = self.waypoints[next_idx]
        
        cx = p1["cx"] + (p2["cx"] - p1["cx"]) * ease_t
        cy = p1["cy"] + (p2["cy"] - p1["cy"]) * ease_t
        cz = p1["cz"] + (p2["cz"] - p1["cz"]) * ease_t
        sway = p1["sway"] + (p2["sway"] - p1["sway"]) * ease_t
        
        return cx, cy, cz, sway
# ============================================================
# 音频时长解析器
# ============================================================

class AudioDurationParser:
    """从 timed_script.json 解析音频时长"""
    
    @staticmethod
    def get_scene_duration(scene: Dict) -> float:
        """
        获取场景的实际音频时长（秒）
        
        优先级：
        1. 场景中已计算的 duration_sec
        2. 场景中 audio_segments 的总时长
        3. 场景中 merged 音频的实际时长
        4. 默认 3 秒
        """
        # 方式1: 使用已计算的时长
        if "duration_sec" in scene and scene["duration_sec"]:
            return float(scene["duration_sec"])
        
        # 方式2: 从 audio_segments 计算总时长
        audio_segments = scene.get("audio_segments", [])
        if audio_segments:
            total_duration = sum(seg.get("duration", 0) for seg in audio_segments)
            if total_duration > 0:
                return total_duration
        
        # 方式3: 尝试读取合并后的音频文件
        merged_audio = scene.get("audio", {}).get("merged")
        if merged_audio and Path(merged_audio).exists():
            try:
                from moviepy import AudioFileClip
                with AudioFileClip(merged_audio) as audio:
                    return audio.duration
            except:
                pass
        
        # 默认
        return 3.0


# ============================================================
# 动画曲线工具
# ============================================================

class AnimationCurve:
    """动画曲线工具"""
    
    @staticmethod
    def linear(t: float) -> float:
        return t
    
    @staticmethod
    def ease_in(t: float) -> float:
        return t * t
    
    @staticmethod
    def ease_out(t: float) -> float:
        return 1 - (1 - t) * (1 - t)
    
    @staticmethod
    def ease_in_out(t: float) -> float:
        return 3 * t * t - 2 * t * t * t
    
    @staticmethod
    def elastic(t: float) -> float:
        return math.sin(13 * math.pi / 2 * t) * math.pow(2, -10 * t)
    
    @staticmethod
    def bounce(t: float) -> float:
        if t < 1 / 2.75:
            return 7.5625 * t * t
        elif t < 2 / 2.75:
            t -= 1.5 / 2.75
            return 7.5625 * t * t + 0.75
        elif t < 2.5 / 2.75:
            t -= 2.25 / 2.75
            return 7.5625 * t * t + 0.9375
        else:
            t -= 2.625 / 2.75
            return 7.5625 * t * t + 0.984375
    
    @staticmethod
    def get_curve(name: str) -> Callable:
        curves = {
            "linear": AnimationCurve.linear,
            "ease_in": AnimationCurve.ease_in,
            "ease_out": AnimationCurve.ease_out,
            "ease_in_out": AnimationCurve.ease_in_out,
            "elastic": AnimationCurve.elastic,
            "bounce": AnimationCurve.bounce,
        }
        return curves.get(name, AnimationCurve.linear)


# ============================================================
# 渲染器抽象基类
# ============================================================

class BaseRenderer(ABC):
    """渲染器抽象基类"""
    
    @abstractmethod
    def load_maps(self, rgb: np.ndarray, depth: np.ndarray, normal: np.ndarray):
        pass
    
    @abstractmethod
    def init_sim(self):
        pass
    
    @abstractmethod
    def update_sim(self, dt: float, vfx_type: int, audio_feature: float, has_boids: int, intensity: float):
        pass
    
    @abstractmethod
    def render_frame(self, t: float, cx: float, cy: float, cz: float, 
                     light_pos, light_mode: int, shadow_intensity: float,
                     sway: float, bass: float, light_intensity: float):
        pass
    
    @abstractmethod
    def apply_godrays(self, lx: float, ly: float):
        pass
    
    @abstractmethod
    def render_particles(self):
        pass
    
    @abstractmethod
    def get_frame(self) -> np.ndarray:
        pass


class TaichiRendererWrapper(BaseRenderer):
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.renderer = TitaniumRenderer(width, height)
    
    def load_maps(self, rgb: np.ndarray, depth: np.ndarray, normal: np.ndarray):
        self.renderer.load_maps(rgb, depth, normal)
    
    def init_sim(self):
        self.renderer.init_sim()
    
    def update_sim(self, dt: float, vfx_type: int, audio_feature: float, has_boids: int, intensity: float):
        self.renderer.update_sim(dt, vfx_type, audio_feature, has_boids, intensity)
    
    def render_frame(self, t: float, cx: float, cy: float, cz: float, 
                     light_pos, light_mode: int, shadow_intensity: float,
                     sway: float, bass: float, light_intensity: float):
        self.renderer.render_titan(t, cx, cy, cz, light_pos, light_mode, 
                                   shadow_intensity, sway, bass, light_intensity)
    
    def apply_godrays(self, lx: float, ly: float):
        self.renderer.apply_godrays(lx, ly)
    
    def render_particles(self):
        self.renderer.render_particles()
    
    def get_frame(self) -> np.ndarray:
        return self.renderer.get_frame()


class SimpleRendererWrapper(BaseRenderer):
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.renderer = SimpleRenderer(width, height)
    
    def load_maps(self, rgb: np.ndarray, depth: np.ndarray, normal: np.ndarray):
        self.renderer.load_maps(rgb, depth, normal)
    
    def init_sim(self):
        self.renderer.init_sim()
    
    def update_sim(self, dt: float, vfx_type: int, audio_feature: float, has_boids: int, intensity: float):
        self.renderer.update_sim(dt, vfx_type, audio_feature, has_boids, intensity)
    
    def render_frame(self, t: float, cx: float, cy: float, cz: float, 
                     light_pos, light_mode: int, shadow_intensity: float,
                     sway: float, bass: float, light_intensity: float):
        self.renderer.render_titan(t, cx, cy, cz, light_pos, light_mode,
                                   shadow_intensity, sway, bass, light_intensity)
    
    def apply_godrays(self, lx: float, ly: float):
        self.renderer.apply_godrays(lx, ly)
    
    def render_particles(self):
        self.renderer.render_particles()
    
    def get_frame(self) -> np.ndarray:
        return self.renderer.get_frame()


def create_renderer(width: int, height: int) -> BaseRenderer:
    if USE_TAICHI:
        return TaichiRendererWrapper(width, height)
    else:
        return SimpleRendererWrapper(width, height)


# ============================================================
# 电影后期特效处理器
# ============================================================

# ============================================================
# 电影后期特效处理器 (清晰度优化版)
# ============================================================

class CinematicPostProcessor:
    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        
        # 减弱暗角强度，防止画面边缘过暗导致细节丢失
        Y, X = np.ogrid[:height, :width]
        dist_sq = (X - width/2)**2 + (Y - height/2)**2
        max_radius_sq = (min(width, height) * 0.7)**2
        self.base_vignette = np.clip(1.1 - dist_sq / max_radius_sq, 0.6, 1.0)
    
    def compute_ssao_mask(self, depth_norm: np.ndarray) -> np.ndarray:
        depth_blur = cv2.GaussianBlur(depth_norm, (21, 21), 0)
        # 减轻 SSAO 强度，避免暗部死黑
        return np.clip(1.0 - (depth_blur - depth_norm) * 4.0, 0.6, 1.0)[:, :, np.newaxis]
    
    def apply_dof(self, frame: np.ndarray, depth_norm: np.ndarray, 
                  focus_dist: float = 0.8, blur_strength: float = 2.0) -> np.ndarray:
        # 【修改】将 blur_strength 从 18.0 降到 2.0，几乎关闭景深，保持全景清晰
        if blur_strength <= 0: return frame
        blur_strength_map = np.power(np.abs(depth_norm - focus_dist), 1.2) * blur_strength
        blend_mask = np.clip(blur_strength_map, 0, 1)[:, :, np.newaxis]
        blur_img = cv2.GaussianBlur(frame, (7, 7), 0) # 减小高斯模糊核
        return (frame.astype(np.float32) * (1 - blend_mask) + 
                blur_img.astype(np.float32) * blend_mask).astype(np.uint8)
    
    def apply_chromatic_aberration(self, frame: np.ndarray, t: float, max_shift: int = 0) -> np.ndarray:
        # 【修改】将 max_shift 从 3 降为 0，彻底关闭色散导致的红蓝重影
        if max_shift == 0:
            return frame
        shift = int(max_shift * (0.5 + 0.5 * math.sin(t * math.pi)))
        if shift == 0: return frame
        r, g, b = cv2.split(frame)
        M_r = np.float32([[1, 0, shift], [0, 1, 0]])
        M_b = np.float32([[1, 0, -shift], [0, 1, 0]])
        r_shifted = cv2.warpAffine(r, M_r, (self.w, self.h), borderMode=cv2.BORDER_REPLICATE)
        b_shifted = cv2.warpAffine(b, M_b, (self.w, self.h), borderMode=cv2.BORDER_REPLICATE)
        return cv2.merge((r_shifted, g, b_shifted))
    
    def apply_vignette(self, frame: np.ndarray, t: float) -> np.ndarray:
        breathe = 1.0 + 0.05 * math.sin(t * 2.0) # 减弱呼吸效应
        vignette = np.clip(self.base_vignette * breathe, 0, 1)[:, :, np.newaxis]
        return (frame.astype(np.float32) * vignette).astype(np.uint8)
    
    def apply_film_grain(self, frame: np.ndarray, intensity: float = 0.0) -> np.ndarray:
        # 【修改】将 intensity 从 4.5 降为 0.0，彻底关闭胶片噪点，这对视频压缩极度不友好
        if intensity <= 0: return frame
        noise = np.random.randn(self.h, self.w, 3).astype(np.float32) * intensity
        return np.clip(frame.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    
    def apply_sharpen(self, frame: np.ndarray, amount: float = 0.0) -> np.ndarray:
        if amount <= 0.0:
            return frame # 彻底不进行锐化处理，保持原图柔和
        blurred = cv2.GaussianBlur(frame, (0, 0), 1.5)
        return cv2.addWeighted(frame, 1.0 + amount, blurred, -amount, 0)
    
    def apply_contrast(self, frame: np.ndarray, alpha: float = 1.05, beta: int = 0) -> np.ndarray:
        return cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)
    
    def process(self, frame: np.ndarray, depth_norm: np.ndarray, t: float,
                ssao_mask: np.ndarray = None) -> np.ndarray:
        result = frame.copy()
        if ssao_mask is not None:
            result = (result.astype(np.float32) * ssao_mask).astype(np.uint8)
        
        # 依次应用优化后的特效（去除了景深、色散、噪点，强化了锐化）
        # result = self.apply_dof(result, depth_norm) # 直接注释掉景深
        result = self.apply_chromatic_aberration(result, t)
        result = self.apply_vignette(result, t)
        # result = self.apply_film_grain(result) # 直接注释掉噪点
        result = self.apply_sharpen(result)
        result = self.apply_contrast(result)
        
        return result

# ============================================================
# 场景渲染器
# ============================================================

class SceneRenderer:
    """单场景渲染器 - 时长精确匹配音频"""
    
    def __init__(self, width: int, height: int, fps: int = 24):
        self.w = width
        self.h = height
        self.fps = fps
        self.post_processor = CinematicPostProcessor(width, height)
    
    def render_scene(self, scene: Dict, target_duration: float, 
                     curve_name: str = "ease_in_out") -> List[np.ndarray]:
        """渲染单个场景 - 单次缩放优化版"""
        
        rgb_path = scene.get("rgb_image")
        depth_path = scene.get("depth_map")
        
        if not rgb_path or not Path(rgb_path).exists():
            print(f"      ❌ 图像不存在")
            return []
        
        # ========== 1. 一次性加载到目标尺寸 ==========
        # 直接加载并缩放到最终渲染尺寸，避免中间缩放
        rgb_pil = Image.open(rgb_path).convert("RGB")
        
        # 计算目标尺寸（保持宽高比，然后裁剪到 16:9）
        orig_w, orig_h = rgb_pil.size
        target_w = self.w
        target_h = self.h
        
        # 计算缩放比例（填充模式）
        scale = max(target_w / orig_w, target_h / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        
        # 缩放到稍大的尺寸
        rgb_resized = rgb_pil.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # 裁剪到目标尺寸（中心裁剪）
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        rgb_cropped = rgb_resized.crop((left, top, left + target_w, top + target_h))
        rgb = np.array(rgb_cropped)
        
        # ========== 2. 深度图同样一次性处理 ==========
        if depth_path and Path(depth_path).exists():
            depth_pil = Image.open(depth_path).convert("L")
            depth_resized = depth_pil.resize((new_w, new_h), Image.Resampling.LANCZOS)
            depth_cropped = depth_resized.crop((left, top, left + target_w, top + target_h))
            depth = np.array(depth_cropped)
        else:
            # 创建渐变深度图
            depth = np.zeros((target_h, target_w), dtype=np.uint8)
            for i in range(target_h):
                depth[i, :] = int(255 * (1 - i / target_h))
        
        # ========== 3. 归一化处理 ==========
        depth_norm = depth.astype(np.float32) / 255.0
        rgb_norm = rgb.astype(np.float32) / 255.0
        
        # ========== 4. 计算法线（使用已处理的深度图）==========
        grad_x = cv2.Sobel(depth_norm, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(depth_norm, cv2.CV_32F, 0, 1, ksize=3)
        nx, ny = -grad_x, -grad_y
        nz = np.sqrt(1 - np.clip(nx**2 + ny**2, 0, 0.99))
        norm = np.sqrt(nx**2 + ny**2 + nz**2) + 1e-6
        normal = np.stack([nx/norm, ny/norm, nz/norm], axis=2)
        normal_norm = (normal + 1) / 2.0
        
        # ========== 5. 初始化渲染器 ==========
        renderer = create_renderer(self.w, self.h)
        
        # 转置为渲染器需要的格式 (H, W, C) -> (W, H, C)
        rgb_transposed = rgb_norm.transpose(1, 0, 2)
        depth_transposed = depth_norm.transpose(1, 0)
        normal_transposed = normal_norm.transpose(1, 0, 2)
        
        renderer.load_maps(rgb_transposed, depth_transposed, normal_transposed)
        renderer.init_sim()
        
        # ========== 6. 预计算 SSAO 遮罩 ==========
        ssao_mask = self.post_processor.compute_ssao_mask(depth_norm)
        
        # ========== 7. 场景参数 ==========
        camera_movement = scene.get("camera_movement", "STATIC")
        vfx_tags = scene.get("sfx_tags", [])
        emotion = scene.get("emotion", "NEUTRAL")
        
        vfx_str = str(vfx_tags).lower()
        if "rain" in vfx_str:
            vfx_type = 2
        elif "fire" in vfx_str:
            vfx_type = 1
        else:
            vfx_type = 0
        
        # 相机参数
        camera_movement = scene.get("camera_movement", "STATIC")
        vfx_tags = scene.get("sfx_tags",[])
        emotion = scene.get("emotion", "NEUTRAL")

        
        # 动画曲线
        curve_map = {
            "TENSION": "ease_in",
            "FEAR": "elastic",
            "MYSTERY": "ease_in_out",
            "REVELATION": "bounce",
            "EPIC": "ease_out",
        }
        curve = AnimationCurve.get_curve(curve_map.get(emotion, curve_name))
        
        num_frames = max(1, int(target_duration * self.fps))
        # 实例化动态相机器
        cam_path = DynamicCameraPath(target_duration, camera_movement)
        print(f"      🎨 渲染 | 尺寸:{self.w}x{self.h} | 时长:{target_duration:.2f}s | 帧数:{num_frames}")
        
        # ========== 8. 渲染循环 (动态光影重定向版) ==========
        frames =[]
        for i in range(num_frames):
            time_sec = i / self.fps   # 当前的真实秒数
            t = i / (num_frames - 1) if num_frames > 1 else 0
            
            # 使用极微动态相机器 (保持原图的高清晰度和稳定性)
            cx, cy, cz, sway = cam_path.get_camera_state(time_sec)
            
            # --- 🌟 核心修改：动态光影强度与位置系统 (Relighting) ---
            if vfx_type == 1: 
                # 【火焰模式 / FIRE】暖色闪烁光 (比如壁炉、火把)
                # 1. 模拟火焰不规则的明暗跳动 (叠加三个不同频率的正弦波)
                flicker = 0.85 + 0.1 * math.sin(time_sec * 3.0) + 0.05 * math.sin(time_sec * 5.5)
                current_light_intensity = max(0.5, flicker)
                # 2. 光源位置设定 (模拟火源在画面偏左下方，且有微小晃动)
                # 这样光打在人物身上会产生非常立体的单侧高光和阴影
                lx = self.w * 0.3 + math.sin(time_sec * 4.0) * 15
                ly = self.h * 0.7 + math.cos(time_sec * 3.5) * 15

            elif vfx_type == 2: 
                # 【雨天模式 / RAIN】带有随机闪电的冷光源
                # 偶尔出现的闪电暴击
                import random
                is_lightning = 2.0 if random.random() > 0.95 else 0.0
                current_light_intensity = 0.6 + is_lightning
                lx = self.w / 2 + math.sin(time_sec * 0.8) * self.w / 2
                ly = self.h / 2 + math.cos(time_sec * 1.2) * self.h / 2

            else: 
                # 【常规模式】默认环境光
                # 极其微弱的呼吸光感，让静态场景也能透气
                current_light_intensity = 0.85 + 0.03 * math.sin(time_sec * 2.0)
                lx = self.w / 2 + math.cos(time_sec * 0.5) * self.w / 2.5
                ly = self.h / 2 + math.sin(time_sec * 0.7) * self.h / 2.5
            
            # 粒子与场景律动
            bass = 0.5 + 0.3 * math.sin(time_sec * 2.0)
            treble = 0.5 + 0.2 * math.sin(time_sec * 4.0)
            
            renderer.update_sim(0.1, vfx_type, treble, 0, treble)
            
            light_pos = ti.Vector([lx, ly, 150.0]) if USE_TAICHI else[lx, ly, 150.0]
            
            # --- 🌟 核心修改点：将原本写死的 1.0 替换为 current_light_intensity ---
            # 渲染引擎将利用底层计算好的法线图（Normal Map）与这个跳动的光强进行物理乘法
            renderer.render_frame(t, cx, cy, cz, light_pos, 1, 0.5, sway, bass, current_light_intensity)
            
            # 附加全局光束 (体积光)
            #renderer.apply_godrays(lx, ly)
            renderer.render_particles()
            
            # 提取与后期 (已应用你的极简保真处理器)
            raw = np.clip(renderer.get_frame() * 255, 0, 255).astype(np.uint8)
            raw = cv2.cvtColor(raw, cv2.COLOR_RGB2BGR)
            
            final = self.post_processor.process(raw, depth_norm, t, ssao_mask)
            frames.append(final)
            
            # 打印渲染进度条
            if i % max(1, num_frames // 10) == 0 and i > 0:
                print(f"      📸 进度: {int(t * 100)}%")
        
        return frames        
       

# ============================================================
# 音频合成器
# ============================================================

class AudioComposer:
    @staticmethod
    def compose_all_audio(timed_script: Dict, audio_dir: Path, bitrate: str = "192k") -> Optional[Path]:
        """
        合成所有场景的音频（按时间顺序）- 优化版
        
        Args:
            timed_script: 时序剧本
            audio_dir: 音频目录
            bitrate: 音频比特率 (默认 192k，范围 128k-320k)
        """
        scenes = timed_script.get("scenes", [])
        all_audio = []
        
        # 收集所有音频文件
        for i, scene in enumerate(scenes):
            # 优先使用合并后的音频
            merged = scene.get("audio", {}).get("merged")
            if merged and Path(merged).exists():
                all_audio.append(merged)
                continue
            
            # 收集场景中的所有音频片段
            audio_segments = scene.get("audio_segments", [])
            for seg in audio_segments:
                path = seg.get("path")
                if path and Path(path).exists():
                    all_audio.append(path)
            
            # 额外检查目录中的场景音频文件
            scene_files = list(audio_dir.glob(f"scene_{i+1:03d}_*.mp3"))
            for f in scene_files:
                if str(f) not in all_audio:
                    all_audio.append(str(f))
        
        if not all_audio:
            print(f"      ⚠️ 未找到任何音频文件")
            return None
        
        # 按场景顺序排序
        all_audio.sort()
        
        print(f"      🎵 找到 {len(all_audio)} 个音频文件")
        
        try:
            from moviepy import AudioFileClip, concatenate_audioclips
            import subprocess
            
            # 方法1: 使用 ffmpeg 直接合并（更快，质量更好）
            # 创建 ffmpeg 输入文件列表
            list_file = audio_dir / "audio_list.txt"
            with open(list_file, 'w', encoding='utf-8') as f:
                for audio_path in all_audio:
                    f.write(f"file '{Path(audio_path).absolute()}'\n")
            
            output_path = audio_dir / "final_audio.mp3"
            
            # 使用 ffmpeg 合并音频，设置 CRF 类似的参数
            # MP3 使用比特率控制质量，192k 是高质量标准
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(list_file),
                '-c:a', 'libmp3lame',
                '-b:a', bitrate,           # 比特率，如 192k
                '-q:a', '2',               # VBR 质量 (0-9, 0最好, 2是高质量)
                '-ar', '44100',            # 采样率
                '-ac', '2',                # 立体声
                str(output_path)
            ]
            
            print(f"      🎵 合并音频 (比特率: {bitrate})")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and output_path.exists():
                # 清理临时文件
                if list_file.exists():
                    list_file.unlink()
                print(f"      ✅ 音频合成完成: {output_path.name}")
                return output_path
            
            # 方法2: 如果 ffmpeg 失败，回退到 moviepy
            print(f"      ⚠️ ffmpeg 合并失败，尝试 moviepy...")
            clips = []
            for f in all_audio:
                if Path(f).exists():
                    clips.append(AudioFileClip(str(f)))
            
            if clips:
                final = concatenate_audioclips(clips)
                final.write_audiofile(
                    str(output_path), 
                    logger=None,
                    fps=44100,
                    nbytes=2,
                    codec='libmp3lame',
                    bitrate=bitrate
                )
                final.close()
                return output_path
            
            return None
            
        except Exception as e:
            print(f"   ❌ 音频合成失败: {e}")
            return None

# ============================================================
# 主引擎
# ============================================================

class AdvancedRenderEngine:
    def __init__(self, script_path: str, audio_dir: str = "./data/output/audio",
                 visuals_dir: str = "./data/output/visuals",
                 output_dir: str = "./data/output",
                 output_filename: str = "final_render.mp4",
                 fps: int = 12, quality: int = 5, target_width: int = 1920,
                 preset: str = "fast"):
        
        self.script_path = Path(script_path)
        self.audio_dir = Path(audio_dir)
        self.visuals_dir = Path(visuals_dir)
        self.output_path = Path(output_dir) / output_filename
        self.fps = min(fps, 30)
        self.quality = max(1, min(10, quality))       
        self.crf = max(18, min(28, 28 - (self.quality - 1) * 1.1))
        
        self.target_width = min(target_width, 1920)
        self.preset = preset
        
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.timed_script = self._load_script()
        
        self.w = self.target_width
        self.h = int(self.target_width * 9 / 16)
        
        self.stats = {"total_scenes": 0, "scenes_rendered": 0, 
                      "total_frames": 0, "total_duration": 0}
        
        print("\n" + "="*60)
        print("🎬 2.5D 渲染引擎 (音频对齐版)")
        print("="*60)
        print(f"📁 输出: {self.output_path}")
        print(f"🎬 分辨率: {self.w}x{self.h} @ {self.fps}fps")
        print(f"🎨 画质: {self.quality}/10 | ⚡ 预设: {self.preset}")
        print("="*60)
    
    def _load_script(self) -> Dict:
        with open(self.script_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
# modules/06_render_engine.py
# 修复 _get_scene_duration 方法

    def _get_scene_duration(self, scene: Dict) -> float:
        """获取场景的实际音频时长（秒）- 从多个来源获取"""
        
        # 方式1: 场景中直接存储的 duration_sec
        if "duration_sec" in scene and scene["duration_sec"]:
            dur = float(scene["duration_sec"])
            if dur > 0:
                print(f"      📍 从 duration_sec 读取: {dur:.2f}s")
                return dur
        
        # 方式2: 从 audio 对象中的 merged 音频文件获取实际时长
        audio_obj = scene.get("audio", {})
        merged_path = audio_obj.get("merged")
        if merged_path and Path(merged_path).exists():
            try:
                from moviepy import AudioFileClip
                with AudioFileClip(merged_path) as audio:
                    dur = audio.duration
                    print(f"      📍 从 merged 音频读取: {dur:.2f}s ({merged_path})")
                    return dur
            except Exception as e:
                print(f"      ⚠️ 读取 merged 音频失败: {e}")
        
        # 方式3: 从 audio_segments 计算总时长
        audio_segments = scene.get("audio_segments", [])
        if audio_segments:
            total = 0
            for seg in audio_segments:
                seg_dur = seg.get("duration", 0)
                if seg_dur > 0:
                    total += seg_dur
                else:
                    # 尝试读取实际文件时长
                    seg_path = seg.get("path")
                    if seg_path and Path(seg_path).exists():
                        try:
                            from moviepy import AudioFileClip
                            with AudioFileClip(seg_path) as audio:
                                seg_dur = audio.duration
                                total += seg_dur
                        except:
                            pass
            if total > 0:
                print(f"      📍 从 audio_segments 计算: {total:.2f}s")
                return total
        
        # 方式4: 从场景中的 dialogue 和 narration 估算
        narration = scene.get("narration", "")
        dialogues = scene.get("dialogues", [])
        if narration or dialogues:
            # 粗略估算：中文语速约 3-4 字/秒
            total_chars = len(narration)
            for d in dialogues:
                total_chars += len(d.get("line", ""))
            estimated = max(1.5, total_chars / 3.5)
            print(f"      📍 估算时长: {estimated:.2f}s (基于文本长度)")
            return estimated
        
        # 默认
        print(f"      ⚠️ 无法获取音频时长，使用默认 3.0s")
        return 3.0
    
    
    def run(self) -> Path:
        print("\n🎬 开始渲染...")
        
        scenes = self.timed_script.get("scenes", [])
        self.stats["total_scenes"] = len(scenes)
        
        # 调试：打印第一个场景的完整结构
        if scenes:
            print("\n   🔍 调试: 第一个场景的数据结构")
            first_scene = scenes[0]
            print(f"      scene_name: {first_scene.get('scene_name')}")
            print(f"      duration_sec: {first_scene.get('duration_sec')}")
            print(f"      audio: {first_scene.get('audio', {}).keys() if first_scene.get('audio') else 'None'}")
            print(f"      audio_segments: {len(first_scene.get('audio_segments', []))} 个")
            for seg in first_scene.get('audio_segments', [])[:3]:
                print(f"         - type: {seg.get('type')}, duration: {seg.get('duration')}, path: {Path(seg.get('path', '')).name}")
        
        scene_renderer = SceneRenderer(self.w, self.h, self.fps)
        all_frames = []
        
        for i, scene in enumerate(scenes, 1):
            print(f"\n   🎬 场景 {i}: {scene.get('scene_name', '未命名')[:40]}")
            
            duration = self._get_scene_duration(scene)
            emotion = scene.get("emotion", "NEUTRAL")
            
            print(f"      ⏱️ 最终使用时长: {duration:.2f}s")
            
            frames = scene_renderer.render_scene(scene, duration)
            
            if frames:
                all_frames.extend(frames)
                self.stats["scenes_rendered"] += 1
                self.stats["total_duration"] += duration
                self.stats["total_frames"] += len(frames)
        
        if not all_frames:
            print("❌ 没有成功渲染任何帧")
            return self.output_path
        
        # 合成最终音频
        print(f"\n🎵 合成最终音频...")
        final_audio = self.audio_dir / "final_audio.mp3"
        
        if not final_audio.exists():
            # 尝试合成所有场景音频
            all_audio = []
            for i, scene in enumerate(scenes, 1):
                audio_files = list(self.audio_dir.glob(f"scene_{i:03d}_*.mp3"))
                all_audio.extend(audio_files)
            
            if all_audio:
                try:
                    from moviepy import AudioFileClip, concatenate_audioclips
                    clips = [AudioFileClip(str(f)) for f in all_audio if f.exists()]
                    if clips:
                        final = concatenate_audioclips(clips)
                        final.write_audiofile(str(final_audio), logger=None)
                        final.close()
                        print(f"      ✅ 合成音频完成: {final_audio.name}")
                except Exception as e:
                    print(f"      ⚠️ 音频合成失败: {e}")
        
        # 合成视频
        print(f"\n🎬 合成视频 ({len(all_frames)} 帧, 目标时长: {self.stats['total_duration']:.1f}s)")

        try:
            import imageio
            import subprocess
            
            temp_video = self.output_path.with_suffix('.temp.mp4')
            
            # CRF 值设置
            crf_val = 26
            if hasattr(self, 'quality') and self.quality:
                crf_val = max(18, min(28, 28 - (self.quality - 1) * 1.1))
            
            preset = getattr(self, 'preset', 'medium')
            
            print(f"      🎬 编码参数: CRF={crf_val:.1f}, 预设={preset}")
            
            writer = imageio.get_writer(
                str(temp_video), 
                fps=self.fps, 
                codec='libx264',
                quality=None, 
                pixelformat='yuv420p',
                ffmpeg_params=[
                    '-preset', preset,
                    '-crf', str(crf_val),
                    '-tune', 'stillimage',  # 🌟【神级参数】告诉编码器这是静态图微动，极大压缩背景体积
                    '-movflags', '+faststart',
                    '-profile:v', 'high',
                    '-level', '4.1',
                    # 🌟【体积暴降核心】将关键帧间隔从 48 增加到 250（约10秒一次）。极大减少大体积帧的数量
                    '-x264opts', 'keyint=250:min-keyint=24:scenecut=0' 
                ]
            )
            
            total_frames = len(all_frames)
            for i, frame in enumerate(all_frames):
                if frame.shape[1] != self.w or frame.shape[0] != self.h:
                    frame = cv2.resize(frame, (self.w, self.h))
                writer.append_data(frame)
                if i % 200 == 0 and i > 0:
                    print(f"      📹 写入帧 {i}/{total_frames}")
            writer.close()
            
            if final_audio and final_audio.exists():
                print(f"   🎵 添加音频: {final_audio.name}")
                cmd =[
                    'ffmpeg', '-y',
                    '-i', str(temp_video),
                    '-i', str(final_audio),
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-b:a', '192k',  # 🎵 将音频从 192k 降到 128k (人声足够清晰，体积减小 30%)
                    '-ar', '44100',
                    '-ac', '2',
                    '-shortest',
                    '-movflags', '+faststart',
                    str(self.output_path)
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if temp_video.exists():
                    temp_video.unlink()
                print(f"   ✅ 音视频合成完成")
            else:
                print(f"   ⚠️ 未找到音频文件，输出无声视频")
                temp_video.rename(self.output_path)
            
            size_mb = self.output_path.stat().st_size / (1024 * 1024) if self.output_path.exists() else 0
            print(f"\n✅ 完成!")
            print(f"   📁 {self.output_path}")
            print(f"   📦 {size_mb:.1f} MB")
            print(f"   ⏱️ 视频时长: {self.stats['total_duration']:.1f}s")
            print(f"   🎬 {self.stats['scenes_rendered']}/{self.stats['total_scenes']} 场景")
            
        except Exception as e:
            print(f"   ❌ 合成失败: {e}")
            import traceback
            traceback.print_exc()

        return self.output_path    
        

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--script", default="./data/output/timed_script.json")
    p.add_argument("--audio-dir", default="./data/output/audio")
    p.add_argument("--visuals-dir", default="./data/output/visuals")
    p.add_argument("--output", default="./data/output")
    p.add_argument("--fps", type=int, default=12)
    p.add_argument("--quality", type=int, default=5)
    p.add_argument("--width", type=int, default=1280)
    p.add_argument("--preset", default="fast")
    args = p.parse_args()
    
    engine = AdvancedRenderEngine(
        script_path=args.script,
        audio_dir=args.audio_dir,
        visuals_dir=args.visuals_dir,
        output_dir=args.output,
        fps=args.fps,
        quality=args.quality,
        target_width=args.width,
        preset=args.preset
    )
    engine.run()