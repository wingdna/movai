# models/schemas.py
"""
工业级数据模型 - 使用 Pydantic 进行强校验
"""
from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from datetime import datetime


# ========== 枚举类型（强制约束） ==========

class CameraMovement(str, Enum):
    """运镜方式枚举 - 后端只能识别这些值"""
    STATIC = "STATIC"
    Z_DOLLY_IN = "Z_DOLLY_IN"
    Z_DOLLY_OUT = "Z_DOLLY_OUT"
    PAN_LEFT = "PAN_LEFT"
    PAN_RIGHT = "PAN_RIGHT"
    TILT_UP = "TILT_UP"
    TILT_DOWN = "TILT_DOWN"
    HANDHELD_SHAKE = "HANDHELD_SHAKE"
    STATIC_JITTER = "STATIC_JITTER"
    SLOW_PAN = "SLOW_PAN"
    RAPID_CUT = "RAPID_CUT"
    ZOOM_IN = "ZOOM_IN"
    ZOOM_OUT = "ZOOM_OUT"


class EmotionType(str, Enum):
    """情绪类型枚举"""
    NEUTRAL = "NEUTRAL"
    TENSION = "TENSION"
    FEAR = "FEAR"
    HORROR = "HORROR"
    MYSTERY = "MYSTERY"
    REVELATION = "REVELATION"
    JOY = "JOY"
    SADNESS = "SADNESS"
    ANGER = "ANGER"
    DESPAIR = "DESPAIR"
    HOPE = "HOPE"


class CharacterStatus(str, Enum):
    """角色状态枚举"""
    ALIVE = "ALIVE"
    INJURED = "INJURED"
    CRITICAL = "CRITICAL"
    DEAD = "DEAD"
    MUTATED = "MUTATED"
    MISSING = "MISSING"
    POSSESSED = "POSSESSED"
    TRANSFORMED = "TRANSFORMED"


class SFXType(str, Enum):
    """音效类型枚举"""
    AMBIENT = "AMBIENT"
    FOOTSTEPS = "FOOTSTEPS"
    DOOR = "DOOR"
    ALARM = "ALARM"
    WHISPER = "WHISPER"
    EXPLOSION = "EXPLOSION"
    GUNSHOT = "GUNSHOT"
    HEARTBEAT = "HEARTBEAT"
    STATIC = "STATIC"
    SCREAM = "SCREAM"
    METALLIC = "METALLIC"
    ORGANIC = "ORGANIC"


# ========== Pydantic 模型 ==========

class CharacterVisual(BaseModel):
    """角色视觉字典 - 锁定外貌，不可篡改"""
    name: str = Field(..., description="角色名称", min_length=1, max_length=20)
    identity: str = Field(..., description="身份（必须符合风格设定）", min_length=2, max_length=50)
    personality_traits: List[str] = Field(default_factory=list, max_items=5)
    
    # 锁定的视觉锚点（不可篡改，生成时由代码拼接）
    visual_anchor: str = Field(..., description="固定的视觉Prompt锚点", min_length=10)
    
    voice_profile: str = Field(..., description="TTS音色特征")
    
    # 状态机强约束
    initial_hp: int = Field(default=100, ge=0, le=100)
    initial_status: CharacterStatus = Field(default=CharacterStatus.ALIVE)
    initial_location: str = Field(default="起点", description="初始位置")
    
    @validator('identity')
    def validate_identity(cls, v, values):
        """检查身份是否符合风格"""
        # 这个验证会在运行时由风格映射注入具体规则
        forbidden = ['书生', '秀才', '举人', '小姐', '丫鬟', '老媪']
        for word in forbidden:
            if word in v:
                raise ValueError(f"身份 '{v}' 包含禁用词 '{word}'")
        return v


class Beat(BaseModel):
    """节拍表 - 剧情骨架"""
    beat_id: int = Field(ge=1, le=20)
    beat_name: str = Field(..., min_length=2, max_length=30)
    description: str = Field(..., min_length=10, max_length=200)
    emotion: EmotionType
    emotion_intensity: float = Field(ge=0, le=1, description="情绪强度 0-1")
    key_characters: List[str] = Field(..., min_items=1, max_items=5)
    estimated_duration_sec: int = Field(default=10, ge=5, le=120)


class SceneDialogue(BaseModel):
    """场景对话"""
    character: str = Field(..., min_length=1, max_length=20)
    line: str = Field(..., description="对白内容，必须是中文", min_length=1, max_length=200)
    
    @validator('line')
    def validate_line_language(cls, v):
        """检查对白是否为中文"""
        chinese_chars = sum(1 for c in v if '\u4e00' <= c <= '\u9fff')
        if chinese_chars == 0 and len(v) > 3:
            raise ValueError(f"对白 '{v[:50]}...' 应为中文")
        return v


class SceneStateUpdate(BaseModel):
    """场景状态更新 - 强约束数值范围"""
    character: str = Field(..., description="角色名称")
    hp_change: int = Field(default=0, ge=-50, le=50, description="HP变化量 -50 到 +50")
    new_status: Optional[CharacterStatus] = None
    location_change: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=100)
    
    @root_validator
    def validate_hp_and_status(cls, values):
        """验证HP和状态的一致性"""
        hp_change = values.get('hp_change', 0)
        new_status = values.get('new_status')
        
        # 如果HP变化很大，建议更新状态
        if hp_change <= -30 and not new_status:
            values['new_status'] = CharacterStatus.INJURED
        elif hp_change <= -80 and not new_status:
            values['new_status'] = CharacterStatus.CRITICAL
        
        return values


class Scene(BaseModel):
    """单场景分镜 - 完整约束"""
    scene_id: int = Field(ge=1)
    beat_id: int = Field(ge=1)
    scene_name: str = Field(..., min_length=2, max_length=50)
    
    # 视觉部分 - 只描述动作和环境，不重复角色外貌
    visual_action: str = Field(..., description="当前动作和环境描述（纯英文）", min_length=5)
    
    # 运镜 - 强制枚举
    camera_movement: CameraMovement
    
    # 音频部分
    narration: str = Field(..., description="观察者旁白（中文，冷酷客观）", min_length=5)
    dialogues: List[SceneDialogue] = Field(default_factory=list)
    sfx_tags: List[str] = Field(default_factory=list, description="音效标签（英文）")
    vfx_tags: List[str] = Field(default_factory=list, description="特效标签（英文）")
    
    # 状态更新
    state_updates: List[SceneStateUpdate] = Field(default_factory=list)
    
    # 元数据
    estimated_duration_ms: Optional[int] = Field(None, ge=1000, le=60000)
    
    @validator('narration')
    def validate_narration(cls, v):
        """旁白必须是冷酷客观的，禁止心理描写"""
        forbidden_words = ['心中', '感到', '觉得', '以为', '心跳加速', '恐惧', '好奇', '希望', '期待',
                          '心里', '内心', '暗自', '偷偷', '悄悄', '忍不住', '不由得']
        for word in forbidden_words:
            if word in v:
                raise ValueError(f"旁白包含主观词汇 '{word}'")
        return v
    
    @validator('visual_action')
    def validate_visual_action_language(cls, v):
        """视觉动作描述必须为英文（用于生图）"""
        chinese_chars = sum(1 for c in v if '\u4e00' <= c <= '\u9fff')
        if chinese_chars > 0:
            raise ValueError(f"visual_action 应为英文，包含 {chinese_chars} 个中文字符")
        return v
    
    @validator('sfx_tags', 'vfx_tags', each_item=True)
    def validate_tag_format(cls, v):
        """验证标签格式"""
        if not v.startswith(('SFX:', 'VFX:', 'AMBIENT:', 'VISUAL:')):
            # 自动修复
            if 'SFX' in v.upper() or 'sound' in v.lower():
                return f"SFX: {v}"
            elif 'VFX' in v.upper() or 'effect' in v.lower():
                return f"VFX: {v}"
        return v


class MasterScript(BaseModel):
    """主剧本 - 顶层模型"""
    project_name: str = Field(..., min_length=1, max_length=50)
    style: str = Field(..., min_length=1, max_length=30)
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # 角色库（从 ProjectBible 继承）
    characters: List[CharacterVisual] = Field(..., min_items=1, max_items=10)
    
    # 场景列表
    scenes: List[Scene] = Field(..., min_items=1)
    
    # 最终台账快照
    ledger_snapshot: Dict[str, Any]
    
    # 验证
    @root_validator
    def validate_scene_continuity(cls, values):
        """验证场景连续性"""
        scenes = values.get('scenes', [])
        if not scenes:
            return values
        
        # 检查 scene_id 连续性
        scene_ids = [s.scene_id for s in scenes]
        expected_ids = list(range(1, len(scenes) + 1))
        if scene_ids != expected_ids:
            raise ValueError(f"scene_id 不连续: {scene_ids}, 期望: {expected_ids}")
        
        return values
    
    def get_character_visual_anchor(self, character_name: str) -> Optional[str]:
        """获取角色的视觉锚点"""
        for char in self.characters:
            if char.name == character_name:
                return char.visual_anchor
        return None
    
    def build_full_prompt(self, scene: Scene) -> str:
        """构建完整的生图 Prompt"""
        # 获取角色锚点
        character_anchors = []
        for dialogue in scene.dialogues:
            anchor = self.get_character_visual_anchor(dialogue.character)
            if anchor:
                character_anchors.append(anchor)
        
        # 去重
        character_anchors = list(dict.fromkeys(character_anchors))
        
        # 拼接完整 Prompt
        full_prompt = f"{scene.visual_action}"
        if character_anchors:
            full_prompt += f", characters: {' and '.join(character_anchors)}"
        
        return full_prompt


class ProjectBible(BaseModel):
    """项目圣经 - 导演引擎输出"""
    project_name: str
    style: str
    generated_at: str
    
    world_setting: Dict[str, Any] = Field(..., description="世界观设定")
    character_visual_dict: List[CharacterVisual] = Field(..., description="角色视觉字典")
    beat_sheet: List[Beat] = Field(..., description="节拍表")


# ========== 验证函数 ==========

def validate_master_script(file_path: str) -> MasterScript:
    """验证主剧本文件"""
    import json
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return MasterScript(**data)