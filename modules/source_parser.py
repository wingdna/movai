# modules/source_parser.py
"""
模块1增强版：智能数据采集与预处理
支持：URL、本地文件、直接文本输入
自动提取标题、作者、正文，无需手动配置
"""
import json
import re
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
import requests
from urllib.parse import urlparse


class SourceParser:
    """智能数据采集与预处理中心"""
    
    def __init__(self, output_dir: str = "./data/input"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def parse(self, source: Union[str, Path], source_type: str = "auto") -> Path:
        """
        解析输入源，生成 raw_source.json
        
        Args:
            source: 输入源（URL、文件路径、或直接文本）
            source_type: 类型提示（auto/url/file/text）
            
        Returns:
            raw_source.json 路径
        """
        print("\n" + "="*60)
        print("📥 模块1：数据采集与预处理中心")
        print("="*60)
        
        # 自动判断输入类型
        if source_type == "auto":
            source_type = self._detect_source_type(source)
        
        print(f"🔍 检测到输入类型: {source_type}")
        
        # 根据类型解析
        if source_type == "url":
            raw_data = self._parse_url(source)
        elif source_type == "file":
            raw_data = self._parse_file(source)
        elif source_type == "text":
            raw_data = self._parse_text(source)
        else:
            raise ValueError(f"不支持的输入类型: {source_type}")
        
        # 文本清洗和分块
        raw_data = self._clean_and_chunk(raw_data)
        
        # 保存
        output_path = self.output_dir / "raw_source.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 解析完成，已保存至: {output_path}")
        print(f"   - 标题: {raw_data['title']}")
        print(f"   - 作者: {raw_data.get('author', '未知')}")
        print(f"   - 文本长度: {len(raw_data.get('full_text', ''))} 字符")
        print(f"   - 分块数: {len(raw_data.get('text_chunks', []))}")
        
        return output_path
    
    def _detect_source_type(self, source: str) -> str:
        """自动检测输入类型"""
        # 检查是否为URL
        if source.startswith(('http://', 'https://')):
            return "url"
        
        # 检查是否为文件路径
        if Path(source).exists():
            return "file"
        
        # 默认为文本
        return "text"
    
    def _parse_url(self, url: str) -> Dict[str, Any]:
        """从URL解析内容"""
        print(f"🌐 正在抓取URL: {url}")
        
        # 支持多种来源
        if 'wikipedia' in url:
            return self._parse_wikipedia(url)
        elif 'gutenberg' in url:
            return self._parse_gutenberg(url)
        elif 'zhihu' in url:
            return self._parse_zhihu(url)
        else:
            # 通用网页解析
            return self._parse_generic_webpage(url)
    
    def _parse_wikipedia(self, url: str) -> Dict[str, Any]:
        """解析维基百科"""
        try:
            # 提取页面标题
            title_match = re.search(r'/wiki/([^/#?]+)', url)
            if not title_match:
                raise ValueError("无法解析维基百科URL")
            
            page_title = title_match.group(1).replace('_', ' ')
            
            # 使用维基百科API
            api_url = f"https://en.wikipedia.org/w/api.php"
            params = {
                "action": "parse",
                "page": page_title,
                "format": "json",
                "prop": "text"
            }
            
            response = requests.get(api_url, params=params, timeout=10)
            data = response.json()
            
            # 简单提取文本（去除HTML标签）
            html_content = data.get("parse", {}).get("text", {}).get("*", "")
            text = re.sub(r'<[^>]+>', ' ', html_content)
            text = re.sub(r'\s+', ' ', text).strip()
            
            # 提取前5000字作为主要内容
            full_text = text[:15000] if len(text) > 15000 else text
            
            return {
                "title": page_title,
                "author": "Wikipedia",
                "source_url": url,
                "full_text": full_text,
                "metadata": {"source_type": "wikipedia"}
            }
            
        except Exception as e:
            print(f"⚠️ 维基百科解析失败: {e}")
            return self._parse_generic_webpage(url)
    
    def _parse_gutenberg(self, url: str) -> Dict[str, Any]:
        """解析古登堡计划"""
        # 简化实现：直接抓取文本
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        
        text = response.text
        
        # 提取标题（常见模式）
        title_match = re.search(r'<title>(.*?)</title>', text, re.IGNORECASE)
        title = title_match.group(1) if title_match else "未知标题"
        
        # 提取正文（简单处理）
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return {
            "title": title,
            "author": "古登堡计划",
            "source_url": url,
            "full_text": text[:20000],
            "metadata": {"source_type": "gutenberg"}
        }
    
    def _parse_zhihu(self, url: str) -> Dict[str, Any]:
        """解析知乎文章"""
        # 简化实现
        response = requests.get(url, timeout=10)
        text = response.text
        
        # 提取标题
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.IGNORECASE)
        title = title_match.group(1) if title_match else "知乎文章"
        
        # 提取正文
        content_match = re.search(r'<div[^>]*class="RichText[^"]*"[^>]*>(.*?)</div>', text, re.DOTALL)
        content = content_match.group(1) if content_match else text
        
        content = re.sub(r'<[^>]+>', ' ', content)
        content = re.sub(r'\s+', ' ', content).strip()
        
        return {
            "title": title,
            "author": "知乎用户",
            "source_url": url,
            "full_text": content[:20000],
            "metadata": {"source_type": "zhihu"}
        }
    
    def _parse_generic_webpage(self, url: str) -> Dict[str, Any]:
        """通用网页解析"""
        try:
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 提取标题
            title = soup.title.string if soup.title else "未知标题"
            title = title.strip()
            
            # 提取正文（优先找article/main/content标签）
            content_selectors = ['article', 'main', '[role="main"]', '.content', '#content']
            content = None
            
            for selector in content_selectors:
                elem = soup.select_one(selector)
                if elem:
                    content = elem.get_text()
                    break
            
            if not content:
                content = soup.body.get_text() if soup.body else ""
            
            # 清理文本
            content = re.sub(r'\n\s*\n', '\n\n', content)
            content = re.sub(r'\s+', ' ', content).strip()
            
            # 限制长度
            full_text = content[:20000] if len(content) > 20000 else content
            
            return {
                "title": title,
                "author": "未知",
                "source_url": url,
                "full_text": full_text,
                "metadata": {"source_type": "generic"}
            }
            
        except Exception as e:
            raise Exception(f"网页解析失败: {e}")
    
    def _parse_file(self, file_path: str) -> Dict[str, Any]:
        """解析本地文件"""
        file_path = Path(file_path)
        print(f"📄 正在读取文件: {file_path.name}")
        
        # 根据扩展名选择解析方式
        ext = file_path.suffix.lower()
        
        if ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                full_text = f.read()
            
            # 尝试提取标题（第一行）
            lines = full_text.split('\n')
            title = lines[0].strip() if lines else file_path.stem
            if len(title) > 100:
                title = file_path.stem
            
            return {
                "title": title,
                "author": "未知",
                "source_file": str(file_path),
                "full_text": full_text,
                "metadata": {"source_type": "txt"}
            }
            
        elif ext in ['.json']:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 如果是标准格式，直接返回
            if 'full_text' in data or 'text_chunks' in data:
                return data
            
            # 否则尝试提取
            return {
                "title": data.get('title', file_path.stem),
                "author": data.get('author', '未知'),
                "full_text": data.get('content', data.get('text', json.dumps(data))),
                "metadata": {"source_type": "json"}
            }
            
        elif ext in ['.md']:
            with open(file_path, 'r', encoding='utf-8') as f:
                full_text = f.read()
            
            # 提取标题（第一个#标题）
            title_match = re.search(r'^#\s+(.+)$', full_text, re.MULTILINE)
            title = title_match.group(1) if title_match else file_path.stem
            
            return {
                "title": title,
                "author": "未知",
                "source_file": str(file_path),
                "full_text": full_text,
                "metadata": {"source_type": "markdown"}
            }
        
        else:
            # 尝试作为文本读取
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    full_text = f.read()
                
                return {
                    "title": file_path.stem,
                    "author": "未知",
                    "source_file": str(file_path),
                    "full_text": full_text,
                    "metadata": {"source_type": "text"}
                }
            except:
                raise ValueError(f"不支持的文件类型: {ext}")
    
    def _parse_text(self, text: str) -> Dict[str, Any]:
        """直接解析文本"""
        # 尝试提取标题（第一行）
        lines = text.strip().split('\n')
        first_line = lines[0].strip()
        
        # 如果第一行较短，可能是标题
        if len(first_line) < 50 and not first_line.endswith(('.', '！', '？')):
            title = first_line
            content = '\n'.join(lines[1:])
        else:
            title = "用户输入的文本"
            content = text
        
        return {
            "title": title,
            "author": "用户",
            "full_text": content,
            "metadata": {"source_type": "direct_text"}
        }
    
    def _clean_and_chunk(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """清洗文本并分块"""
        full_text = raw_data.get('full_text', '')
        
        # 清洗
        cleaned_text = self._clean_text(full_text)
        
        # 分块（按段落，每块约2000字）
        chunks = self._chunk_text(cleaned_text, chunk_size=2000)
        
        # 更新数据
        raw_data['clean_text'] = cleaned_text
        raw_data['text_chunks'] = chunks
        raw_data['char_count'] = len(cleaned_text)
        raw_data['chunk_count'] = len(chunks)
        raw_data['processed_at'] = datetime.now().isoformat()
        
        return raw_data
    
    def _clean_text(self, text: str) -> str:
        """文本清洗"""
        # 移除多余空白
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 移除常见的垃圾内容
        patterns = [
            r'Copyright.*?\n',
            r'All rights reserved.*?\n',
            r'http[s]?://\S+',
            r'[◆◇■□▶△▽▲▼●○★☆]+',
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def _chunk_text(self, text: str, chunk_size: int = 2000) -> list:
        """将文本分块"""
        # 按段落分割
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) <= chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks


# 快捷函数
def parse_source(source: Union[str, Path], output_dir: str = "./data/input") -> Path:
    """快捷解析函数"""
    parser = SourceParser(output_dir)
    return parser.parse(source)


# 命令行入口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="数据采集与预处理中心")
    parser.add_argument("source", help="输入源（URL/文件路径/直接文本）")
    parser.add_argument("--output", default="./data/input", help="输出目录")
    parser.add_argument("--type", choices=["auto", "url", "file", "text"], default="auto", help="输入类型")
    
    args = parser.parse_args()
    
    # 如果是直接文本，从stdin读取
    if args.type == "text" or (args.type == "auto" and not args.source.startswith(('http://', 'https://')) and not Path(args.source).exists()):
        # 作为文本处理
        pass
    
    parse_source(args.source, args.output)