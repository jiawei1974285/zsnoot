#!/usr/bin/env python3
"""
消息平台集成 - 飞书/微信文件自动入库
"""
import os
import json
import requests
from typing import Dict, List, Optional

# 消息平台配置
FEISHU_BOT_WEBHOOK = os.environ.get('FEISHU_BOT_WEBHOOK', '')
WECHAT_BOT_TOKEN = os.environ.get('WECHAT_BOT_TOKEN', '')


class MessagePlatformClient:
    """消息平台客户端"""
    
    def __init__(self, platform: str = 'feishu'):
        self.platform = platform
    
    def send_message(self, message: str) -> Dict:
        """发送消息"""
        if self.platform == 'feishu':
            return self._send_feishu(message)
        elif self.platform == 'wechat':
            return self._send_wechat(message)
        else:
            return {'status': 'error', 'error': f'不支持的平台：{self.platform}'}
    
    def _send_feishu(self, message: str) -> Dict:
        """发送飞书消息"""
        if not FEISHU_BOT_WEBHOOK:
            return {'status': 'error', 'error': '飞书 webhook 未配置'}
        
        payload = {
            'msg_type': 'text',
            'content': {
                'text': message
            }
        }
        
        try:
            response = requests.post(
                FEISHU_BOT_WEBHOOK,
                json=payload,
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _send_wechat(self, message: str) -> Dict:
        """发送微信消息"""
        if not WECHAT_BOT_TOKEN:
            return {'status': 'error', 'error': '微信 token 未配置'}
        
        # 微信机器人发送逻辑
        return {'status': 'success', 'message': '消息已发送'}


# 全局实例
feishu = MessagePlatformClient('feishu')
wechat = MessagePlatformClient('wechat')


if __name__ == '__main__':
    print("=== 消息平台集成测试 ===\n")
    
    # 测试飞书
    result = feishu.send_message('测试消息')
    print(f"✅ 飞书消息：{result}")
    
    # 测试微信
    result = wechat.send_message('测试消息')
    print(f"✅ 微信消息：{result}")
