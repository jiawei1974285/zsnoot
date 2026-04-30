#!/usr/bin/env python3
"""
Hermes 集成模块 - 通过 Hermes 命令查询知识库
"""
import os
import json
import subprocess
from typing import Dict, List, Optional

# Hermes 配置
HERMES_CONFIG = os.environ.get('HERMES_CONFIG', '/root/.hermes/config.yaml')


class HermesClient:
    """Hermes API 客户端"""
    
    def __init__(self):
        self.config_path = HERMES_CONFIG
    
    def query_knowledge_base(self, query: str) -> Dict:
        """查询知识库"""
        # 通过 Hermes 终端工具执行查询
        cmd = f'python3 /root/.openclaw/workspace/projects/mjq-handynotes/app.py --query "{query}"'
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {
                    'status': 'success',
                    'result': result.stdout
                }
            else:
                return {
                    'status': 'error',
                    'error': result.stderr
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def add_document(self, file_path: str) -> Dict:
        """添加文档到知识库"""
        cmd = f'python3 /root/.openclaw/workspace/projects/mjq-handynotes/auto_ingest.py "{file_path}"'
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return {
                    'status': 'success',
                    'result': result.stdout
                }
            else:
                return {
                    'status': 'error',
                    'error': result.stderr
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def list_documents(self) -> List[Dict]:
        """列出所有文档"""
        cmd = 'python3 -c "from app import get_wiki_pages; import json; print(json.dumps(get_wiki_pages(), ensure_ascii=False))"'
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return []
        except Exception as e:
            print(f"❌ 列出文档失败：{e}")
            return []


# 全局实例
hermes = HermesClient()


if __name__ == '__main__':
    print("=== Hermes 集成测试 ===\n")
    
    # 测试查询
    result = hermes.query_knowledge_base('盗窃案')
    print(f"✅ 查询结果：{result['status']}")
    print(f"   {result.get('result', '')[:200]}")
    
    # 测试列出文档
    docs = hermes.list_documents()
    print(f"\n✅ 文档数量：{len(docs)}")
    for doc in docs[:5]:
        print(f"  - {doc.get('title', 'Unknown')}")
