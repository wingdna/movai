# run.py
"""
幻影卷轴 - 交互式菜单脚本
提供友好的命令行菜单界面
包含模块4：音频锚点工坊、模块5：视觉资产铸造厂、模块6：2.5D渲染合成器
"""
import sys
import os
import subprocess
import json
import time
import shutil
import traceback
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))

from config.settings import (
    STYLES, 
    DEFAULT_CONFIG, 
    validate_config, 
    check_balance,
    SILICONFLOW_API_KEY
)

# 全局测试模式标志
TEST_MODE = False
TEST_SCENE_COUNT = 3


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    🎬 幻影卷轴 影视化生产线                    ║
║                     Phantom Scroll Pipeline                  ║
╚══════════════════════════════════════════════════════════════╝
    """)


def print_menu():
    test_status = "🔬 测试模式 (ON)" if TEST_MODE else "🎬 正式模式"
    print("\n" + "="*60)
    print(f"📋 主菜单 [{test_status}]")
    print("="*60)
    print("1. 🚀 完整管线（模块1→2→3→4→5→6）")
    print("2. 📥 仅运行模块1（解析文本）")
    print("3. 🎬 仅运行模块2（导演引擎）")
    print("4. ✍️ 仅运行模块3（编剧引擎）")
    print("5. 🎵 仅运行模块4（音频锚点工坊）")
    print("6. 🎨 仅运行模块5（视觉资产铸造厂）")
    print("7. 🎬 仅运行模块6（2.5D渲染合成器）")
    print("8. 🎭 生成角色四方向参考图")
    print("9. 🔬 切换测试模式/正式模式")
    print("10. ⚙️ 查看配置")
    print("11. 💰 检查账户余额")
    print("0. 🚪 退出")
    print("="*60)


def toggle_test_mode():
    global TEST_MODE
    TEST_MODE = not TEST_MODE
    if TEST_MODE:
        print(f"\n🔬 已切换到【测试模式】- 仅生成前 {TEST_SCENE_COUNT} 个场景")
        print("   💡 测试模式会大幅节省时间和算力")
    else:
        print("\n🎬 已切换到【正式模式】- 生成所有场景")
    input("\n按回车键继续...")


def get_test_scene_count():
    global TEST_SCENE_COUNT
    if TEST_MODE:
        print(f"\n🔬 测试模式：将只生成前 {TEST_SCENE_COUNT} 个场景")
        change = input(f"是否修改测试场景数量？(当前{TEST_SCENE_COUNT}) [y/N]: ").strip().lower()
        if change == 'y':
            try:
                new_count = int(input(f"请输入测试场景数量 (1-10): ").strip())
                if 1 <= new_count <= 10:
                    TEST_SCENE_COUNT = new_count
                    print(f"✅ 已设置测试场景数量为 {TEST_SCENE_COUNT}")
                else:
                    print(f"❌ 无效数量，保持 {TEST_SCENE_COUNT}")
            except:
                print(f"❌ 无效输入，保持 {TEST_SCENE_COUNT}")
    return TEST_SCENE_COUNT


def check_output_files(output_dir="./data/output"):
    """检查输出文件是否存在"""
    files = {
        "raw_source.json": Path(output_dir).parent / "input" / "raw_source.json",
        "project_bible.json": Path(output_dir) / "project_bible.json",
        "beat_sheet.json": Path(output_dir) / "beat_sheet.json",
        "master_script.json": Path(output_dir) / "master_script.json",
        "timed_script.json": Path(output_dir) / "timed_script.json"
    }
    
    existing = []
    missing = []
    for name, path in files.items():
        if path.exists():
            existing.append(name)
        else:
            missing.append(name)
    return existing, missing


def get_input_source():
    print("\n📖 选择输入方式:")
    print("1. 输入URL")
    print("2. 本地文件路径")
    print("3. 直接粘贴文本")
    
    choice = input("\n请选择 (1-3): ").strip()
    
    if choice == "1":
        source = input("请输入URL: ").strip()
        source_type = "url"
    elif choice == "2":
        source = input("请输入文件路径: ").strip()
        source_type = "file"
    else:
        print("请输入文本内容（输入空行结束）:")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        source = "\n".join(lines)
        source_type = "text"
    
    return source, source_type


def select_style():
    print("\n🎨 请选择改编风格:")
    print("="*50)
    
    mid = len(STYLES) // 2
    for i in range(mid):
        left = f"{i+1:2}. {STYLES[i]}"
        right = f"{i+mid+1:2}. {STYLES[i+mid]}" if i+mid < len(STYLES) else ""
        print(f"{left:<30} {right}")
    
    if len(STYLES) % 2 == 1:
        print(f"{mid+1:2}. {STYLES[mid]}")
    
    print("\n0. 使用默认风格")
    
    choice = input(f"\n请选择 (0-{len(STYLES)}): ").strip()
    
    if choice == "0":
        return DEFAULT_CONFIG["style"]
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(STYLES):
            return STYLES[idx]
    except:
        pass
    
    return DEFAULT_CONFIG["style"]


def run_module1(source, source_type, output_dir="./data/input"):
    print("\n" + "="*60)
    print("📥 运行模块1：数据采集与预处理")
    print("="*60)
    
    from modules.source_parser import SourceParser
    parser = SourceParser(output_dir)
    
    if source_type == "text":
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(source)
            temp_path = f.name
        result = parser.parse(temp_path, source_type="file")
        os.unlink(temp_path)
        return result
    else:
        return parser.parse(source, source_type)


def run_module2(style, output_dir="./data/output"):
    print("\n" + "="*60)
    print("🎬 运行模块2：总导演引擎")
    print("="*60)
    
    raw_source = Path(output_dir).parent / "input" / "raw_source.json"
    if not raw_source.exists():
        raise FileNotFoundError(f"请先运行模块1生成 {raw_source}")
    
    cmd = [sys.executable, "modules/director_engine.py", "--input", str(raw_source), 
           "--output", output_dir, "--style", style]
    subprocess.run(cmd, check=True)
    return Path(output_dir) / "project_bible.json", Path(output_dir) / "beat_sheet.json"


def run_module3(output_dir="./data/output"):
    print("\n" + "="*60)
    print("✍️ 运行模块3：执笔编剧引擎")
    print("="*60)
    
    bible_path = Path(output_dir) / "project_bible.json"
    beat_path = Path(output_dir) / "beat_sheet.json"
    
    if not bible_path.exists():
        raise FileNotFoundError(f"请先运行模块2生成 {bible_path}")
    if not beat_path.exists():
        raise FileNotFoundError(f"请先运行模块2生成 {beat_path}")
    
    cmd = [sys.executable, "modules/writer_engine.py", "--bible", str(bible_path), 
           "--beat", str(beat_path), "--output", output_dir]
    subprocess.run(cmd, check=True)
    return Path(output_dir) / "master_script.json"


def run_module4(script_path=None, output_dir="./data/output", audio_dir="./data/output/audio"):
    print("\n" + "="*60)
    print("🎵 运行模块4：音频锚点工坊")
    print("="*60)
    
    if script_path is None:
        script_path = Path(output_dir) / "master_script.json"
    else:
        script_path = Path(script_path)
    
    if not script_path.exists():
        raise FileNotFoundError(f"剧本文件不存在: {script_path}")
    
    audio_dir_path = Path(audio_dir)
    audio_dir_path.mkdir(parents=True, exist_ok=True)
    
    from modules.audio_anchor_forge import AudioAnchorForge
    forge = AudioAnchorForge(str(script_path), output_dir, audio_dir)
    return forge.run()


def run_module5(script_path=None, output_dir="./data/output", visuals_dir="./data/output/visuals", async_mode=False):
    """运行模块5：视觉资产铸造厂 - 支持测试模式"""
    print("\n" + "="*60)
    print("🎨 运行模块5：视觉资产铸造厂")
    print("="*60)
    
    if script_path is None:
        script_path = Path(output_dir) / "timed_script.json"
    else:
        script_path = Path(script_path)
    
    if not script_path.exists():
        raise FileNotFoundError(f"剧本文件不存在: {script_path}")
    
    visuals_dir_path = Path(visuals_dir)
    visuals_dir_path.mkdir(parents=True, exist_ok=True)
    
    from modules.visual_asset_foundry import VisualAssetFoundry, AsyncVisualAssetFoundry
    
    # 测试模式下，修改剧本只保留前 N 个场景
    if TEST_MODE:
        print(f"\n🔬 测试模式：只生成前 {TEST_SCENE_COUNT} 个场景")
        with open(script_path, 'r', encoding='utf-8') as f:
            script_data = json.load(f)
        
        original_scenes = script_data.get("scenes", [])
        if len(original_scenes) > TEST_SCENE_COUNT:
            script_data["scenes"] = original_scenes[:TEST_SCENE_COUNT]
            script_data["total_scenes"] = TEST_SCENE_COUNT
            
            test_script_path = Path(output_dir) / "timed_script_test.json"
            with open(test_script_path, 'w', encoding='utf-8') as f:
                json.dump(script_data, f, ensure_ascii=False, indent=2)
            script_path = test_script_path
            print(f"   📝 已创建测试剧本: {script_path}")
    
    if async_mode:
        foundry = AsyncVisualAssetFoundry(str(script_path), output_dir, visuals_dir)
        import asyncio
        visuals_dir_result, poster_path = asyncio.run(foundry.run_async())
    else:
        foundry = VisualAssetFoundry(str(script_path), output_dir, visuals_dir)
        visuals_dir_result, poster_path = foundry.run()
    
    # 清理测试文件
    if TEST_MODE and script_path != Path(output_dir) / "timed_script.json":
        try:
            os.remove(script_path)
        except:
            pass
    
    return visuals_dir_result, poster_path


def run_module6(script_path=None, output_dir="./data/output", 
                audio_dir="./data/output/audio", visuals_dir="./data/output/visuals"):
    """运行模块6：2.5D 动态渲染与合成器"""
    print("\n" + "="*60)
    print("🎬 运行模块6：2.5D 动态渲染与合成器")
    print("="*60)
    
    if script_path is None:
        script_path = Path(output_dir) / "timed_script.json"
    else:
        script_path = Path(script_path)
    
    if not script_path.exists():
        raise FileNotFoundError(f"剧本文件不存在: {script_path}")
    
    from modules.visual_asset_foundry import VisualAssetFoundry
    
    # 测试模式下，修改剧本只保留前 N 个场景
    if TEST_MODE:
        print(f"\n🔬 测试模式：只渲染前 {TEST_SCENE_COUNT} 个场景")
        with open(script_path, 'r', encoding='utf-8') as f:
            script_data = json.load(f)
        
        original_scenes = script_data.get("scenes",[])
        if len(original_scenes) > TEST_SCENE_COUNT:
            script_data["scenes"] = original_scenes[:TEST_SCENE_COUNT]
            script_data["total_scenes"] = TEST_SCENE_COUNT
            
            test_script_path = Path(output_dir) / "timed_script_test.json"
            with open(test_script_path, 'w', encoding='utf-8') as f:
                json.dump(script_data, f, ensure_ascii=False, indent=2)
            script_path = test_script_path
            print(f"   📝 已创建测试剧本: {script_path}")
    
    # 动态导入 06_render_engine_advanced (修复模块导入问题)
    import importlib.util
    
    # 确保寻找的是你刚才更新的高级版模块 (06_render_engine_advanced.py)
    # 如果你把它重命名回了 06_render_engine.py，请将这里改回去
    engine_path = Path(__file__).parent / "modules" / "06_render_engine_advanced.py"
    if not engine_path.exists():
        # 兼容旧的文件名
        engine_path = Path(__file__).parent / "modules" / "06_render_engine.py"
        
    spec = importlib.util.spec_from_file_location("render_engine", engine_path)
    render_engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(render_engine)
    AdvancedRenderEngine = render_engine.AdvancedRenderEngine
    
    # 运行渲染
    engine = AdvancedRenderEngine(
        script_path=str(script_path),
        audio_dir=audio_dir,
        visuals_dir=visuals_dir,
        output_dir=output_dir,
        output_filename="final_render.mp4",
        fps=12,
        quality=5,
        target_width=1920,
        preset="ultrafast"
    )
    result = engine.run()
    
    # 清理测试文件
    if TEST_MODE and script_path != Path(output_dir) / "timed_script.json":
        try:
            os.remove(script_path)
        except:
            pass
    
    return result
    
def run_character_generation(output_dir="./data/output"):
    """生成角色四方向参考图"""
    print("\n" + "="*60)
    print("🎭 生成角色四方向参考图")
    print("="*60)
    
    try:
        from modules.visual_asset_foundry import VisualAssetFoundry
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return
    
    bible_path = Path(output_dir) / "project_bible.json"
    if not bible_path.exists():
        bible_path = Path(output_dir).parent / "output" / "project_bible.json"
        if not bible_path.exists():
            print("❌ 未找到 project_bible.json，请先运行模块2")
            return
    
    foundry = VisualAssetFoundry(
        script_path=Path(output_dir) / "master_script.json",
        output_dir=output_dir,
        visuals_dir=Path(output_dir) / "visuals"
    )
    foundry.generate_character_references()


def show_config():
    global TEST_MODE, TEST_SCENE_COUNT
    print("\n" + "="*60)
    print("⚙️ 当前配置")
    print("="*60)
    key_display = SILICONFLOW_API_KEY
    if key_display and len(key_display) > 14:
        key_display = f"{key_display[:10]}...{key_display[-4:]}"
    print(f"API Key: {key_display if key_display else '未设置'}")
    print(f"输出目录: {DEFAULT_CONFIG['output_dir']}")
    print(f"可用风格数: {len(STYLES)}")
    print(f"\n🔬 测试模式: {'开启' if TEST_MODE else '关闭'}")
    if TEST_MODE:
        print(f"   📊 测试场景数量: {TEST_SCENE_COUNT}")
    print("="*60)


def show_production_status(output_dir="./data/output"):
    existing, missing = check_output_files(output_dir)
    print("\n" + "="*60)
    print("📊 生产状态")
    print("="*60)
    print("\n✅ 已生成:")
    for f in existing:
        print(f"   - {f}")
    if missing:
        print("\n❌ 未生成:")
        for f in missing:
            print(f"   - {f}")
    
    visuals_dir = Path(output_dir) / "visuals"
    if visuals_dir.exists():
        rgb_files = list(visuals_dir.glob("*_rgb.png"))
        depth_files = list(visuals_dir.glob("*_depth.png"))
        print(f"\n🎨 视觉资产:")
        print(f"   - RGB 图像: {len(rgb_files)} 个")
        print(f"   - 深度图: {len(depth_files)} 个")
    
    # 检查最终视频
    final_video = Path(output_dir) / "final_render.mp4"
    if final_video.exists():
        size_mb = final_video.stat().st_size / (1024 * 1024)
        print(f"\n🎬 最终视频:")
        print(f"   - {final_video.name} ({size_mb:.1f} MB)")
    
    char_dir = Path("./data/characters")
    if char_dir.exists():
        sheets = list(char_dir.glob("*_sheet.png"))
        if sheets:
            print(f"\n🎭 角色四方向图:")
            for s in sheets:
                print(f"   - {s.name}")
    print("="*60)


def main():
    clear_screen()
    print_banner()
    
    if not validate_config():
        print("\n请先配置后再运行")
        input("\n按回车键退出...")
        return
    
    print("\n正在检查账户余额...")
    check_balance()
    
    while True:
        print_menu()
        choice = input("\n请选择 (0-11): ").strip()
        
        if choice == "0":
            print("\n👋 再见！")
            break
        
        elif choice == "1":
            print("\n🚀 启动完整管线...")
            try:
                source, source_type = get_input_source()
                style = select_style()
                if TEST_MODE:
                    get_test_scene_count()
                
                run_module1(source, source_type)
                print(f"✅ 模块1完成")
                
                run_module2(style)
                print(f"✅ 模块2完成")
                
                run_module3()
                print(f"✅ 模块3完成")
                
                run_module4()
                print(f"✅ 模块4完成")
                
                run_module5()
                print(f"✅ 模块5完成")
                
                run_module6()
                print(f"✅ 模块6完成")
                
                print("\n" + "="*60)
                print("🎉 完整管线运行成功！")
                print("="*60)
                print(f"\n📁 输出目录: ./data/output")
                print(f"🎬 最终视频: ./data/output/final_render.mp4")
                
            except Exception as e:
                print(f"\n❌ 运行失败: {e}")
                traceback.print_exc()
            input("\n按回车键继续...")
            clear_screen()
            print_banner()
        
        elif choice == "2":
            print("\n📥 仅运行模块1...")
            try:
                source, source_type = get_input_source()
                run_module1(source, source_type)
            except Exception as e:
                print(f"\n❌ 运行失败: {e}")
                traceback.print_exc()
            input("\n按回车键继续...")
            clear_screen()
            print_banner()
        
        elif choice == "3":
            print("\n🎬 仅运行模块2...")
            try:
                style = select_style()
                run_module2(style)
            except Exception as e:
                print(f"\n❌ 运行失败: {e}")
                traceback.print_exc()
            input("\n按回车键继续...")
            clear_screen()
            print_banner()
        
        elif choice == "4":
            print("\n✍️ 仅运行模块3...")
            try:
                run_module3()
            except Exception as e:
                print(f"\n❌ 运行失败: {e}")
                traceback.print_exc()
            input("\n按回车键继续...")
            clear_screen()
            print_banner()
        
        elif choice == "5":
            print("\n🎵 仅运行模块4...")
            try:
                existing, _ = check_output_files()
                if "master_script.json" not in existing:
                    print("⚠️ 未找到 master_script.json")
                else:
                    run_module4()
            except Exception as e:
                print(f"\n❌ 运行失败: {e}")
                traceback.print_exc()
            input("\n按回车键继续...")
            clear_screen()
            print_banner()
        
        elif choice == "6":
            print("\n🎨 仅运行模块5...")
            try:
                existing, _ = check_output_files()
                if "timed_script.json" not in existing:
                    print("⚠️ 未找到 timed_script.json")
                else:
                    if TEST_MODE:
                        get_test_scene_count()
                    use_async = input("是否使用异步模式？(y/n): ").strip().lower()
                    run_module5(async_mode=(use_async == 'y'))
            except Exception as e:
                print(f"\n❌ 运行失败: {e}")
                traceback.print_exc()
            input("\n按回车键继续...")
            clear_screen()
            print_banner()
        
        elif choice == "7":
            print("\n🎬 仅运行模块6...")
            try:
                existing, _ = check_output_files()
                if "timed_script.json" not in existing:
                    print("⚠️ 未找到 timed_script.json，请先运行模块1-5")
                else:
                    if TEST_MODE:
                        get_test_scene_count()
                    run_module6()
            except Exception as e:
                print(f"\n❌ 运行失败: {e}")
                traceback.print_exc()
            input("\n按回车键继续...")
            clear_screen()
            print_banner()
        
        elif choice == "8":
            print("\n🎭 生成角色四方向参考图...")
            try:
                run_character_generation()
            except Exception as e:
                print(f"\n❌ 运行失败: {e}")
                traceback.print_exc()
            input("\n按回车键继续...")
            clear_screen()
            print_banner()
        
        elif choice == "9":
            toggle_test_mode()
            clear_screen()
            print_banner()
        
        elif choice == "10":
            show_config()
            input("\n按回车键继续...")
            clear_screen()
            print_banner()
        
        elif choice == "11":
            print("\n💰 检查账户余额...")
            check_balance()
            show_production_status()
            input("\n按回车键继续...")
            clear_screen()
            print_banner()
        
        else:
            print("\n❌ 无效选择")
            time.sleep(1)


if __name__ == "__main__":
    main()