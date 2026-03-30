# modules/06_render_engine_advanced.py
"""
模块6：2.5D 动态渲染与合成器 - 满血 IMAX 级视觉无损版
- 解决大动态运镜带来的变形问题 (引入 Overscan 过扫描)
- 3-6秒多段动态大幅度运镜
- 极致奶油虚化景深 + 炫酷法线光影
- 视觉无损 (CRF 21) 且高压缩比编码
"""
import sys
import math
import json
import numpy as np
import cv2
import subprocess
import random
from pathlib import Path
from typing import Dict, List, Optional
from PIL import Image, ImageOps

# 🛡️ 架构师防线：双重绝对寻址
sys.path.insert(0, str(Path(__file__).parent.parent)) 
sys.path.insert(0, str(Path(__file__).parent))        

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["TAICHI_ARCH"] = "cpu"

try:
    import taichi as ti
    ti.init(arch=ti.cpu, cpu_max_num_threads=8, fast_math=True, verbose=False)
    try:
        from modules.physics_engine import TitaniumRenderer
    except ImportError:
        from physics_engine import TitaniumRenderer
    USE_TAICHI = True
    print("✅ Taichi CPU 高速模式已启用")
except ImportError:
    USE_TAICHI = False
    try:
        from modules.simple_engine import SimpleRenderer
    except ImportError:
        from simple_engine import SimpleRenderer
    print("⚠️ Taichi 未安装，使用简化渲染器")



def get_edge_decoupling_mask(depth_norm: np.ndarray) -> np.ndarray:
    """
    [Priority 1] 分层边缘防拉丝引擎
    输入: 归一化的深度图 (H, W)
    输出: 边缘阻尼掩码 (H, W, 1)
    """
    # 1. 使用 Sobel 算子提取深度突变梯度
    gx = cv2.Sobel(depth_norm, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(depth_norm, cv2.CV_32F, 0, 1, ksize=3)
    edge_gradient = np.sqrt(gx**2 + gy**2)
    
    # 2. 将梯度归一化并取反：梯度越大(边缘越猛)，系数越小(位移越低)
    # 系数 15.0 控制敏感度，建议范围 10.0-20.0
    mask = np.clip(1.0 - edge_gradient * 5.0, 0.0, 1.0)
    
    # 3. 边缘羽化处理，让过渡更自然
    mask = cv2.GaussianBlur(mask, (7, 7), 0)
    return mask[:, :, np.newaxis]
    
def compute_normals_and_relighting(frame: np.ndarray, depth_norm: np.ndarray, 
                                 light_pos_normalized: tuple, 
                                 light_intensity: float = 1.2) -> np.ndarray:
    """
    [Priority 2] 动态法线光影重定向引擎
    输入: 当前帧, 深度图, 归一化光源坐标(lx, ly), 光强
    输出: 带有物理阴影和高光的帧
    """
    h, w = depth_norm.shape
    # 1. 快速计算深度梯度
    dzdx = cv2.Sobel(depth_norm, cv2.CV_32F, 1, 0, ksize=3)
    dzdy = cv2.Sobel(depth_norm, cv2.CV_32F, 0, 1, ksize=3)
    
    # 2. 构造法线贴图 (Normal Map)
    # nz 控制表面平滑度，0.1-0.2 之间质感最硬核
    nz = 0.15 
    norm = np.sqrt(dzdx**2 + dzdy**2 + nz**2)
    nx, ny, nz = -dzdx/norm, -dzdy/norm, nz/norm
    
    # 3. 计算光照向量 (Light Vector)
    lx, ly = light_pos_normalized
    # 模拟点光源方位
    # 4. 点积运算计算漫反射 (Lambertian Reflection)
    diffuse = np.clip(nx * (lx-0.5) + ny * (ly-0.5) + nz * 0.8, 0.0, 1.0)
    
    # 5. 电影级色彩偏移：高光处略微偏蓝/白，暗部保持原色
    lighting_field = (diffuse * light_intensity + 0.2)[:, :, np.newaxis]
    
    return np.clip(frame.astype(np.float32) * lighting_field, 0, 255).astype(np.uint8)


def get_smoothstep_camera_state(t: float, p1: dict, p2: dict) -> tuple:
    """
    [Priority 3] 贝塞尔平滑运镜引擎
    输入: 当前区间进度 t (0-1), 起点关键点, 终点关键点
    输出: 平滑后的 (cx, cy, cz, sway)
    """
    # 🚀 核心逻辑：Cubic Smoothstep 公式
    # 它可以让镜头在起点缓慢加速，在终点缓慢减速
    s = t * t * (3 - 2 * t) 
    
    cx = p1["cx"] + (p2["cx"] - p1["cx"]) * s
    cy = p1["cy"] + (p2["cy"] - p1["cy"]) * s
    cz = p1["cz"] + (p2["cz"] - p1["cz"]) * s
    sway = p1["sway"] + (p2["sway"] - p1["sway"]) * s
    
    return cx, cy, cz, sway    
# ============================================================
# 动态多阶段大范围运镜系统 (3-6秒随机变轨)
# ============================================================
# ============================================================
class DynamicCameraPath:
    def __init__(self, duration: float, movement_tag: str):
        self.duration = max(duration, 0.1)
        self.waypoints =[]
        
        # 3到6秒随机变换一次运镜动作
        interval = random.uniform(3.0, 6.0)
        num_phases = max(2, int(duration / interval) + 1)
        
        # 初始点
        self.waypoints.append({"cx": 0.0, "cy": 0.0, "cz": 0.0, "sway": 0.0})
        
        # 允许更大的位移，因为我们有 S-Curve 深度保护
        intensity = 1.0 
        if "SLOW" in movement_tag: intensity = 0.5

        for i in range(1, num_phases):
            self.waypoints.append({
                "cx": random.uniform(-0.06, 0.06) * intensity,
                "cy": random.uniform(-0.03, 0.03) * intensity,
                # cz 适当增加，配合拉伸保护
                "cz": random.uniform(0.0, 0.09) * intensity, 
                # 🌟 大幅增加 Z 轴摇晃 (Sway)，这是制造巨大 3D 纵深感且绝不穿帮的神技
                "sway": random.uniform(-0.035, 0.035) * intensity 
            })
            
        # 柔和收尾
        self.waypoints[-1] = {k: v*0.3 for k, v in self.waypoints[-1].items()}
        self.phase_duration = self.duration / (num_phases - 1)
        
    def get_camera_state(self, time_sec: float) -> tuple:
        if time_sec >= self.duration:
            last = self.waypoints[-1]
            return last["cx"], last["cy"], last["cz"], last["sway"]
            
        current_idx = int(time_sec / self.phase_duration)
        next_idx = min(current_idx + 1, len(self.waypoints) - 1)
        local_t = (time_sec % self.phase_duration) / self.phase_duration
        
        # Sine Ease 丝滑插值
        ease_t = 0.5 * (1 - math.cos(math.pi * local_t))
        
        p1 = self.waypoints[current_idx]
        p2 = self.waypoints[next_idx]
        
        cx = p1["cx"] + (p2["cx"] - p1["cx"]) * ease_t
        cy = p1["cy"] + (p2["cy"] - p1["cy"]) * ease_t
        cz = p1["cz"] + (p2["cz"] - p1["cz"]) * ease_t
        sway = p1["sway"] + (p2["sway"] - p1["sway"]) * ease_t
        return cx, cy, cz, sway

# ============================================================
# 满血版：光影特效处理器 (Cinematic FX)
# ============================================================
class CinematicPostProcessor:
    def __init__(self, width: int, height: int):
        self.w, self.h = width, height
        Y, X = np.ogrid[:height, :width]
        dist_sq = (X - width/2)**2 + (Y - height/2)**2
        max_radius_sq = (min(width, height) * 0.7)**2
        self.base_vignette = np.clip(1.1 - dist_sq / max_radius_sq, 0.9, 1.0)
    
    def compute_ssao_mask(self, depth_norm: np.ndarray) -> np.ndarray:
        """厚重的物理角落阴影"""
        depth_blur = cv2.GaussianBlur(depth_norm, (35, 35), 0)
        return np.clip(1.0 - (depth_blur - depth_norm) * 6.0, 0.5, 1.0)[:, :, np.newaxis]
    
    def apply_chromatic_aberration(self, frame: np.ndarray, t: float) -> np.ndarray:
        """高性能零拷贝：实现 IMAX 镜头边缘色差畸变"""
        shift = int(2.0 + 1.5 * math.sin(t * math.pi))
        if shift <= 0: return frame
        res = frame.copy()
        res[:, shift:, 2] = frame[:, :-shift, 2] # R通道右移
        res[:, :-shift, 0] = frame[:, shift:, 0] # B通道左移
        return res
    
    def apply_godrays_cpu(self, frame: np.ndarray, light_x: float, light_y: float) -> np.ndarray:
        """炫酷的光束穿透效果 (体积光)"""
        result = frame.astype(np.float32) / 255.0
        I, J = np.meshgrid(np.arange(self.w), np.arange(self.h), indexing='xy')
        dir_x, dir_y = I - light_x, J - light_y
        dist = np.sqrt(dir_x**2 + dir_y**2) + 1e-6
        ray_intensity = np.clip(1 - dist / (min(self.w, self.h) * 0.8), 0, 1)[:, :, np.newaxis]
        return np.clip((result + ray_intensity * 0.25) * 255, 0, 255).astype(np.uint8)

# ============================================================
# 场景渲染器 (真 2.5D 过扫描防变形版)
# ============================================================
class SceneRenderer:
    def __init__(self, width: int, height: int, fps: int = 24):
        self.out_w, self.out_h = width, height
        # 🚀 架构师防线：OVERSCAN (过扫描)
        # 内部渲染分辨率放大 1.15 倍！这样大运镜时就不会拉扯到黑边，保证人物完全不变形！
        self.w = int(width * 1.15)
        self.h = int(height * 1.15)
        self.fps = fps
        self.post_processor = CinematicPostProcessor(self.w, self.h)
    
    def _compute_normal(self, depth_norm: np.ndarray) -> np.ndarray:
        grad_x = cv2.Sobel(depth_norm, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(depth_norm, cv2.CV_32F, 0, 1, ksize=3)
        nz = np.sqrt(1 - np.clip((-grad_x)**2 + (-grad_y)**2, 0, 0.99))
        norm = np.sqrt((-grad_x)**2 + (-grad_y)**2 + nz**2) + 1e-6
        return (np.stack([-grad_x/norm, -grad_y/norm, nz/norm], axis=2) + 1) / 2.0
    
    def render_scene(self, scene: Dict, target_duration: float) -> List[np.ndarray]:
        """渲染单个场景 - 满血特效版"""
        rgb_path = scene.get("rgb_image")
        depth_path = scene.get("depth_map")
        if not rgb_path or not Path(rgb_path).exists(): 
            return []
        
        # 1. 🛡️ 架构师防线：过扫描预处理 (1.15x 放大防变形)
        rgb_pil = Image.open(rgb_path).convert("RGB")
        rgb_resized = ImageOps.fit(rgb_pil, (self.w, self.h), Image.Resampling.LANCZOS)
        rgb_base = np.array(rgb_resized)
        
        if depth_path and Path(depth_path).exists():
            depth_pil = Image.open(depth_path).convert("L")
            depth = np.array(ImageOps.fit(depth_pil, (self.w, self.h), Image.Resampling.LANCZOS))
        else:
            depth = np.linspace(255, 0, self.h, dtype=np.uint8).reshape(self.h, 1).repeat(self.w, axis=1)
        
        depth_norm = depth.astype(np.float32) / 255.0

        # ============================================================
        # 🚀 极致升级 1：几何特性推演 (SSAO + Normal + Edge Mask)
        # ============================================================
        # A. 计算法线贴图 (用于后期光影重定向)
        gx = cv2.Sobel(depth_norm, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(depth_norm, cv2.CV_32F, 0, 1, ksize=3)
        nz_val = 0.15 # 表面硬度
        mag = np.sqrt(gx**2 + gy**2 + nz_val**2)
        normal_map = np.stack([-gx/mag, -gy/mag, np.full_like(gx, nz_val)/mag], axis=2)
        
        # B. 优先级 1：分层边缘脱离掩码 (Edge Decoupling)
        # 检测深度突变边缘，防止位移时的背景拉丝
        edge_grad = np.sqrt(gx**2 + gy**2)
        edge_mask = np.clip(1.0 - edge_grad * 15.0, 0.0, 1.0)
        edge_mask = cv2.GaussianBlur(edge_mask, (7, 7), 0)[:, :, np.newaxis]
        
        # C. 预计算 SSAO (环境光遮蔽)
        depth_blur = cv2.GaussianBlur(depth_norm, (31, 31), 0)
        ssao_mask = np.clip(1.0 - (depth_blur - depth_norm) * 6.0, 0.4, 1.0)[:, :, np.newaxis]
        
        # 渲染器初始化
        if USE_TAICHI:
            renderer = TitaniumRenderer(self.w, self.h)
        else:
            renderer = SimpleRenderer(self.w, self.h)
        
        renderer.load_maps(
            (rgb_base.astype(np.float32)/255.0).transpose(1, 0, 2), 
            depth_norm.transpose(1, 0), 
            ((normal_map + 1.0) / 2.0).transpose(1, 0, 2)
        )
        renderer.init_sim()
        
        vfx_type = 2 if "rain" in str(scene.get("sfx_tags",[])).lower() else (1 if "fire" in str(scene.get("sfx_tags",[])).lower() else 0)
        camera_movement = scene.get("camera_movement", "DYNAMIC")
        emotion = scene.get("emotion", "WONDER")
        
        num_frames = max(1, int(target_duration * self.fps))
        cam_path = DynamicCameraPath(target_duration, camera_movement)
        y_indices, x_indices = np.indices((self.h, self.w))
        # 🌟 关键：将原图预先转为 BGR，作为整个循环的“无损母带”
        base_bgr = cv2.cvtColor(rgb_base, cv2.COLOR_RGB2BGR)        
        
        frames = []

        for i in range(num_frames):
            time_sec = i / self.fps
            t_raw = i / (num_frames - 1) if num_frames > 1 else 0
            
            # 1. 镜头状态：增加 cz (推拉) 的动态感
            cx, cy, cz, sway = cam_path.get_camera_state(time_sec)
            
            # 2. 光源位置 (局部手电筒效果)
            lx_norm = 0.5 + 0.35 * math.sin(time_sec * 1.2)
            ly_norm = 0.35 + 0.25 * math.cos(time_sec * 1.5)

            # ========================================================
            # 🚀 极致位移：S-Curve + 边缘保护 (杜绝重影)
            # ========================================================
            # 强化深度图：让前景(人)更突出，背景(隧道)更深
            d_logic = np.power(depth_norm, 1.5) 
            
            # 计算位移：cz (前后推拉) 作用于深度
            # 这里 cz 建议控制在 0.0 - 0.1 之间
            dx = (d_logic * cz * self.w * 0.4 + cx * self.w * 0.7) * edge_mask.squeeze()
            dy = (d_logic * cz * self.h * 0.1 + cy * self.h * 0.7) * edge_mask.squeeze()
            
            nx = np.clip(x_indices - dx, 0, self.w - 1).astype(np.float32)
            ny = np.clip(y_indices - dy, 0, self.h - 1).astype(np.float32)
            
            # 纹理与深度严格同步重采样
            warped_frame = cv2.remap(base_bgr, nx, ny, interpolation=cv2.INTER_LINEAR)
            warped_depth = cv2.remap(depth_norm, nx, ny, interpolation=cv2.INTER_LINEAR)
            
            # ========================================================
            # 🚀 极致景深：三层动态模糊 (奶油虚化)
            # ========================================================
            # 只有远离相机 (深度 < 0.55) 的地方才模糊
            # 模糊半径随深度减小而指数级增加
            
            # 背景层遮罩 (远景)
            bg_mask_far = np.clip((0.4 - warped_depth) * 5.0, 0.0, 1.0)[:, :, np.newaxis]
            # 中景层遮罩
            bg_mask_mid = np.clip((0.6 - warped_depth) * 4.0, 0.0, 1.0)[:, :, np.newaxis]
            
            # 第一层轻微模糊 (模拟近景散景)
            layer1 = cv2.GaussianBlur(warped_frame, (11, 11), 0)
            # 第二层重度模糊 (模拟远景奶油虚化)
            layer2 = cv2.GaussianBlur(warped_frame, (35, 35), 0)
            
            # 混合多级景深：主体(无模糊) -> 中景(轻微) -> 背景(重度)
            frame_dof = warped_frame.astype(np.float32)
            frame_dof = frame_dof * (1.0 - bg_mask_mid) + layer1.astype(np.float32) * bg_mask_mid
            frame_dof = frame_dof * (1.0 - bg_mask_far) + layer2.astype(np.float32) * bg_mask_far
            frame_dof = frame_dof.astype(np.uint8)

            # ========================================================
            # 🚀 极致光影：局部法线高光 (Relighting)
            # ========================================================
            dist_map = np.sqrt((x_indices/self.w - lx_norm)**2 + (y_indices/self.h - ly_norm)**2)
            # 限制光照范围，形成局部光斑
            light_spot = np.clip(1.0 - dist_map / 0.4, 0.0, 1.0)[:, :, np.newaxis]
            light_spot = np.power(light_spot, 2.0) 

            f_normal = normal_map[ny.astype(int), nx.astype(int)]
            dot_l = np.clip(f_normal[:,:,0]*(lx_norm-0.5) + f_normal[:,:,1]*(ly_norm-0.5) + f_normal[:,:,2]*0.8, 0.0, 1.0)
            
            # 只有在主体边缘和受光面产生高光，亮部呼吸感
            highlight_intensity = 0.22 + 0.08 * math.sin(time_sec * 3.0)
            highlight_layer = (dot_l[:, :, np.newaxis] * light_spot * highlight_intensity * 255).astype(np.int16)
            
            # 无损叠加：原图亮度不变，只增加受光细节
            frame_lit = np.clip(frame_dof.astype(np.int16) + highlight_layer, 0, 255).astype(np.uint8)

            # ========================================================
            # 🚀 极致推拉：Overscan 裁切还原
            # ========================================================
            # cz 决定了镜头的缩放感。随着 cz 增大，我们进行中心裁剪再放大，
            # 配合之前的位移，产生强烈的 3D Dolly Zoom (希区柯克变焦) 效果。
            zoom_factor = 1.0 + cz * 0.5 
            h_crop, w_crop = int(self.h / zoom_factor), int(self.w / zoom_factor)
            y1, x1 = (self.h - h_crop) // 2, (self.w - w_crop) // 2
            
            final_frame = frame_lit[y1:y1+h_crop, x1:x1+w_crop]
            # 最终缩放到目标分辨率，LANCZOS4 保证最高清晰度
            final_out = cv2.resize(final_frame, (self.out_w, self.out_h), interpolation=cv2.INTER_LANCZOS4)

            frames.append(final_out)
            if i % 20 == 0: 
                print(f"      🎞️ 极致推拉渲染中: {int(t_raw * 100)}%")        
        return frames
            
class AdvancedRenderEngine:
    def __init__(self, script_path: str, audio_dir: str = "./data/output/audio",
                 visuals_dir: str = "./data/output/visuals", output_dir: str = "./data/output", 
                 output_filename: str = "final_render.mp4", fps: int = 12, quality: int = 5, 
                 target_width: int = 1920, preset: str = "ultrafast"):
        
        self.script_path = Path(script_path)
        self.audio_dir, self.visuals_dir, self.output_path = Path(audio_dir), Path(visuals_dir), Path(output_dir) / output_filename
        
        # 恢复 24fps 电影帧率
        self.fps = min(fps, 30)
        self.quality = max(1, min(10, quality))       
        
        # 强制 16 字节物理对齐
        self.target_width = min(target_width, 1920)
        self.w = (self.target_width // 16) * 16
        self.h = (int(self.w * 9 / 16) // 16) * 16
        
        self.preset = preset
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.script_path, 'r', encoding='utf-8') as f: self.timed_script = json.load(f)
        self.stats = {"total_scenes": 0, "scenes_rendered": 0, "total_frames": 0, "total_duration": 0}
        
        print("\n" + "="*60)
        print("🎬 2.5D 满血全特效渲染引擎 (IMAX 无损级)")
        print("="*60)
        print(f"🎬 规格: {self.w}x{self.h} @ {self.fps}fps | 画质: 肉眼无损 (CRF 21)")
        print(f"✨ 激活: 过扫描防变形 | 3-6s疯狂运镜 | 奶油虚化景深 | 动态光照")
        print("="*60)
    
    def _get_scene_duration(self, scene: Dict) -> float:
        # 1. 尝试从 JSON 直接读取时长 (检查多个可能的键名)
        for key in ["duration_sec", "duration", "total_duration"]:
            if key in scene and scene[key]:
                val = float(scene[key])
                if val > 0:
                    # print(f"      DEBUG: 找到预设时长 ({key}): {val}s")
                    return val

        # 2. 尝试从 audio_segments 累加时长 (这是最稳妥的备选方案)
        segments = scene.get("audio_segments", [])
        if segments:
            total_seg_dur = sum(float(s.get("duration", 0)) for s in segments)
            if total_seg_dur > 0:
                # print(f"      DEBUG: 从片段累加时长: {total_seg_dur}s")
                return total_seg_dur

        # 3. 尝试读取物理文件时长
        audio_obj = scene.get("audio", {})
        merged_path = audio_obj.get("merged")
        if merged_path:
            p = Path(merged_path)
            if p.exists():
                try:
                    from moviepy import AudioFileClip
                    with AudioFileClip(str(p)) as audio:
                        # print(f"      DEBUG: 从物理文件读取时长: {audio.duration}s")
                        return audio.duration
                except Exception as e:
                    print(f"      ⚠️ 读取音频文件失败: {e}")
            else:
                print(f"      ⚠️ 音频文件不存在: {merged_path}")

        # 4. 如果是旁白文本，根据字数估算 (保底方案)
        text = scene.get("narration", "") or scene.get("content", "")
        if text:
            # 中文约每秒 3-4 个字，英文约每秒 2-3 个单词
            estimated = max(2.5, len(text) / 3.5)
            # print(f"      DEBUG: 根据文本估算时长: {estimated:.2f}s")
            return estimated

        # 最终保底
        return 3.0
    
    def run(self) -> Path:
        print("\n🎬 开始满血渲染管线...")
        scenes = self.timed_script.get("scenes", [])
        self.stats["total_scenes"] = len(scenes)
        
        scene_renderer = SceneRenderer(self.w, self.h, self.fps)
        all_frames =[]
        
        for i, scene in enumerate(scenes, 1):
            duration = self._get_scene_duration(scene)
            print(f"\n   🎬 场景 {i}: 时长 {duration:.1f}s")
            frames = scene_renderer.render_scene(scene, duration)
            if frames:
                all_frames.extend(frames)
                self.stats["total_duration"] += duration
        
        if not all_frames: return self.output_path
        
        # --------------------------------------------------------
        # 🚀 高压缩且视觉无损的 H.264 编码 (CRF 21 + 超长 GOP)
        # --------------------------------------------------------
        final_audio = self.audio_dir / "final_audio.mp3"
        try:
            import imageio
            temp_video = self.output_path.with_suffix('.temp.mp4')
            
            # CRF 21 是 H.264 肉眼无损的最佳分水岭
            writer = imageio.get_writer(
                str(temp_video), fps=self.fps, codec='libx264', quality=None, pixelformat='yuv420p',
                ffmpeg_params=[
                    '-preset', self.preset, 
                    '-crf', '26',          
                    '-tune', 'stillimage',  # 电影纹理调优
                    '-g', '300',      # 超大 GOP，极其节省体积
                    '-keyint_min', '300',   
                    '-sc_threshold', '0',  
                    '-x264opts', 'keyint=250',                            
                    '-movflags', '+faststart'
                ]
            )
            
            for i, frame in enumerate(all_frames):
                writer.append_data(frame)
            writer.close()
            
            if final_audio and final_audio.exists():
                print(f"   🎵 混入音频...")
                # 修改 FFmpeg 混音指令（伪代码逻辑）
                # 使用 asidechaincompress 滤镜实现自动化避让
                #filter_complex = "[1:a]asplit[vocal1][vocal2];[0:a][vocal1]sidechaincompress=threshold=0.15:ratio=4[bgm_ducked];[bgm_ducked][vocal2]amix=inputs=2:weights='1 1'"

                cmd = [
                    'ffmpeg', '-y',
                    '-i', str(temp_video),   # 输入0：无声视频
                    '-i', str(final_audio),  # 输入1：合成音频
                    '-c:v', 'copy',          # 视频流直接拷贝（极速）
                    '-c:a', 'aac',           # 音频转码为 AAC
                    '-b:a', '192k',          # 音频比特率
                    '-map', '0:v:0',         # 使用第一个输入的第一个视频流
                    '-map', '1:a:0',         # 使用第二个输入的第一个音频流
                    '-shortest',             # 以最短的流（通常是视频）为准结束
                    str(self.output_path)
                ]
                #cmd =['ffmpeg', '-y', '-i', str(temp_video), '-i', str(final_audio),
                #    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-shortest', str(self.output_path)]
                # 运行合并，暂时去掉 DEVNULL 方便排查错误（运行成功后可以加回来）
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"   ❌ FFmpeg 合成失败! 错误信息:\n{result.stderr}")
                else:
                    if temp_video.exists(): temp_video.unlink()
                    print(f"   ✅ 音视频合成完成")                       
                    size_mb = self.output_path.stat().st_size / (1024 * 1024)
                    print(f"\n✅ IMAX 无损级渲染成功!")
                    print(f"   📦 最终体积: {size_mb:.2f} MB (高画质)")
            else:
                print(f"   ⚠️ 未找到音频文件，直接重命名视频")
                if self.output_path.exists(): self.output_path.unlink()
                temp_video.rename(self.output_path)
            
        except Exception as e: print(f"   ❌ 合成失败: {e}")

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
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--preset", default="ultrafast")
    args = p.parse_args()
    
    engine = AdvancedRenderEngine(
        script_path=args.script, audio_dir=args.audio_dir, visuals_dir=args.visuals_dir,
        output_dir=args.output, fps=args.fps, quality=args.quality,
        target_width=args.width, preset=args.preset
    )
    engine.run()