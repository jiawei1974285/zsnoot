#!/usr/bin/env python3
"""
文件监控服务 - 自动扫描 inbox 文件夹，触发 LLM 分析
"""
import os
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileHandler(FileSystemEventHandler):
    """文件变化处理器"""
    
    def __init__(self, on_file_created: Callable = None):
        self.on_file_created = on_file_created
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        logger.info(f"📁 新文件：{file_path}")
        
        if self.on_file_created:
            self.on_file_created(file_path)


def start_watcher(inbox_dir: str, on_file_created: Callable = None, interval: int = 1):
    """
    启动文件监控
    
    Args:
        inbox_dir: 监控目录
        on_file_created: 文件创建回调
        interval: 检查间隔（秒）
    """
    os.makedirs(inbox_dir, exist_ok=True)
    
    event_handler = FileHandler(on_file_created)
    observer = Observer()
    observer.schedule(event_handler, inbox_dir, recursive=False)
    observer.start()
    
    logger.info(f"👁️ 开始监控：{inbox_dir}")
    
    try:
        while True:
            time.sleep(interval)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()


if __name__ == '__main__':
    import sys
    
    def on_file(file_path):
        print(f"收到文件：{file_path}")
        # 这里会调用 LLM 分析
    
    inbox = sys.argv[1] if len(sys.argv) > 1 else 'raw/inbox'
    start_watcher(inbox, on_file)
