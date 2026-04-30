#!/usr/bin/env python3
"""
OpenClaw 集成模块 - 通过 OpenClaw API 访问知识库
"""
import os
import json
import requests
from typing import Dict, List, Optional

# OpenClaw 配置
OPENCLAW_GATEWAY = os.environ.get('OPENCLAW_GATEWAY', 'http://127.0.0.1:18789')
OPENCLAW_TOKEN = os.environ.get('OPENCLAW_TOKEN', '')


class OpenClawClient:
    """OpenClaw API 客户端"""
    
    def __init__(self, gateway: str = None, token: str = None):
        self.gateway = gateway or OPENCLAW_GATEWAY
        self.token = token or OPENCLAW_TOKEN
        self.headers = {
            'Content-Type': 'application/json',
        }
        if self.token:
            self.headers['Authorization'] = f'Bearer {self.token}'
    
    def get(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """GET 请求"""
        url = f'{self.gateway}{endpoint}'
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ OpenClaw GET {endpoint} 失败：{e}")
            return None
    
    def post(self, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """POST 请求"""
        url = f'{self.gateway}{endpoint}'
        try:
            response = requests.post(url, headers=self.headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ OpenClaw POST {endpoint} 失败：{e}")
            return None
    
    def list_agents(self) -> List[Dict]:
        """列出所有 Agent"""
        return self.get('/api/agents') or []
    
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """获取 Agent 信息"""
        return self.get(f'/api/agents/{agent_id}')
    
    def create_task(self, agent_id: str, task: Dict) -> Optional[Dict]:
        """创建任务"""
        return self.post(f'/api/agents/{agent_id}/tasks', task)
    
    def get_task_result(self, task_id: str) -> Optional[Dict]:
        """获取任务结果"""
        return self.get(f'/api/tasks/{task_id}')


# 全局实例
openclaw = OpenClawClient()


if __name__ == '__main__':
    print("=== OpenClaw 集成测试 ===\n")
    
    # 测试连接
    agents = openclaw.list_agents()
    print(f"✅ Agent 数量：{len(agents)}")
    for agent in agents:
        print(f"  - {agent.get('name', 'Unknown')}")
