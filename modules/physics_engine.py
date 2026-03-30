import taichi as ti

@ti.data_oriented
class TitaniumRenderer:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.color = ti.Vector.field(3, dtype=ti.f32, shape=(w, h))
        self.depth = ti.field(dtype=ti.f32, shape=(w, h))
        self.normal = ti.Vector.field(3, dtype=ti.f32, shape=(w, h))
        self.screen = ti.Vector.field(3, dtype=ti.f32, shape=(w, h))
        self.godray_buf = ti.Vector.field(3, dtype=ti.f32, shape=(w, h))
        self.z_buf = ti.field(dtype=ti.f32, shape=(w, h))
        self.max_p = 20000  # 增加粒子数量以增强效果
        self.p_pos = ti.Vector.field(3, dtype=ti.f32, shape=self.max_p)
        self.p_vel = ti.Vector.field(3, dtype=ti.f32, shape=self.max_p)
        self.p_col = ti.Vector.field(3, dtype=ti.f32, shape=self.max_p)
        self.p_active = ti.field(dtype=ti.i32, shape=self.max_p)
        self.p_life = ti.field(dtype=ti.f32, shape=self.max_p)  # 粒子生命周期
        self.max_b = 200
        self.b_pos = ti.Vector.field(2, dtype=ti.f32, shape=self.max_b)
        self.b_vel = ti.Vector.field(2, dtype=ti.f32, shape=self.max_b)
        self.b_active = ti.field(dtype=ti.i32, shape=self.max_b)

    @ti.kernel
    def init_sim(self):
        for i in range(self.max_p):
            self.p_active[i] = 0
            self.p_life[i] = 0.0
        for i in range(self.max_b):
            self.b_active[i] = 0
            self.b_pos[i] = ti.Vector([ti.random()*self.w, ti.random()*self.h])
            self.b_vel[i] = ti.Vector([ti.random()-0.5, ti.random()-0.5]).normalized() * 3.0

    def load_maps(self, c, d, n):
        self.color.from_numpy(c); self.depth.from_numpy(d); self.normal.from_numpy(n)

    @ti.func
    def spawn_p(self, type: int):
        slot = int(ti.random() * self.max_p)
        if self.p_active[slot] == 0:
            self.p_active[slot] = 1
            self.p_life[slot] = 1.0  # 完整生命周期
            if type == 1:  # FIRE (底部中心)
                off = (ti.random() + ti.random() - 1.0) * 0.15
                self.p_pos[slot] = ti.Vector([(0.5+off)*self.w, self.h-10, 0.1 + ti.random()*0.2])
                self.p_vel[slot] = ti.Vector([(ti.random()-0.5)*3, -ti.random()*6-4, (ti.random()-0.5)*0.5])
                temp = ti.random()
                if temp < 0.3:
                    self.p_col[slot] = ti.Vector([1.0, 0.2, 0.05])  # 红色火焰
                elif temp < 0.6:
                    self.p_col[slot] = ti.Vector([1.0, 0.6, 0.1])  # 橙色火焰
                else:
                    self.p_col[slot] = ti.Vector([1.0, 0.9, 0.3])  # 黄色火焰
            elif type == 2:  # RAIN (雨滴)
                self.p_pos[slot] = ti.Vector([ti.random()*self.w, -10, ti.random()*0.5])
                self.p_vel[slot] = ti.Vector([(ti.random()-0.5)*2, 18.0 + ti.random()*8, 0])
                self.p_col[slot] = ti.Vector([0.85, 0.9, 1.0])
            elif type == 0:  # SNOW (雪花)
                self.p_pos[slot] = ti.Vector([ti.random()*self.w, -10, ti.random()*0.8])
                self.p_vel[slot] = ti.Vector([(ti.random()-0.5)*3, 2.5 + ti.random()*2, 0])
                self.p_col[slot] = ti.Vector([0.95, 0.98, 1.0])
            elif type == 3:  # HORROR (恐怖粒子)
                self.p_pos[slot] = ti.Vector([ti.random()*self.w, self.h + 10, ti.random()*0.3])
                self.p_vel[slot] = ti.Vector([(ti.random()-0.5)*2, -3 - ti.random()*2, 0])
                self.p_col[slot] = ti.Vector([0.1, 0.05, 0.02])
            elif type == 6:  # OCEAN (水面波动粒子)
                self.p_pos[slot] = ti.Vector([ti.random()*self.w, self.h*0.7 + ti.random()*self.h*0.2, ti.random()*0.1])
                self.p_vel[slot] = ti.Vector([(ti.random()-0.5)*1.5, (ti.random()-0.5)*0.5, 0])
                self.p_col[slot] = ti.Vector([0.1, 0.3, 0.6])

    @ti.kernel
    def update_sim(self, dt: ti.f32, vfx: int, high: ti.f32, has_boids: int, audio_high: ti.f32):
        if vfx >= 0:
            spawn_count = 40 if high > 0.5 else 15  # 增加粒子生成数量
            for _ in range(spawn_count):
                self.spawn_p(vfx)
        for i in range(self.max_p):
            if self.p_active[i]:
                # 粒子物理更新
                if vfx == 1:  # 火焰上升
                    self.p_vel[i].y -= 0.1  # 重力
                    self.p_vel[i].x += (ti.random()-0.5)*0.2
                    self.p_life[i] -= 0.02  # 火焰衰减
                elif vfx == 2:  # 雨滴
                    self.p_vel[i].y += 0.2  # 重力加速度
                elif vfx == 0:  # 雪花
                    self.p_vel[i].x += (ti.random()-0.5)*0.1  # 风效果
                    self.p_life[i] -= 0.005
                elif vfx == 6:  # 水面
                    self.p_vel[i].y += ti.math.sin(self.p_pos[i].x * 0.1) * 0.05
                    self.p_vel[i] *= 0.98  # 阻尼

                self.p_pos[i] += self.p_vel[i] + ti.Vector([ti.random()-0.5, 0, 0]) * audio_high * 3.0

                # 粒子生命周期和边界检查
                if self.p_pos[i].y > self.h + 20 or self.p_pos[i].y < -20 or self.p_life[i] <= 0.0:
                    self.p_active[i] = 0
        if has_boids:
            for i in range(self.max_b):
                p, v = self.b_pos[i], self.b_vel[i]
                center = ti.Vector([self.w/2, self.h/2])
                v = (v + (center-p).normalized()*0.05 + ti.Vector([ti.random()-0.5,ti.random()-0.5])*0.2).normalized() * 3.5
                p += v
                if p.x<0 or p.x>self.w or p.y<0 or p.y>self.h:
                    p = center
                self.b_pos[i], self.b_vel[i] = p, v

    @ti.kernel
    def render_frame(self, t: ti.f32, cam_x: ti.f32, cam_y: ti.f32, cam_zoom: ti.f32,
                     l_pos: ti.types.vector(3, ti.f32), l_mode: int,
                     shadow_str: ti.f32, sway: ti.f32, bass: ti.f32, l_intensity: ti.f32):
        for I in ti.grouped(self.screen):
            self.screen[I], self.z_buf[I], self.godray_buf[I] = ti.Vector([0.,0.,0.]), 999.0, ti.Vector([0.,0.,0.])

        cx, cy = self.w * 0.5, self.h * 0.5
        for i, j in self.color:
            base, d, n = self.color[i, j], self.depth[i, j], self.normal[i, j]*2-1
            off_x = 0.0
            if sway > 0.0 and d < 0.6:
                off_x = ti.math.sin(t*2.5 + j*0.03) * 5.0 + ti.math.sin(t*1.2 + i*0.02) * 2.0
            z_world = d * 300.0  # 增强深度感
            zoom_f = 1.0 + cam_zoom * (d * 2.0 + 0.2)
            fx = cx + (float(i) + off_x - cx) * zoom_f - cam_x * (z_world + 80) * 0.025  # 增强视差
            fy = cy + (float(j) - cy) * zoom_f - cam_y * (z_world + 80) * 0.025
            px, py = int(fx), int(fy)

            # 3x3 Splatting 极致填充
            for dx, dy in ti.ndrange((-1, 2), (-1, 2)):
                sx, sy = px+dx, py+dy
                if 0 <= sx < self.w and 0 <= sy < self.h:
                    depth_key = z_world # 修正：使用正深度
                    if depth_key < ti.atomic_min(self.z_buf[sx, sy], depth_key):
                        lv = (l_pos - ti.Vector([float(sx), float(sy), 80.])).normalized()
                        view_v = ti.Vector([0.0, 0.0, 1.0])
                        diff = max(0.0, n.dot(lv))
                        half = (lv + view_v).normalized()
                        spec = pow(max(0.0, n.dot(half)), 60.0)
                        fresnel = 0.15 + 0.85 * pow(1.0 - max(0.0, n.dot(view_v)), 3.0)
                        ao = 1.0 - (1.0 - d) * shadow_str * 0.8
                        # 动态光照效果
                        light = (0.35 * ao) + (diff * 0.8 + spec * 0.6 + fresnel * 0.3) * l_intensity + bass * 0.15
                        col = base * light
                        a, b, c, de, e = 2.51, 0.03, 2.43, 0.59, 0.14
                        col = (col*(a*col+b))/(col*(c*col+de)+e)
                        self.screen[sx, sy] = ti.math.clamp(col, 0.0, 1.0)
                        # 修正判据：如果当前深度确实是可见的，才更新godray buffer
                        if col.norm() > 0.95 and d < 0.35:
                            self.godray_buf[sx, sy] = col

    @ti.kernel
    def apply_godrays(self, lx: ti.f32, ly: ti.f32):
        l_pos = ti.Vector([lx, ly])
        for i, j in self.screen:
            uv, accum, decay = ti.Vector([float(i), float(j)]), ti.Vector([0.,0.,0.]), 1.0
            delta = (uv - l_pos) * (1.0 / (float(self.w) * 0.9))
            for k in range(30):
                uv -= delta
                sx, sy = int(uv.x), int(uv.y)
                if 0 <= sx < self.w and 0 <= sy < self.h:
                    accum += self.godray_buf[sx, sy] * decay * 0.035
                    decay *= 0.95
            self.screen[i, j] += accum * 1.8

    @ti.kernel
    def render_particles(self):
        for i in range(self.max_p):
            if self.p_active[i]:
                x, y = int(self.p_pos[i].x), int(self.p_pos[i].y)
                if 0 <= x < self.w and 0 <= y < self.h:
                    # 粒子大小根据深度调整
                    size = 2.0 + self.p_pos[i].z * 3.0
                    life = self.p_life[i]
                    alpha = ti.math.clamp(life, 0.3, 1.0)
                    color = self.p_col[i] * alpha
                    # 粒子光晕效果
                    for dx, dy in ti.ndrange((-1, 2), (-1, 2)):
                        sx, sy = x + dx, y + dy
                        if 0 <= sx < self.w and 0 <= sy < self.h:
                            dist = ti.math.sqrt(float(dx*dx + dy*dy)) / size
                            if dist <= 1.0:
                                weight = 1.0 - dist
                                self.screen[sx, sy] += color * weight * 0.3

    @ti.kernel
    def render_water_effect(self, t: ti.f32):
        # 水面波动效果
        for i, j in self.color:
            d = self.depth[i, j]
            if d > 0.7:  # 假设深度较大的区域是水面
                wave1 = ti.math.sin(t*3.0 + i*0.02 + j*0.01) * 0.05
                wave2 = ti.math.sin(t*1.5 + i*0.01 + j*0.02) * 0.03
                offset = wave1 + wave2
                # 调整水面颜色
                self.screen[i, j] *= (1.0 + offset * 0.3)
                # 水面反光
                self.screen[i, j] += ti.Vector([0.1, 0.2, 0.3]) * offset * 0.5

    def get_frame(self):
        return self.screen.to_numpy().transpose(1, 0, 2)