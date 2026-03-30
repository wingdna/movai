# modules/sfx_downloader.py
import requests
import os
import random
import shutil
import re
import hashlib
from pathlib import Path
from dotenv import load_dotenv

class SFXDownloader:
    def __init__(self, api_key=None, cache_dir="./cache/sfx", proxy_host=None, proxy_port=None, force_redownload=True):
        load_dotenv()
        self.freesound_key = api_key or os.getenv("FREESOUND_TOKEN") or os.getenv("MOVAI_FREESOUND_TOKEN")
        self.jamendo_key = os.getenv("JAMENDO_API_KEY", "d8098942")
        
        # ⚠️ 架构师指令：ElevenLabs 额度已干涸，强制将其关闭，防止浪费时间。
        self.elevenlabs_key = None 

        self.base_url_freesound = "https://freesound.org/apiv2"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.force_redownload = force_redownload

        self.proxies = None
        if proxy_host and proxy_port:
            proxy_url = f"http://{proxy_host}:{proxy_port}"
            self.proxies = {"http": proxy_url, "https": proxy_url}

        print(f"\n      🚀 [Audio] 极限求生声学引擎已就绪 | ElevenLabs:[强制离线]")

    def download_sfx(self, query, output_path, duration=5):
        query_hash = hashlib.md5(query.encode()).hexdigest()[:10]
        cache_file = self.cache_dir / f"sfx_{query_hash}_{duration}.mp3"

        if not self.force_redownload and cache_file.exists():
            shutil.copy2(cache_file, output_path)
            return True

        if self.freesound_key and self._fetch_freesound(query, output_path, type="sfx"):
            shutil.copy2(output_path, cache_file)
            return True
            
        return self._fallback(output_path, "sfx")

    def download_bgm(self, query, output_path, duration=30):
        query_hash = hashlib.md5(query.encode()).hexdigest()[:10]
        cache_file = self.cache_dir / f"bgm_{query_hash}_{duration}.mp3"

        if not self.force_redownload and cache_file.exists():
            shutil.copy2(cache_file, output_path)
            return True

        if self.jamendo_key and self._fetch_jamendo(query, output_path):
            shutil.copy2(output_path, cache_file)
            return True
            
        if self.freesound_key and self._fetch_freesound(query, output_path, type="bgm"):
            shutil.copy2(output_path, cache_file)
            return True
            
        return self._fallback(output_path, "bgm")

    def _fetch_jamendo(self, query, output_path):
        """修复版 Jamendo：放弃复杂交集，使用单兵突破"""
        print(f"      🎵 [Jamendo] 正在热榜搜寻配乐: {query}")
        url = "https://api.jamendo.com/v3.0/tracks/"
        
        # 降维映射：只保留一个极其广泛的标签
        emotion_map = {
            "tension": "suspense",
            "mystery": "ambient",
            "epic": "epic",
            "wonder": "cinematic",
            "sad": "sad",
            "action": "electronic",
            "horror": "dark"
        }
        clean_query = str(query).lower().strip()
        core_tag = emotion_map.get(clean_query, "cinematic")
        print(f"      [Jamendo] 使用核心标签: [{core_tag}]")

        params = {
            "client_id": self.jamendo_key,
            "format": "json",
            "limit": 5, # 多拉几个备胎
            "tags": core_tag, # 抛弃坑爹的 fuzzytags，使用标准 tags
            "include": "musicinfo"
        }
        
        try:
            res = requests.get(url, params=params, timeout=20, proxies=self.proxies)
            if res.status_code == 200:
                results = res.json().get('results',[])
                if results:
                    # 随机挑一首，防止每次背景音乐都一样
                    track = random.choice(results)
                    if track.get('audio'):
                        print(f"      [Jamendo] 命中大碟: 《{track.get('name')}》")
                        with requests.get(track['audio'], stream=True, timeout=60, proxies=self.proxies) as r:
                            r.raise_for_status()
                            with open(output_path, "wb") as f:
                                for chunk in r.iter_content(chunk_size=16384):
                                    if chunk: f.write(chunk)
                        print(f"      ✅ [Jamendo] 配乐拉取成功！")
                        return True
            print(f"      ❌ [Jamendo] 未能找到任何曲目。")
        except Exception as e:
            print(f"      🚨 [Jamendo] 网络异常: {e}")
        return False

    def _fetch_freesound(self, query, output_path, type="bgm"):
        """修复版 Freesound：长句降维，提取核心名词"""
        # 将 "pulsating_heartbeat_monitor" 降维成 "heartbeat"
        core_words = re.findall(r'[a-zA-Z]+', query)
        search_term = random.choice(core_words) if core_words else "glitch"
        if len(search_term) < 3 and len(core_words) > 1:
            search_term = core_words[1]
            
        print(f"      [Freesound] 启动降维雷达 (原:{query} -> 搜:{search_term})")
        headers = {'Authorization': f'Token {self.freesound_key}', 'User-Agent': 'Mozilla/5.0'}
        
        # 放宽时长限制
        params = {"query": search_term, "sort": "rating_desc", "fields": "id,name,previews", "page_size": 3}
        
        try:
            res = requests.get(f"{self.base_url_freesound}/search/text/", params=params, headers=headers, timeout=20, proxies=self.proxies)
            if res.status_code == 200 and res.json().get('results'):
                # 拿最高分的那个
                url = res.json()['results'][0]['previews'].get('preview-hq-mp3') or res.json()['results'][0]['previews'].get('preview-lq-mp3')
                if url:
                    with requests.get(url, stream=True, timeout=30, proxies=self.proxies) as r:
                        r.raise_for_status()
                        with open(output_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=16384):
                                if chunk: f.write(chunk)
                    print(f"      ✅ [Freesound] 降维搜索抓取成功。")
                    return True
        except Exception as e:
            print(f"      🚨 [Freesound] 异常: {e}")
        return False

    def _fallback(self, output_path, type):
        """本地 NumPy 合成高级科幻音效兜底"""
        existing_caches = list(self.cache_dir.glob("*.mp3"))
        if existing_caches and random.random() > 0.3:
            src = random.choice(existing_caches)
            shutil.copy2(src, output_path)
            print(f"      ♻️ [Fallback] 挂载历史音频: {src.name}")
            return True
        
        try:
            # 绝杀：如果没网没缓存，直接用 CPU 算一段赛博朋克环境音
            import numpy as np
            import soundfile as sf
            sr = 44100
            t = np.linspace(0, 5, sr * 5)
            # 生成低频深空嗡嗡声 (Dark Ambient Drone)
            drone = np.sin(2 * np.pi * 55 * t) * 0.3 + np.sin(2 * np.pi * 56.5 * t) * 0.3
            # 加入微弱的无线电白噪声
            noise = np.random.normal(0, 0.05, len(t))
            # 渐入渐出
            fade = np.minimum(np.minimum(t, 1.0), np.minimum(5-t, 1.0))
            final_audio = (drone + noise) * fade
            sf.write(output_path, final_audio, sr)
            print(f"      🎛️[Fallback] 成功合成局域深空引擎音！")
            return True
        except:
            return False

def download_sfx_sync(query, output_path, duration=5):
    return SFXDownloader().download_sfx(query, output_path, duration)