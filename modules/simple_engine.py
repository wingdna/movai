import numpy as np
import cv2
import math


class SimpleRenderer:
    """不依赖Taichi的简化渲染器，为老旧Intel CPU优化"""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.color = None
        self.depth = None
        self.normal = None
        self.screen = None
        # 进一步减少粒子数量以提升性能（CPU 渲染优化）
        self.max_p = 2000
        self.p_pos = np.zeros((self.max_p, 3), dtype=np.float32)
        self.p_vel = np.zeros((self.max_p, 3), dtype=np.float32)
        self.p_col = np.zeros((self.max_p, 3), dtype=np.float32)
        self.p_active = np.zeros(self.max_p, dtype=np.int32)
        self.p_life = np.zeros(self.max_p, dtype=np.float32)

    def load_maps(self, c, d, n):
        self.color = c
        self.depth = d
        self.normal = n
        self.screen = np.zeros((self.w, self.h, 3), dtype=np.float32)

    def init_sim(self):
        self.p_active[:] = 0
        self.p_life[:] = 0.0

    def spawn_p(self, type):
        # 找到第一个未激活的粒子槽
        slot_idx = np.where(self.p_active == 0)[0]
        if len(slot_idx) > 0:
            slot = slot_idx[0]
            self.p_active[slot] = 1
            self.p_life[slot] = 1.0

            if type == 1:  # 火焰
                off = (np.random.rand() + np.random.rand() - 1.0) * 0.15
                self.p_pos[slot] = [(0.5 + off) * self.w, self.h - 10, 0.1 + np.random.rand() * 0.2]
                self.p_vel[slot] = [(np.random.rand() - 0.5) * 3, -np.random.rand() * 6 - 4, (np.random.rand() - 0.5) * 0.5]
                temp = np.random.rand()
                if temp < 0.3:
                    self.p_col[slot] = [1.0, 0.2, 0.05]
                elif temp < 0.6:
                    self.p_col[slot] = [1.0, 0.6, 0.1]
                else:
                    self.p_col[slot] = [1.0, 0.9, 0.3]

            elif type == 2:  # 雨
                self.p_pos[slot] = [np.random.rand() * self.w, -10, np.random.rand() * 0.5]
                self.p_vel[slot] = [(np.random.rand() - 0.5) * 2, 18.0 + np.random.rand() * 8, 0]
                self.p_col[slot] = [0.85, 0.9, 1.0]

            elif type == 0:  # 雪
                self.p_pos[slot] = [np.random.rand() * self.w, -10, np.random.rand() * 0.8]
                self.p_vel[slot] = [(np.random.rand() - 0.5) * 3, 2.5 + np.random.rand() * 2, 0]
                self.p_col[slot] = [0.95, 0.98, 1.0]

            elif type == 6:  # 水面
                self.p_pos[slot] = [np.random.rand() * self.w, self.h * 0.7 + np.random.rand() * self.h * 0.2, np.random.rand() * 0.1]
                self.p_vel[slot] = [(np.random.rand() - 0.5) * 1.5, (np.random.rand() - 0.5) * 0.5, 0]
                self.p_col[slot] = [0.1, 0.3, 0.6]

    def update_sim(self, dt, vfx, high, has_boids, audio_high):
        if vfx >= 0:
            spawn_count = 5 if high > 0.5 else 2  # 大幅减少粒子生成数量
            for _ in range(spawn_count):
                self.spawn_p(vfx)

        # 更新粒子（简化计算）
        active_indices = np.where(self.p_active == 1)[0]
        for i in active_indices:
            if vfx == 1:  # 火焰
                self.p_vel[i][1] -= 0.05
                self.p_vel[i][0] += (np.random.rand() - 0.5) * 0.1
                self.p_life[i] -= 0.01
            elif vfx == 2:  # 雨
                self.p_vel[i][1] += 0.1
            elif vfx == 0:  # 雪
                self.p_vel[i][0] += (np.random.rand() - 0.5) * 0.05
                self.p_life[i] -= 0.0025
            elif vfx == 6:  # 水面
                self.p_vel[i][1] += math.sin(self.p_pos[i][0] * 0.1) * 0.025
                self.p_vel[i] *= 0.99

            self.p_pos[i] += self.p_vel[i] + np.array([(np.random.rand() - 0.5), 0, 0]) * audio_high * 1.0

            # 检查边界和生命周期
            if (self.p_pos[i][1] > self.h + 20 or self.p_pos[i][1] < -20 or
                    self.p_life[i] <= 0.0):
                self.p_active[i] = 0
                self.p_life[i] = 0.0

    def render_titan(self, t, cam_x, cam_y, cam_zoom, l_pos, l_mode, shadow_str, sway, bass, l_intensity):
        # 使用累加方式而不是覆盖，避免最后一个像素覆盖问题
        # 先清空，但累加而不是覆盖
        self.screen.fill(0.0)

        cx, cy = self.w * 0.5, self.h * 0.5
        # 简化网格操作，避免大量内存分配（性能优化）
        I, J = np.meshgrid(np.arange(self.w), np.arange(self.h), indexing='ij')
        base = self.color
        d = self.depth
        n = self.normal * 2 - 1

        off_x = np.zeros_like(d)
        mask_sway = (sway > 0.0) & (d < 0.6)
        if np.any(mask_sway):
            off_x[mask_sway] = np.sin(t * 2.5 + J[mask_sway] * 0.03) * 1.0 + np.sin(t * 1.2 + I[mask_sway] * 0.02) * 0.5

        z_world = d * 100.0  # 大幅减少景深范围
        zoom_f = 1.0 + cam_zoom * (d * 1.0 + 0.1)  # 减少缩放强度
        fx = cx + (I + off_x - cx) * zoom_f - cam_x * (z_world + 60) * 0.025
        fy = cy + (J - cy) * zoom_f - cam_y * (z_world + 60) * 0.025

        px = np.round(fx).astype(np.int32)
        py = np.round(fy).astype(np.int32)

        # 极其简化的光照计算（最大化性能）
        lx, ly, lz = l_pos
        pos_z = 60.0

        # 使用简单的方向光计算
        diff = np.maximum(0.0, n[:,:,2])
        ao = 1.0 - (1.0 - d) * shadow_str * 0.3

        light = (0.5 * ao) + (diff * 0.6) * l_intensity + bass * 0.05
        light = light[:, :, np.newaxis]
        col = base * light

        # 简化 tone mapping
        col = np.clip(col, 0.0, 1.0)
        col = np.power(col, 0.85)

        # 正确的像素映射 - 使用累加避免覆盖伪影
        mask = (px >= 0) & (px < self.w) & (py >= 0) & (py < self.h)
        if np.any(mask):
            px_valid = px[mask]
            py_valid = py[mask]
            col_valid = col[mask]
            # 累加而不是覆盖
            self.screen[px_valid, py_valid] += col_valid

    def apply_godrays(self, lx, ly):
        # 简化的上帝之光效果（性能优化版本）
        I, J = np.meshgrid(np.arange(self.w), np.arange(self.h), indexing='ij')
        uv = np.stack([I, J], axis=-1).astype(np.float32)
        l_pos = np.array([lx, ly], dtype=np.float32)
        delta = (uv - l_pos) * (1.0 / (self.w * 0.9))

        accum = np.zeros((self.w, self.h, 3), dtype=np.float32)
        decay = 1.0
        curr_uv = uv.copy()

        for k in range(15):  # 减少采样次数
            curr_uv -= delta
            sx = np.round(curr_uv[:, :, 0]).astype(np.int32)
            sy = np.round(curr_uv[:, :, 1]).astype(np.int32)

            mask = (sx >= 0) & (sx < self.w) & (sy >= 0) & (sy < self.h)
            # 正确的像素累积
            sx_valid = sx[mask]
            sy_valid = sy[mask]
            accum[sx_valid, sy_valid] += self.screen[sx_valid, sy_valid] * decay * 0.035
            decay *= 0.95

        self.screen += accum * 1.2  # 减少强度

    def render_particles(self):
        active_indices = np.where(self.p_active == 1)[0]
        if len(active_indices) == 0: return
        
        pos = self.p_pos[active_indices]
        col = self.p_col[active_indices]
        life = self.p_life[active_indices]
        
        # 批量计算粒子属性
        x, y = np.round(pos[:, 0]).astype(np.int32), np.round(pos[:, 1]).astype(np.int32)
        size = 2.0 + pos[:, 2] * 3.0
        alpha = np.clip(life, 0.3, 1.0)
        p_color = col * alpha[:, np.newaxis]
        
        # 遍历 3x3 splatting (粒子数量远小于像素数量，遍历粒子是高效的)
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                sx, sy = x + dx, y + dy
                mask = (sx >= 0) & (sx < self.w) & (sy >= 0) & (sy < self.h)
                if not np.any(mask): continue
                
                # 计算距离权重
                dist = np.sqrt(dx*dx + dy*dy) / size[mask]
                w = np.maximum(0.0, 1.0 - dist)
                
                # 使用 np.add.at 保证索引重复时正确累加 (虽然 3x3 里不会自身重复，但多个粒子可能映射到同一像素)
                np.add.at(self.screen, (sx[mask], sy[mask]), p_color[mask] * w[:, np.newaxis] * 0.3)

    def render_water_effect(self, t):
        # 轻量级水面反射和波动效果
        mask = self.depth > 0.7
        if not np.any(mask): return

        I, J = np.indices((self.w, self.h))
        I_m, J_m = I[mask], J[mask]

        # 水面波动
        wave1 = np.sin(t * 2.0 + I_m * 0.02 + J_m * 0.01) * 0.03
        wave2 = np.sin(t * 1.0 + I_m * 0.01 + J_m * 0.02) * 0.02
        offset = (wave1 + wave2)[:, np.newaxis]

        # 水面闪烁
        flicker = np.sin(t * 5.0 + I_m * 0.03) * 0.02
        self.screen[mask] *= (1.0 + offset * 0.2 + flicker[:, np.newaxis] * 0.1)

        # 反射效果（简化版）
        self.screen[mask] += np.array([0.05, 0.1, 0.15]) * offset * 0.3

    def render_hbloom(self):
        # 轻量级屏幕空间光晕
        # 高斯模糊
        blurred = cv2.GaussianBlur(self.screen, (7, 7), 0)
        # 亮度阈值
        brightness = np.max(self.screen, axis=2)
        mask = brightness > 0.8
        self.screen[mask] += blurred[mask] * 0.2

    def render_film_grain(self):
        # 轻量级胶片颗粒效果
        grain = np.random.rand(self.w, self.h, 3) * 0.03 - 0.015
        self.screen += grain

    def get_frame(self):
        # 添加轻量级后期特效
        self.render_hbloom()
        self.render_film_grain()
        return np.clip(self.screen, 0.0, 1.0).transpose(1, 0, 2)