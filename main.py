#!/usr/bin/env python3
"""
YouTube Subtitle Extractor
A simple GUI application to extract subtitles from YouTube videos
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import yt_dlp
import json


class YouTubeSubtitleExtractor:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube 字幕提取工具")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # 設置風格
        style = ttk.Style()
        style.theme_use('clam')

        # 建立主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 設置權重
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # URL 輸入框
        ttk.Label(main_frame, text="YouTube 網址:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.url_entry = ttk.Entry(main_frame, width=80)
        self.url_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.url_entry.bind('<Return>', lambda e: self.extract_subtitles())

        # 按鈕框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.extract_btn = ttk.Button(button_frame, text="提取字幕", command=self.extract_subtitles)
        self.extract_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.copy_btn = ttk.Button(button_frame, text="複製全部", command=self.copy_to_clipboard, state=tk.DISABLED)
        self.copy_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.save_btn = ttk.Button(button_frame, text="儲存為 TXT", command=self.save_to_file, state=tk.DISABLED)
        self.save_btn.pack(side=tk.LEFT)

        # 字幕顯示框
        ttk.Label(main_frame, text="提取的字幕:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky=tk.W, pady=(10, 5))

        self.text_display = scrolledtext.ScrolledText(main_frame, width=100, height=20, wrap=tk.WORD)
        self.text_display.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # 狀態標籤
        self.status_label = ttk.Label(main_frame, text="就緒", foreground="green")
        self.status_label.grid(row=5, column=0, sticky=tk.W, pady=(0, 5))

        self.subtitle_content = ""

    def set_status(self, message, color="black"):
        """更新狀態顯示"""
        self.status_label.config(text=message, foreground=color)
        self.root.update()

    def extract_subtitles(self):
        """在線程中提取字幕"""
        url = self.url_entry.get().strip()

        if not url:
            messagebox.showwarning("警告", "請輸入 YouTube 網址")
            return

        # 禁用提取按鈕防止重複提取
        self.extract_btn.config(state=tk.DISABLED)
        self.text_display.delete(1.0, tk.END)

        # 在新線程中執行提取
        thread = threading.Thread(target=self._extract_subtitles_thread, args=(url,))
        thread.daemon = True
        thread.start()

    def _extract_subtitles_thread(self, url):
        """線程中提取字幕的實際邏輯"""
        try:
            self.set_status("正在提取字幕...", "blue")

            # 配置 yt-dlp 選項
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'quiet': True,
                'no_warnings': True,
                'subtitlesformat': 'srt/best',
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # 優先使用中文字幕，其次英文，最後任何可用字幕
                subtitles = info.get('subtitles', {})
                automatic_captions = info.get('automatic_captions', {})

                subtitle_data = self._get_best_subtitles(subtitles, automatic_captions)

                if subtitle_data:
                    self.subtitle_content = subtitle_data['text']
                    self.text_display.insert(1.0, self.subtitle_content)
                    self.copy_btn.config(state=tk.NORMAL)
                    self.save_btn.config(state=tk.NORMAL)
                    self.set_status(f"成功提取字幕 ({subtitle_data['language']})", "green")
                else:
                    self.set_status("找不到字幕", "red")
                    messagebox.showinfo("提示", "此影片沒有可用的字幕")

        except Exception as e:
            self.set_status(f"錯誤: {str(e)}", "red")
            messagebox.showerror("提取失敗", f"提取字幕時發生錯誤:\n{str(e)}")

        finally:
            self.extract_btn.config(state=tk.NORMAL)

    def _get_best_subtitles(self, subtitles, automatic_captions):
        """獲取最合適的字幕"""
        # 語言優先順序
        preferred_languages = ['zh-TW', 'zh-CN', 'zh', 'en', 'en-US']

        # 先檢查手動字幕
        for lang in preferred_languages:
            if lang in subtitles:
                return self._fetch_subtitle_content(subtitles[lang], lang)

        # 再檢查自動生成的字幕
        for lang in preferred_languages:
            if lang in automatic_captions:
                return self._fetch_subtitle_content(automatic_captions[lang], lang + " (自動生成)")

        # 如果沒有偏好的語言，使用第一個可用的
        if subtitles:
            lang = list(subtitles.keys())[0]
            return self._fetch_subtitle_content(subtitles[lang], lang)

        if automatic_captions:
            lang = list(automatic_captions.keys())[0]
            return self._fetch_subtitle_content(automatic_captions[lang], lang + " (自動生成)")

        return None

    def _fetch_subtitle_content(self, subtitle_list, language):
        """從字幕列表中提取文本內容"""
        try:
            if not subtitle_list:
                return None

            # 如果是 JSON 格式的字幕
            if subtitle_list[0]['ext'] == 'json3':
                import requests
                response = requests.get(subtitle_list[0]['url'])
                data = response.json()
                text = ""
                for event in data.get('events', []):
                    if 'segs' in event:
                        for seg in event['segs']:
                            text += seg.get('utf8', '')
                return {'text': text, 'language': language}

            # VTT 或 SRT 格式
            else:
                import requests
                response = requests.get(subtitle_list[0]['url'])
                content = response.text
                # 簡單處理：移除時間戳和序號
                lines = content.split('\n')
                subtitle_text = []
                for line in lines:
                    # 跳過空行、時間戳和序號
                    if line.strip() and '-->' not in line and not line.isdigit():
                        subtitle_text.append(line.strip())

                return {'text': '\n'.join(subtitle_text), 'language': language}

        except Exception as e:
            print(f"Error fetching subtitle: {e}")
            return None

    def copy_to_clipboard(self):
        """複製字幕內容到剪貼板"""
        if self.subtitle_content:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.subtitle_content)
            messagebox.showinfo("成功", "字幕已複製到剪貼板")

    def save_to_file(self):
        """將字幕保存為 TXT 文件"""
        if not self.subtitle_content:
            messagebox.showwarning("警告", "沒有字幕內容可保存")
            return

        try:
            # 從 URL 提取影片 ID 作為文件名
            url = self.url_entry.get()
            import re
            video_id_match = re.search(r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^\&\?\/\s]{11})', url)
            video_id = video_id_match.group(1) if video_id_match else "subtitles"

            filename = f"{video_id}_subtitles.txt"
            filepath = f"/Users/jessiekuo/Desktop/Forfun/{filename}"

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.subtitle_content)

            messagebox.showinfo("成功", f"字幕已保存到:\n{filepath}")

        except Exception as e:
            messagebox.showerror("保存失敗", f"保存文件時發生錯誤:\n{str(e)}")


def main():
    root = tk.Tk()
    app = YouTubeSubtitleExtractor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
