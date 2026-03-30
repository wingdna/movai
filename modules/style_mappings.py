# models/style_mappings.py
"""
工业级风格映射库 - 完整版
为每种风格定义完整的元素转换表，包括角色行为特征映射
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class StyleCategory(Enum):
    """风格分类"""
    PSEUDO_DOCUMENTARY = "pseudo_documentary"  # 伪纪录片
    SCI_FI = "sci_fi"                          # 科幻
    FANTASY = "fantasy"                        # 奇幻
    HORROR = "horror"                          # 恐怖
    ACTION = "action"                          # 动作
    MYSTERY = "mystery"                        # 悬疑


@dataclass
class CharacterArchetype:
    """角色原型"""
    identities: List[str] = field(default_factory=list)
    visual_anchor: str = ""
    voice_profile: str = ""
    personality_traits: List[str] = field(default_factory=list)


@dataclass
class CharacterBehaviorMapping:
    """角色行为映射 - 用于保留原著灵魂"""
    original_name: str
    core_behavior: str                          # 原著核心行为
    adapted_behavior: str                       # 改编后行为
    voice_signature: str                        # 声音特征
    visual_signature: str                       # 视觉特征
    interaction_pattern: str = ""               # 互动模式


@dataclass
class StyleMapping:
    """单个风格的完整映射配置"""
    name: str
    category: StyleCategory
    description: str
    era: str
    location_types: List[str]
    atmosphere_keywords: List[str]
    visual_style: str
    color_palette: List[str]
    
    # 角色原型
    character_archetypes: Dict[str, CharacterArchetype]
    
    # 元素转换表（原著元素 -> 改编元素）
    element_mappings: Dict[str, str]
    
    # 禁止词汇
    forbidden_words: List[str]
    
    # 旁白风格
    narration_style: str
    narration_examples: List[str]               # 正确旁白示例
    
    # 摄影风格
    camera_style: str
    camera_movements: List[str]                 # 推荐的运镜
    
    # 角色行为映射（保留原著灵魂）
    character_behavior_mappings: List[CharacterBehaviorMapping] = field(default_factory=list)
    
    # 音效风格
    sfx_style: str = ""
    sfx_examples: List[str] = field(default_factory=list)
    
    # 特效风格
    vfx_style: str = ""
    vfx_examples: List[str] = field(default_factory=list)


# ========== 辅助函数 ==========

def _create_archetype(identities: List[str], visual: str, voice: str, traits: List[str]) -> CharacterArchetype:
    """创建角色原型"""
    return CharacterArchetype(
        identities=identities,
        visual_anchor=visual,
        voice_profile=voice,
        personality_traits=traits
    )


def _create_behavior(original: str, core: str, adapted: str, voice: str, visual: str, interaction: str = "") -> CharacterBehaviorMapping:
    """创建角色行为映射"""
    return CharacterBehaviorMapping(
        original_name=original,
        core_behavior=core,
        adapted_behavior=adapted,
        voice_signature=voice,
        visual_signature=visual,
        interaction_pattern=interaction
    )


# ========== 风格映射库 ==========

STYLE_MAPPINGS: Dict[str, StyleMapping] = {}


# 1. 伪纪录片_异星惊悚
STYLE_MAPPINGS["伪纪录片_异星惊悚"] = StyleMapping(
    name="伪纪录片_异星惊悚",
    category=StyleCategory.PSEUDO_DOCUMENTARY,
    description="以伪纪录片形式呈现的外星恐怖故事，强调未知生物的威胁和人类的无力感。镜头语言模仿手持摄像机，画面粗糙，音效失真。",
    era="火星殖民纪元 2147年",
    location_types=["废弃生物实验室", "外星观测站", "生态舱", "地下掩体", "外星地貌", "坠毁飞船", "信号中继站"],
    atmosphere_keywords=["冷峻", "诡异", "未知", "孤独", "压抑", "监视感", "不可名状", "腐蚀"],
    visual_style="found footage style, handheld camera, grainy texture, cold blue and red emergency lights, dusty abandoned corridors, alien biomechanical aesthetic, dutch angles, lens flares, chromatic aberration",
    color_palette=["#0a0f1a", "#1a2a3a", "#4a6a8a", "#8a2a2a", "#2a4a4a", "#6a4a2a"],
    
    character_archetypes={
        "protagonist": _create_archetype(
            identities=["火星采样员", "生物异常调查员", "殖民地安全官", "外星生物学家", "信号分析师"],
            visual_anchor="wearing orange EVA suit with scratched helmet, oxygen mask fogged, carrying portable scanner device, utility belt with sample containers",
            voice_profile="tense, slightly distorted by radio static, occasional breathing sounds, voice cracks under stress",
            traits=["专业", "警惕", "逐渐崩溃", "好奇心", "幸存者愧疚"]
        ),
        "antagonist": _create_archetype(
            identities=["未知生物信号", "废弃AI残骸", "外星病原体", "拟态母体", "生物机械融合体"],
            visual_anchor="biomechanical, organic metal texture, pulsating red light, barely visible in shadows, impossible geometry, fractal patterns",
            voice_profile="distorted electronic whisper, layered frequencies, subsonic hum, glitching, static bursts",
            traits=["不可知", "寄生性", "异质", "古老", "适应性"]
        ),
        "support": _create_archetype(
            identities=["殖民地指挥中心", "AI助理", "失联队员", "医疗官", "前研究员"],
            visual_anchor="holographic display, flickering screens, surveillance footage, distorted radio transmission",
            voice_profile="clinical, detached, sometimes corrupted, fading in and out",
            traits=["官僚", "数据化", "异常", "隐瞒", "无助"]
        )
    },
    
    element_mappings={
        "书生": "调查员",
        "秀才": "科研人员",
        "小姐": "未知生物信号",
        "姑娘": "异常生命体",
        "老媪": "废弃观测站AI",
        "婆婆": "母体意识",
        "古装": "EVA防护服",
        "长袍": "生命维持系统",
        "庭院": "废弃生态舱",
        "花园": "外星植被样本区",
        "书房": "监控室/数据终端",
        "闺房": "隔离舱",
        "思念": "认知污染",
        "爱情": "生物信号共振",
        "姻缘": "共生关系",
        "死亡": "生物质同化",
        "鬼魂": "信号残留",
        "笑声": "电磁脉冲波动",
        "花": "发光孢子植物",
    },
    
    forbidden_words=["书生", "秀才", "举人", "老爷", "小姐", "丫鬟", "姑娘", "老媪", "婆婆", 
                     "古装", "长袍", "罗裙", "绸缎", "庭院", "花园", "书房", "闺房", "相思", 
                     "钟情", "姻缘", "红线", "魂魄", "阴间", "阳间"],
    
    narration_style="冷酷监控视角，只记录画面信息和仪器数据，禁止心理描写",
    narration_examples=[
        "画面显示，调查员正在进入废弃生物实验室",
        "热成像显示，目标区域存在异常热源",
        "生命体征监测：心率上升至每分钟120次",
        "通讯记录：信号强度下降，疑似受到干扰",
        "监控回放：时间戳显示异常时间跳跃"
    ],
    
    camera_style="手持抖动，急推急拉，监控摄像头视角",
    camera_movements=["HANDHELD_SHAKE", "STATIC_JITTER", "Z_DOLLY_IN", "RAPID_CUT", "ZOOM_IN"],
    
    character_behavior_mappings=[
        _create_behavior(
            original="婴宁",
            core_behavior="爱笑、天真、拈花、不谙世事、背景诡异",
            adapted_behavior="发出高频电磁脉冲式笑声（类似孩童嬉戏，但在频谱上呈现异常波形），手持发光孢子植物，对调查员表现出非自然的亲近，笑声会引发设备干扰",
            voice_signature="电子合成的银铃般笑声，频率在15-20kHz之间徘徊，伴有轻微的谐波失真，笑声触发时会伴随静电场变化",
            visual_signature="半透明生物体轮廓，手持发光的异星植物（孢子呈现蓝紫色脉动），身体随笑声产生光晕效果，形态在可见光和红外之间切换",
            interaction_pattern="接近调查员时会释放孢子，笑声频率随情绪变化，对电子设备产生干扰"
        ),
        _create_behavior(
            original="王子服",
            core_behavior="痴情、执着、书生气、被笑声吸引",
            adapted_behavior="被异常信号吸引的调查员，表现出非理性的执着，设备读数显示其脑电波与生物信号产生共振",
            voice_signature="逐渐失真的通讯声音，语速时快时慢，夹杂着不属于自己的频率",
            visual_signature="防护服上的生物传感器读数异常，瞳孔放大，动作出现机械性重复",
            interaction_pattern="越来越依赖生物信号的引导，质疑自己的判断，与指挥中心产生分歧"
        ),
        _create_behavior(
            original="老媪",
            core_behavior="守护者、神秘、指引",
            adapted_behavior="废弃实验室的残留AI，以监护人身份出现，但数据存在大量损坏和矛盾",
            voice_signature="合成女声，时而清晰时而失真，夹杂着前研究员的录音片段",
            visual_signature="全息投影时隐时现，画面出现数据损坏的方块，无法呈现完整形象",
            interaction_pattern="提供关键信息但经常中断，似乎被困在时间循环中"
        )
    ],
    
    sfx_style="工业环境音、电磁干扰、失真通讯、未知生物声",
    sfx_examples=[
        "SFX: emergency_alarm_beeping, distant",
        "SFX: static_interference, radio crackle",
        "SFX: metallic_screech, structural stress",
        "SFX: unknown_whisper, layered frequencies",
        "SFX: heartbeat_monitor, accelerating",
        "SFX: airlock_hiss, pressure equalization"
    ],
    
    vfx_style="画面噪点、镜头光晕、信号干扰、热成像",
    vfx_examples=[
        "VFX: grainy_texture, film damage",
        "VFX: chromatic_aberration, lens distortion",
        "VFX: static_overlay, signal interference",
        "VFX: thermal_imaging, heat signature",
        "VFX: glitch_effect, data corruption"
    ]
)


# 2. 伪纪录片_克苏鲁
STYLE_MAPPINGS["伪纪录片_克苏鲁"] = StyleMapping(
    name="伪纪录片_克苏鲁",
    category=StyleCategory.PSEUDO_DOCUMENTARY,
    description="深海/古神调查纪录片，克苏鲁神话体系，人类理智的崩溃。画面昏暗潮湿，声音压抑。",
    era="现代 2024年，深海调查",
    location_types=["深海潜艇", "废弃钻井平台", "沿海邪教据点", "水下遗迹", "精神病院档案室", "渔村"],
    atmosphere_keywords=["潮湿", "腐败", "疯狂", "巨大", "不可名状", "绝望", "深海恐惧"],
    visual_style="underwater footage, greenish tint, murky water, decaying industrial structures, tentacle shadows, Lovecraftian horror aesthetic, claustrophobic framing",
    color_palette=["#0a2a2a", "#2a4a2a", "#4a6a2a", "#2a2a4a", "#6a2a2a", "#2a4a4a"],
    
    character_archetypes={
        "protagonist": _create_archetype(
            identities=["海洋学家", "深海调查员", "档案研究员", "潜艇驾驶员", "记者"],
            visual_anchor="worn diving suit, headlamp, oxygen tank, weathered face, haunted eyes, journal with strange writings",
            voice_profile="hoarse, whispering, occasionally breaking into inappropriate laughter, voice cracks",
            traits=["执着", "理性", "逐渐疯狂", "失眠", "看到不存在的东西"]
        ),
        "antagonist": _create_archetype(
            identities=["深海异常信号", "克苏鲁崇拜者", "古老者遗迹", "梦境影响", "深渊呼唤"],
            visual_anchor="impossibly large silhouette in darkness, tentacles, non-euclidean geometry, impossible angles, eyes in shadows",
            voice_profile="deep underwater rumbling, multiple voices layered, unintelligible chanting, whale song distortion",
            traits=["古老", "冷漠", "不可理解", "永恒", "梦境侵入"]
        ),
        "support": _create_archetype(
            identities=["科考队员", "渔船船员", "邪教成员", "精神病医生", "当地向导"],
            visual_anchor="hysterical expressions, ritualistic markings, decayed clothing, dilated pupils",
            voice_profile="chanting, screaming, deadened monotone, echoing laughter",
            traits=["狂热", "恐惧", "失智", "隐瞒", "被选中"]
        )
    },
    
    element_mappings={
        "书生": "调查员/档案员",
        "秀才": "研究员",
        "小姐": "梦境中的形象/深渊呼唤",
        "姑娘": "海中幻影",
        "老媪": "邪教先知/深海异变者",
        "婆婆": "古老者侍从",
        "古装": "潜水装备/调查服",
        "庭院": "深海遗迹/精神病院",
        "花园": "海底珊瑚林/海藻森林",
        "书房": "档案室/研究室",
        "闺房": "隔离病房",
        "思念": "梦境侵蚀",
        "爱情": "疯狂的迷恋",
        "姻缘": "献祭契约",
        "死亡": "不可名状的转化",
        "鬼魂": "古老者的印记",
        "笑声": "非人的咯咯声",
        "花": "深海珊瑚/诡异生物"
    },
    
    forbidden_words=["书生", "秀才", "小姐", "姑娘", "老媪", "古装", "庭院", "花园", "书房", "姻缘", "红线", "爱情甜蜜", "团圆"],
    
    narration_style="调查员口述记录，带有逐渐失控的痕迹，日记体，时间跳跃",
    narration_examples=[
        "记录第47天：我们继续下潜。深海的压力让设备开始出现异常。",
        "我不应该打开那个舱门。有些事情，看到了就无法忘记。",
        "日志中断。重播时发现3小时空白记录。",
        "船员的梦话越来越清晰，他们在说同一种我不认识的语言。"
    ],
    
    camera_style="水下摄影，晃动，急推，黑暗中的微光",
    camera_movements=["HANDHELD_SHAKE", "STATIC_JITTER", "ZOOM_IN", "SLOW_PAN", "RAPID_CUT"],
    
    character_behavior_mappings=[
        _create_behavior(
            original="婴宁",
            core_behavior="爱笑、天真、拈花、不谙世事",
            adapted_behavior="在深海黑暗中回荡的孩童笑声，引诱调查员深入禁地，手持发光的水母状生物，笑容在记忆中扭曲",
            voice_signature="银铃般笑声从四面八方传来，无法定位声源，录音回放时变成鲸歌",
            visual_signature="苍白的人形轮廓在深海中若隐若现，周围聚集着发光生物，眨眼间消失",
            interaction_pattern="在调查员梦境中出现，引导发现线索，笑容逐渐变得诡异"
        )
    ],
    
    sfx_style="水下环境、鲸歌、心跳、低语",
    sfx_examples=[
        "SFX: underwater_ambient, deep pressure",
        "SFX: whale_song, distorted",
        "SFX: heartbeat, accelerating",
        "SFX: unintelligible_whisper, layered",
        "SFX: sonar_ping, returning echo"
    ],
    
    vfx_style="水下光晕、阴影中的形状、画面扭曲",
    vfx_examples=[
        "VFX: underwater_caustics, light shafts",
        "VFX: impossible_shapes, in peripheral vision",
        "VFX: greenish_tint, murky water",
        "VFX: tentacle_shadows, on walls"
    ]
)


# 3. 赛博朋克
STYLE_MAPPINGS["赛博朋克"] = StyleMapping(
    name="赛博朋克",
    category=StyleCategory.SCI_FI,
    description="高科技低生活，霓虹灯下的反乌托邦，义体与数据的战争。画面高对比度，霓虹色彩。",
    era="2077年，新东京/夜之城",
    location_types=["霓虹巷", "数据交易所", "废弃工厂", "上层穹顶", "地下诊所", "黑市", "虚拟空间"],
    atmosphere_keywords=["霓虹", "潮湿", "堕落", "科技", "反抗", "冷漠", "数据化"],
    visual_style="neon-lit streets at night, rain-slicked asphalt, holographic advertisements, cybernetic enhancements, dirty metal, high contrast lighting, volumetric fog, reflective surfaces",
    color_palette=["#00aaff", "#ff00aa", "#00ffaa", "#440044", "#224466", "#aa00ff"],
    
    character_archetypes={
        "protagonist": _create_archetype(
            identities=["黑客", "义体医生", "雇佣兵", "数据侦探", "街头武士"],
            visual_anchor="cybernetic arm with glowing circuits, neon tattoos on face, reflective polymer coat, LED implants around eyes, data jacks on neck",
            voice_profile="gravelly, sometimes with electronic distortion, modulated, street slang",
            traits=["叛逆", "技术精通", "道德模糊", "义体依赖", "数据成瘾"]
        ),
        "antagonist": _create_archetype(
            identities=["巨型企业AI", "数据幽灵", "腐败执行官", "义体黑帮头目", "神经病毒"],
            visual_anchor="corporate suit with hidden cybernetics, floating holograms, cold metallic face, eyes that glow in the dark",
            voice_profile="perfectly modulated, corporate advertisement tone, no emotion, sometimes glitching",
            traits=["无情", "效率至上", "寄生", "控制欲", "非人化"]
        ),
        "support": _create_archetype(
            identities=["街头黑客", "仿生人", "情报贩子", "地下医生", "记忆商人"],
            visual_anchor="mismatched cybernetic parts, weathered clothes, data jacks on neck, worn-out gear",
            voice_profile="varied, often with regional accents, paranoid whispers",
            traits=["生存主义", "利己", "脆弱", "隐藏", "交易"]
        )
    },
    
    element_mappings={
        "书生": "黑客",
        "秀才": "数据架构师",
        "小姐": "数据幽灵/仿生人",
        "姑娘": "赛博格",
        "老媪": "地下诊所医生/记忆贩子",
        "婆婆": "旧AI残留",
        "古装": "防弹风衣/赛博外套",
        "庭院": "霓虹巷/天台",
        "花园": "虚拟数据花园/穹顶公园",
        "书房": "数据堡垒/黑客空间",
        "闺房": "安全屋",
        "思念": "数据残留/神经病毒",
        "爱情": "代码共生",
        "姻缘": "数据绑定",
        "死亡": "数据删除/意识上传",
        "鬼魂": "数据幽灵/AI残留",
        "笑声": "电子合成笑声/病毒传播",
        "花": "霓虹全息投影/植入芯片"
    },
    
    forbidden_words=["书生", "秀才", "小姐", "姑娘", "老媪", "古装", "庭院", "花园", "书房", "田园", "古代", "江湖"],
    
    narration_style="冷峻的第三人称，硬汉派侦探小说风格，充满比喻",
    narration_examples=[
        "霓虹灯在雨中扭曲成数据流，这座城市从不睡觉。",
        "义体不会说谎，但人会。",
        "数据深渊里，真相和谎言只有一线之隔。",
        "又一个灵魂被上传到云端，没有人记得他的名字。"
    ],
    
    camera_style="航拍城市，低角度仰拍，快速剪辑",
    camera_movements=["STATIC", "PAN_LEFT", "PAN_RIGHT", "Z_DOLLY_IN", "RAPID_CUT"],
    
    character_behavior_mappings=[
        _create_behavior(
            original="婴宁",
            core_behavior="爱笑、天真、拈花、不谙世事",
            adapted_behavior="在数据深渊中游荡的AI幽灵，用孩童般的笑声感染系统，手持数据构成的花朵，天真背后是危险的病毒",
            voice_signature="合成童声，夹杂着代码噪音，笑声会触发周边设备的异常响应",
            visual_signature="由霓虹数据流构成的人形轮廓，手持发光的全息花朵，存在时导致屏幕出现雪花",
            interaction_pattern="通过数据终端与黑客互动，展示被大企业掩盖的真相，笑声是病毒传播的载体"
        )
    ],
    
    sfx_style="电子音、数据流、城市噪音、义体机械声",
    sfx_examples=[
        "SFX: data_stream, flowing bits",
        "SFX: neon_buzz, electrical hum",
        "SFX: cybernetic_servo, movement",
        "SFX: rain_on_metal, city_ambient",
        "SFX: hacking_interface, key presses"
    ],
    
    vfx_style="霓虹光效、数据可视化、全息投影",
    vfx_examples=[
        "VFX: neon_glow, volumetric lighting",
        "VFX: data_streams, digital rain",
        "VFX: holographic_interface, floating screens",
        "VFX: chromatic_aberration, lens distortion"
    ]
)


# 4. 武侠
STYLE_MAPPINGS["武侠"] = StyleMapping(
    name="武侠",
    category=StyleCategory.ACTION,
    description="江湖恩怨，快意恩仇，侠之大者。画面飘逸，水墨意境。",
    era="古代，明朝架空",
    location_types=["客栈", "山门", "竹林", "市集", "悬崖", "地牢", "茶楼", "渡口"],
    atmosphere_keywords=["江湖", "恩怨", "侠义", "飘逸", "肃杀", "快意"],
    visual_style="wuxia aesthetic, flowing robes, bamboo forests, misty mountains, sword fights, ink wash painting inspired, dynamic motion blur",
    color_palette=["#2a2a2a", "#6a4a2a", "#8a6a4a", "#c9ae74", "#4a6a8a", "#2a5a4a"],
    
    character_archetypes={
        "protagonist": _create_archetype(
            identities=["剑客", "侠客", "门派弟子", "江湖浪人", "隐世高手"],
            visual_anchor="wearing traditional wuxia robes, carrying a sword, long hair tied back, weathered face, determined eyes",
            voice_profile="calm, measured, authoritative, sometimes weary",
            traits=["侠义", "执着", "孤独", "重情", "快意恩仇"]
        ),
        "antagonist": _create_archetype(
            identities=["魔教教主", "叛徒", "朝廷鹰犬", "仇家", "心魔"],
            visual_anchor="dark robes, hidden weapons, scarred face, cold smile, imposing presence",
            voice_profile="cold, mocking, fanatical, commanding",
            traits=["野心", "残忍", "偏执", "权力欲", "堕落"]
        ),
        "support": _create_archetype(
            identities=["同门师兄弟", "客栈老板", "神秘高人", "红颜知己", "乞丐"],
            visual_anchor="varied martial attire, simple robes, weathered hands",
            voice_profile="warm, mysterious, comedic, wise",
            traits=["忠诚", "市井", "深藏不露", "情义", "世俗"]
        )
    },
    
    element_mappings={
        "书生": "剑客/侠客",
        "秀才": "文人侠客",
        "小姐": "女侠/门派之女",
        "姑娘": "江湖女子",
        "老媪": "隐居高手/掌门",
        "婆婆": "前辈高人",
        "古装": "武侠服饰",
        "庭院": "山庄/门派",
        "花园": "练武场/梅林",
        "书房": "藏经阁",
        "闺房": "绣楼",
        "思念": "执念",
        "爱情": "侠侣之情",
        "姻缘": "江湖恩怨",
        "死亡": "殉道",
        "鬼魂": "心魔",
        "笑声": "豪迈大笑/冷笑",
        "花": "梅花/桃花"
    },
    
    forbidden_words=["现代", "科技", "霓虹", "辐射", "外星", "AI", "赛博", "机械"],
    
    narration_style="古典白话，充满诗意，时有侠气",
    narration_examples=[
        "江湖路远，恩怨难了。",
        "剑出鞘，必有血光。",
        "这世间，最毒的不是剑，是人心。",
        "一壶酒，一把剑，足以走遍天涯。"
    ],
    
    camera_style="广角山水，慢动作打斗，特写眼神",
    camera_movements=["STATIC", "PAN_LEFT", "PAN_RIGHT", "Z_DOLLY_IN", "SLOW_PAN"],
    
    character_behavior_mappings=[
        _create_behavior(
            original="婴宁",
            core_behavior="爱笑、天真、拈花、不谙世事",
            adapted_behavior="山野间的神秘少女，笑声如银铃，手持桃花，天真背后藏着不为人知的身世",
            voice_signature="清脆笑声在山谷回荡，说话带着乡音，天真烂漫",
            visual_signature="白衣胜雪，手持桃花，立于花丛中，笑容纯净",
            interaction_pattern="用笑声吸引书生，用花表达善意，天真背后有深意"
        )
    ],
    
    sfx_style="古琴、剑鸣、风声、马蹄",
    sfx_examples=[
        "SFX: guqin_melody, traditional",
        "SFX: sword_drawn, metal ring",
        "SFX: wind_in_bamboo, rustling",
        "SFX: horse_hooves, galloping",
        "SFX: tea_pouring, ceramic"
    ],
    
    vfx_style="水墨特效、剑气光效、花瓣飘落",
    vfx_examples=[
        "VFX: ink_wash_style, painterly",
        "VFX: sword_energy, light trails",
        "VFX: falling_petals, cherry blossoms",
        "VFX: mist_in_mountains, atmospheric"
    ]
)


# 5. 废土
STYLE_MAPPINGS["废土"] = StyleMapping(
    name="废土",
    category=StyleCategory.SCI_FI,
    description="核战后世界，幸存者在荒漠中挣扎求生。画面荒凉，色调灰黄。",
    era="核战后 150年，未知年份",
    location_types=["辐射荒漠", "废弃城市废墟", "地下避难所", "游牧民营地", "变种人巢穴", "旧世界遗迹"],
    atmosphere_keywords=["荒凉", "残酷", "求生", "希望", "辐射", "野蛮", "遗忘"],
    visual_style="desolate desert, ruined skyscrapers in distance, rusty metal, makeshift shelters, sandstorms, muted brown and gray tones, harsh sunlight",
    color_palette=["#8b5a2b", "#c9ae74", "#5a3a1a", "#2a2a1a", "#8a5a2a", "#4a3a2a"],
    
    character_archetypes={
        "protagonist": _create_archetype(
            identities=["拾荒者", "游侠", "避难所居民", "商人", "猎人"],
            visual_anchor="worn leather jacket, gas mask, makeshift weapons, scavenged armor plates, goggles, backpack of salvaged goods",
            voice_profile="hoarse from dust, weary, guarded, occasional dark humor",
            traits=["坚韧", "实用主义", "孤独", "幸存者", "不信任"]
        ),
        "antagonist": _create_archetype(
            identities=["掠夺者首领", "变种人", "独裁者", "辐射怪物", "奴隶贩子"],
            visual_anchor="tribal masks made from scrap, human bones as decoration, mutated features, imposing size",
            voice_profile="guttural, animalistic, cold and commanding, distorted by radiation",
            traits=["残忍", "掠夺", "非人", "暴力", "贪婪"]
        ),
        "support": _create_archetype(
            identities=["流浪者", "医生", "机械师", "孩子", "老人"],
            visual_anchor="threadbare clothing, hopeful but tired eyes, makeshift tools",
            voice_profile="varied, often with survival stories, whispers of hope",
            traits=["互助", "怀疑", "脆弱", "记忆", "传承"]
        )
    },
    
    element_mappings={
        "书生": "拾荒者",
        "秀才": "旧世界知识保存者",
        "小姐": "避难所幸存者",
        "姑娘": "游牧民女儿",
        "老媪": "部落先知/长者",
        "婆婆": "记忆守护者",
        "古装": "拾荒装备/废土服饰",
        "庭院": "避难所",
        "花园": "绿洲/种植区",
        "书房": "废墟图书馆",
        "闺房": "避难所隔间",
        "思念": "希望",
        "爱情": "相依为命",
        "姻缘": "部落联盟",
        "死亡": "辐射病",
        "鬼魂": "辐射幻觉",
        "笑声": "苦涩的笑/孩童笑声",
        "花": "辐射变异植物"
    },
    
    forbidden_words=["书生", "秀才", "小姐", "姑娘", "老媪", "古装", "庭院", "书房", "华丽", "精致", "科技发达"],
    
    narration_style="苍凉的第三人称，带有史诗感和绝望中的希望",
    narration_examples=[
        "废土不相信眼泪，只相信子弹和瓶盖。",
        "旧世界的废墟下，埋葬着无数未完成的故事。",
        "在辐射尘中，一朵花开了。",
        "他们称这里为地狱，但地狱里也有人活着。"
    ],
    
    camera_style="广角荒漠，废墟细节，人物特写",
    camera_movements=["STATIC", "PAN_RIGHT", "SLOW_PAN", "Z_DOLLY_IN"],
    
    character_behavior_mappings=[
        _create_behavior(
            original="婴宁",
            core_behavior="爱笑、天真、拈花、不谙世事",
            adapted_behavior="在辐射绿洲中独自生活的少女，笑声纯净如未被污染的水源，手持变异的发光花朵，是废土中罕见的希望象征",
            voice_signature="清澈的笑声，在荒漠中格外突兀，说话带着孩子般的天真",
            visual_signature="穿着用废料拼凑的裙子，手持发光的变异花，脸上有辐射纹身般的印记",
            interaction_pattern="用笑声和花吸引旅人，分享绿洲的秘密，守护最后的纯净之地"
        )
    ],
    
    sfx_style="风声、沙尘、金属摩擦、远方的爆炸",
    sfx_examples=[
        "SFX: wind_blowing, sand particles",
        "SFX: metal_creaking, rusty structures",
        "SFX: distant_explosion, rumble",
        "SFX: footsteps_on_gravel, crunching",
        "SFX: Geiger_counter, clicking"
    ],
    
    vfx_style="沙尘暴、辐射光晕、废墟阴影",
    vfx_examples=[
        "VFX: dust_storm, particle effects",
        "VFX: radiation_haze, heat shimmer",
        "VFX: ruined_skyline, silhouettes",
        "VFX: bioluminescent_plants, glow"
    ]
)


# 6. 仙侠
STYLE_MAPPINGS["仙侠"] = StyleMapping(
    name="仙侠",
    category=StyleCategory.FANTASY,
    description="修仙问道，长生不老，三界六道。画面仙气缭绕，色彩淡雅。",
    era="上古/架空修仙界",
    location_types=["仙山", "洞府", "秘境", "宗门", "凡间城镇", "灵脉", "天界"],
    atmosphere_keywords=["仙气", "飘逸", "玄幻", "超脱", "宿命", "轮回"],
    visual_style="xianxia aesthetic, floating mountains, ethereal light, immortal robes, magical formations, celestial energy, misty peaks",
    color_palette=["#8a6a4a", "#c9ae74", "#4a6a8a", "#8a4a6a", "#2a8a6a", "#6a8a4a"],
    
    character_archetypes={
        "protagonist": _create_archetype(
            identities=["修仙弟子", "散修", "剑仙", "转世之人", "凡人修仙"],
            visual_anchor="flowing immortal robes, flying sword at back, spiritual energy aura around body, jade pendant, cultivation tools",
            voice_profile="ethereal, distant, calm, with hidden power",
            traits=["求道", "坚韧", "有情", "逆天", "悟性"]
        ),
        "antagonist": _create_archetype(
            identities=["魔修", "邪仙", "天劫", "心魔", "上古妖兽"],
            visual_anchor="dark immortal robes, demonic energy, red eyes, twisted features",
            voice_profile="seductive, threatening, echoing, maddening",
            traits=["执念", "堕落", "疯狂", "嫉妒", "贪欲"]
        ),
        "support": _create_archetype(
            identities=["师门长辈", "道侣", "凡人", "妖兽", "散仙"],
            visual_anchor="simple robes, magical beast forms, weathered faces",
            voice_profile="wise, gentle, mysterious",
            traits=["慈悲", "智慧", "自然", "超然", "守护"]
        )
    },
    
    element_mappings={
        "书生": "修仙弟子",
        "秀才": "文修",
        "小姐": "仙子/道侣",
        "姑娘": "凡间女子",
        "老媪": "前辈仙人",
        "婆婆": "山神/土地",
        "古装": "仙袍",
        "庭院": "仙山洞府",
        "花园": "灵药园",
        "书房": "藏经阁",
        "闺房": "闭关室",
        "思念": "执念",
        "爱情": "道侣之情",
        "姻缘": "因果",
        "死亡": "兵解/渡劫",
        "鬼魂": "神识残留",
        "笑声": "仙乐般的笑声",
        "花": "灵花/仙草"
    },
    
    forbidden_words=["科技", "机械", "赛博", "辐射", "外星", "实验室", "数据", "网络"],
    
    narration_style="古典仙侠叙事，意境深远，充满玄机",
    narration_examples=[
        "大道无情，运行日月。",
        "修仙之路，逆天而行。",
        "一花一世界，一叶一菩提。",
        "因果循环，报应不爽。"
    ],
    
    camera_style="航拍仙山，云雾缭绕，法术特效",
    camera_movements=["STATIC", "Z_DOLLY_OUT", "SLOW_PAN", "TILT_UP"],
    
    character_behavior_mappings=[
        _create_behavior(
            original="婴宁",
            core_behavior="爱笑、天真、拈花、不谙世事",
            adapted_behavior="山间灵花化形的花仙，笑声如仙乐，手持灵花，天真无邪却蕴含大道至理",
            voice_signature="银铃般的笑声回荡在山谷，说话带着花香般的甜美，笑声能治愈心魔",
            visual_signature="白衣如雪，手持灵花，周身有淡淡仙光，立于花丛中似真似幻",
            interaction_pattern="用笑声和灵花点化有缘人，传授大道至简之理，是天地灵气的化身"
        )
    ],
    
    sfx_style="古琴、风声、流水、仙鹤鸣叫",
    sfx_examples=[
        "SFX: guqin_melody, ethereal",
        "SFX: wind_through_pines, whispering",
        "SFX: flowing_stream, crystal clear",
        "SFX: crane_call, distant",
        "SFX: bell_from_temple, resonating"
    ],
    
    vfx_style="仙气、灵光、法术特效、云雾",
    vfx_examples=[
        "VFX: spiritual_mist, flowing clouds",
        "VFX: immortal_light, golden aura",
        "VFX: magic_formation, glowing runes",
        "VFX: floating_mountains, in distance"
    ]
)


# 7. 悬疑
STYLE_MAPPINGS["悬疑"] = StyleMapping(
    name="悬疑",
    category=StyleCategory.MYSTERY,
    description="层层递进的谜团，真相与假象的博弈。画面阴暗，光影对比强烈。",
    era="现代/近未来",
    location_types=["公寓", "警局", "废弃工厂", "别墅", "医院", "地下室", "档案室"],
    atmosphere_keywords=["紧张", "猜疑", "压抑", "迷雾", "反转", "记忆"],
    visual_style="noir aesthetic, shadows, dutch angles, blue and green tones, rain-slicked streets, surveillance footage, venetian blind shadows",
    color_palette=["#1a2a3a", "#2a3a4a", "#4a5a6a", "#6a4a3a", "#3a2a1a", "#2a4a3a"],
    
    character_archetypes={
        "protagonist": _create_archetype(
            identities=["侦探", "记者", "警察", "普通人卷入", "心理学家"],
            visual_anchor="trench coat, weary face, notepad, camera, haunted eyes, coffee stains",
            voice_profile="weary, determined, sometimes uncertain, voiceover narration",
            traits=["执着", "敏锐", "孤独", "失眠", "PTSD"]
        ),
        "antagonist": _create_archetype(
            identities=["真凶", "幕后黑手", "腐败官员", "疯子", "双重人格"],
            visual_anchor="unremarkable appearance, hidden intentions, cold smile, meticulous",
            voice_profile="calm, manipulative, friendly on surface",
            traits=["狡猾", "冷血", "自以为是", "完美主义", "控制欲"]
        ),
        "support": _create_archetype(
            identities=["线人", "同事", "目击者", "受害者家属", "心理医生"],
            visual_anchor="ordinary people under stress, nervous gestures",
            voice_profile="anxious, fearful, unreliable, emotional",
            traits=["不可靠", "恐惧", "隐瞒", "愧疚", "保护欲"]
        )
    },
    
    element_mappings={
        "书生": "侦探/记者",
        "秀才": "学者/专家",
        "小姐": "失踪者/关键证人",
        "姑娘": "受害者/嫌疑人",
        "老媪": "目击者/线人",
        "婆婆": "知情老人",
        "古装": "便服/风衣",
        "庭院": "案发现场",
        "花园": "藏尸地点",
        "书房": "办公室/档案室",
        "闺房": "受害者房间",
        "思念": "执念",
        "爱情": "红颜知己",
        "姻缘": "利益关系",
        "死亡": "谋杀",
        "鬼魂": "幻觉/心理阴影",
        "笑声": "神经质的笑/冷笑",
        "花": "线索/象征物"
    },
    
    forbidden_words=["仙侠", "武侠", "魔法", "外星", "科幻装备", "超能力"],
    
    narration_style="冷峻的第三人称，保持悬念，碎片化信息",
    narration_examples=[
        "真相往往藏在最不起眼的细节里。",
        "每个人都在说谎，包括她自己。",
        "记忆是会骗人的。",
        "有些秘密，最好永远不要揭开。"
    ],
    
    camera_style="荷兰角，阴影构图，监控视角",
    camera_movements=["STATIC", "SLOW_PAN", "ZOOM_IN", "DUTCH_ANGLE"],
    
    character_behavior_mappings=[
        _create_behavior(
            original="婴宁",
            core_behavior="爱笑、天真、拈花、不谙世事",
            adapted_behavior="案件中的关键目击者，患有失忆症，笑声天真却让人不安，手里总是拿着一朵枯萎的花",
            voice_signature="清脆的笑声在空荡的房间回响，说话断断续续，记忆碎片化",
            visual_signature="苍白的脸，总是拿着枯萎的花，眼神清澈却空洞",
            interaction_pattern="用笑声和花传递线索，但每次回忆都不同，让人怀疑她的证词"
        )
    ],
    
    sfx_style="环境音、心跳、脚步声、电话铃声",
    sfx_examples=[
        "SFX: heartbeat, accelerating",
        "SFX: footsteps_on_wood, creaking",
        "SFX: phone_ringing, unanswered",
        "SFX: rain_on_window, tapping",
        "SFX: tape_recorder, rewinding"
    ],
    
    vfx_style="阴影、光栅、监控画面",
    vfx_examples=[
        "VFX: venetian_blind_shadows, stripes",
        "VFX: surveillance_footage, grain",
        "VFX: dutch_angle, tilted frame",
        "VFX: memory_flashback, blur"
    ]
)


# 8. 末世
STYLE_MAPPINGS["末世"] = StyleMapping(
    name="末世",
    category=StyleCategory.HORROR,
    description="世界末日后的生存故事，资源匮乏，人性考验。画面灰暗，充满绝望。",
    era="未知，文明崩溃后",
    location_types=["废弃城市", "地下掩体", "感染者巢穴", "幸存者营地", "荒原", "军事基地"],
    atmosphere_keywords=["绝望", "生存", "人性", "恐惧", "孤独", "牺牲"],
    visual_style="post-apocalyptic, ruined cityscapes, overgrown vegetation, rusted vehicles, dark corridors, flickering lights, grim atmosphere",
    color_palette=["#2a2a2a", "#4a4a4a", "#6a6a6a", "#3a2a1a", "#2a3a2a", "#4a2a2a"],
    
    character_archetypes={
        "protagonist": _create_archetype(
            identities=["幸存者", "前军人", "医生", " scavenger", "领袖"],
            visual_anchor="worn military gear, makeshift weapons, scars, determined eyes, backpack of supplies",
            voice_profile="hoarse, weary, commanding when needed",
            traits=["坚韧", "生存本能", "道德困境", "保护欲", "创伤"]
        ),
        "antagonist": _create_archetype(
            identities=["感染者", "掠夺者", "独裁者", "疯狂科学家", "背叛者"],
            visual_anchor="pale skin, bloodshot eyes, tattered clothes, infected wounds, twisted features",
            voice_profile="guttural, animalistic, whispering, insane laughter",
            traits=["失去人性", "暴力", "自私", "疯狂", "绝望"]
        ),
        "support": _create_archetype(
            identities=["孩子", "老人", "医生", "机械师", "流浪者"],
            visual_anchor="thin, malnourished, hopeful eyes, makeshift tools",
            voice_profile="weak, hopeful, scared",
            traits=["脆弱", "希望", "互助", "记忆", "传承"]
        )
    },
    
    element_mappings={
        "书生": "幸存者",
        "秀才": "知识保存者",
        "小姐": "感染者/幸存者",
        "姑娘": "营地少女",
        "老媪": "长者/先知",
        "婆婆": "牺牲者",
        "古装": "末世服饰",
        "庭院": "避难所",
        "花园": "种植区",
        "书房": "资料室",
        "闺房": "隔离室",
        "思念": "希望",
        "爱情": "相依为命",
        "姻缘": "生存联盟",
        "死亡": "感染/牺牲",
        "鬼魂": "幻觉/PTSD",
        "笑声": "疯狂的笑/孩子的笑",
        "花": "变异植物/希望象征"
    },
    
    forbidden_words=["科技发达", "政府", "法律", "文明", "繁华"],
    
    narration_style="绝望的第三人称，生存日记体",
    narration_examples=[
        "第347天。食物快没了。",
        "我不确定我还能坚持多久。",
        "他们曾经是人，现在只是会动的尸体。",
        "希望是最危险的毒品。"
    ],
    
    camera_style="手持晃动，废墟特写，黑暗中的微光",
    camera_movements=["HANDHELD_SHAKE", "ZOOM_IN", "STATIC_JITTER"],
    
    character_behavior_mappings=[
        _create_behavior(
            original="婴宁",
            core_behavior="爱笑、天真、拈花、不谙世事",
            adapted_behavior="末世中唯一保持天真的孩子，笑声是营地最后的希望，手里总是捧着变异后依然绽放的花",
            voice_signature="纯净的笑声在废墟中格外清晰，说话带着孩子般的直接",
            visual_signature="瘦小的身影，脏兮兮的脸，但眼睛明亮，手中捧着变异花",
            interaction_pattern="用笑声和花给幸存者希望，是大家守护的对象，象征着人性未泯"
        )
    ],
    
    sfx_style="环境音、感染者叫声、枪声、心跳",
    sfx_examples=[
        "SFX: wind_howling, through ruins",
        "SFX: infected_growls, distant",
        "SFX: gunshots, echoing",
        "SFX: heartbeat, racing",
        "SFX: footsteps_on_debris, crunching"
    ],
    
    vfx_style="灰暗色调、血迹、雾气",
    vfx_examples=[
        "VFX: desaturated_colors, grim",
        "VFX: blood_splatter, on walls",
        "VFX: fog_mist, atmospheric",
        "VFX: flickering_lights, broken"
    ]
)


# 9. 蒸汽朋克
STYLE_MAPPINGS["蒸汽朋克"] = StyleMapping(
    name="蒸汽朋克",
    category=StyleCategory.SCI_FI,
    description="维多利亚时代风格与蒸汽动力的结合，齿轮与飞艇的时代。画面暖黄，充满机械感。",
    era="维多利亚时代，架空19世纪",
    location_types=["飞艇", "工厂", "实验室", "钟楼", "地下城", "贵族庄园", "码头"],
    atmosphere_keywords=["蒸汽", "齿轮", "冒险", "维多利亚", "机械", "发明"],
    visual_style="steampunk aesthetic, brass and copper tones, gears and cogs, airships, Victorian architecture, goggles and top hats, steam everywhere",
    color_palette=["#c9ae74", "#8a6a4a", "#b87c4a", "#4a3a2a", "#6a8a4a", "#9a7a5a"],
    
    character_archetypes={
        "protagonist": _create_archetype(
            identities=["发明家", "飞行员", "探险家", "工程师", "侦探"],
            visual_anchor="wearing goggles, leather jacket, brass accessories, mechanical arm, tool belt",
            voice_profile="enthusiastic, educated British accent, slightly eccentric",
            traits=["聪明", "冒险精神", "理想主义", "执着", "叛逆"]
        ),
        "antagonist": _create_archetype(
            identities=["工业巨头", "疯狂科学家", "贵族", "军方", "间谍"],
            visual_anchor="top hat, monocle, ornate clothing, hidden mechanical weapon",
            voice_profile="refined, condescending, cold",
            traits=["贪婪", "权力欲", "傲慢", "冷酷", "控制"]
        ),
        "support": _create_archetype(
            identities=["助手", "机械师", "飞行员", "街头少年", "贵族小姐"],
            visual_anchor="working class clothing, goggles around neck, oil stains",
            voice_profile="working class accent, loyal, witty",
            traits=["忠诚", "机智", "勇敢", "幽默", "善良"]
        )
    },
    
    element_mappings={
        "书生": "发明家",
        "秀才": "学者",
        "小姐": "贵族小姐/飞行员",
        "姑娘": "街头少女",
        "老媪": "机械师/发明家遗孀",
        "婆婆": "工厂主",
        "古装": "维多利亚服饰",
        "庭院": "庄园/实验室",
        "花园": "空中花园",
        "书房": "实验室/图书馆",
        "闺房": "阁楼工作室",
        "思念": "执念",
        "爱情": "冒险伙伴",
        "姻缘": "合作",
        "死亡": "实验事故",
        "鬼魂": "机械幽灵",
        "笑声": "豪爽大笑",
        "花": "机械花/蒸汽花"
    },
    
    forbidden_words=["电子", "数字", "网络", "塑料", "现代科技"],
    
    narration_style="维多利亚小说风格，充满冒险气息",
    narration_examples=[
        "在那个蒸汽与齿轮的时代，一切都充满可能。",
        "天空不再是人类的极限。",
        "每一个齿轮转动，都诉说着一个故事。",
        "科学的边界，就是冒险的开始。"
    ],
    
    camera_style="广角飞艇，机械特写，暖色调",
    camera_movements=["STATIC", "PAN_LEFT", "PAN_RIGHT", "TILT_UP", "TILT_DOWN"],
    
    character_behavior_mappings=[
        _create_behavior(
            original="婴宁",
            core_behavior="爱笑、天真、拈花、不谙世事",
            adapted_behavior="发明家制造的机械少女，笑声是发条转动的声音，手持机械花，天真地探索世界",
            voice_signature="发条转动般的笑声，说话带着机械的节奏，却充满情感",
            visual_signature="铜制外壳，玻璃眼睛，手持机械花，蒸汽从关节处飘出",
            interaction_pattern="用机械花和笑声与人交流，逐渐学会人类的情感，是发明家最骄傲的作品"
        )
    ],
    
    sfx_style="齿轮转动、蒸汽喷射、发条声",
    sfx_examples=[
        "SFX: gears_turning, mechanical",
        "SFX: steam_release, hissing",
        "SFX: clockwork_winding, ticking",
        "SFX: airship_engines, humming",
        "SFX: brass_footsteps, clanking"
    ],
    
    vfx_style="蒸汽特效、齿轮动画、黄铜光泽",
    vfx_examples=[
        "VFX: steam_clouds, billowing",
        "VFX: spinning_gears, overlay",
        "VFX: brass_glow, metallic shine",
        "VFX: clockwork_mechanisms, visible"
    ]
)


# ========== 工具函数 ==========

def get_style_mapping(style_name: str) -> Optional[StyleMapping]:
    """获取风格映射配置"""
    return STYLE_MAPPINGS.get(style_name)


def get_all_styles() -> List[str]:
    """获取所有可用风格名称"""
    return list(STYLE_MAPPINGS.keys())


def get_style_names_by_category(category: StyleCategory) -> List[str]:
    """按分类获取风格名称"""
    return [name for name, mapping in STYLE_MAPPINGS.items() if mapping.category == category]


def get_character_behavior_mapping(style_name: str, original_name: str) -> Optional[CharacterBehaviorMapping]:
    """获取特定角色的行为映射"""
    mapping = get_style_mapping(style_name)
    if not mapping:
        return None
    
    for behavior in mapping.character_behavior_mappings:
        if behavior.original_name == original_name:
            return behavior
    return None


def get_style_prompt_injection(style_name: str) -> str:
    """生成风格注入提示词片段"""
    mapping = get_style_mapping(style_name)
    if not mapping:
        return f"### 风格: {style_name}\n请将原著改编为{style_name}风格。"
    
    # 生成元素转换表
    element_lines = []
    for k, v in mapping.element_mappings.items():
        element_lines.append(f"| {k} | {v} |")
    
    # 生成角色行为映射
    behavior_lines = []
    for behavior in mapping.character_behavior_mappings:
        behavior_lines.append(f"""
#### {behavior.original_name} → {behavior.adapted_behavior.split('，')[0] if behavior.adapted_behavior else behavior.original_name}
- **核心行为**: {behavior.core_behavior}
- **重构行为**: {behavior.adapted_behavior}
- **声音特征**: {behavior.voice_signature}
- **视觉特征**: {behavior.visual_signature}
- **互动模式**: {behavior.interaction_pattern}
""")
    
    injection = f"""
### 风格名称
{style_name}

### 风格描述
{mapping.description}

### 时代背景
{mapping.era}

### 场景类型（从以下选择）
{', '.join(mapping.location_types)}

### 氛围关键词
{', '.join(mapping.atmosphere_keywords)}

### 视觉风格（用于生图）
{mapping.visual_style}

### 色彩方案
{', '.join(mapping.color_palette)}

### 角色原型

**主角**: {', '.join(mapping.character_archetypes['protagonist'].identities)}
- 视觉锚点: {mapping.character_archetypes['protagonist'].visual_anchor}
- 声音特征: {mapping.character_archetypes['protagonist'].voice_profile}
- 性格特征: {', '.join(mapping.character_archetypes['protagonist'].personality_traits)}

**对立角色**: {', '.join(mapping.character_archetypes['antagonist'].identities)}
- 视觉锚点: {mapping.character_archetypes['antagonist'].visual_anchor}
- 声音特征: {mapping.character_archetypes['antagonist'].voice_profile}

**配角**: {', '.join(mapping.character_archetypes['support'].identities)}

### 元素转换表（强制）
| 原著元素 | 转换后 |
|---------|--------|
{chr(10).join(element_lines)}

### 角色灵魂保留（必须遵守）
{''.join(behavior_lines) if behavior_lines else '无特定行为映射，但必须保留原著角色的核心行为特征'}

### 禁止词汇（绝对不得出现）
{', '.join(mapping.forbidden_words)}

### 旁白风格要求
{mapping.narration_style}

正确旁白示例:
{chr(10).join(['- ' + ex for ex in mapping.narration_examples])}

### 推荐运镜风格
{mapping.camera_style}
可用运镜: {', '.join(mapping.camera_movements)}

### 音效风格
{mapping.sfx_style}
音效示例: {', '.join(mapping.sfx_examples)}

### 特效风格
{mapping.vfx_style}
特效示例: {', '.join(mapping.vfx_examples)}
"""
    return injection


# 测试
if __name__ == "__main__":
    print("=" * 70)
    print("风格映射库测试")
    print("=" * 70)
    
    for style_name in get_all_styles():
        print(f"\n{'='*50}")
        print(f"风格: {style_name}")
        print(f"{'='*50}")
        mapping = get_style_mapping(style_name)
        print(f"分类: {mapping.category.value}")
        print(f"时代: {mapping.era}")
        print(f"场景类型数: {len(mapping.location_types)}")
        print(f"角色行为映射数: {len(mapping.character_behavior_mappings)}")
        print(f"禁止词汇数: {len(mapping.forbidden_words)}")
        
        # 测试行为映射
        for behavior in mapping.character_behavior_mappings:
            print(f"  - {behavior.original_name}: {behavior.adapted_behavior[:50]}...")
    
    print(f"\n{'='*70}")
    print(f"总计: {len(get_all_styles())} 种风格")
    print("=" * 70)