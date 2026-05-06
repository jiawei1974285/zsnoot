#!/usr/bin/env python3
"""
LLM 客户端 - 调用 DashScope / OpenAI 兼容 API
"""
import os
import json
import time
import requests
from typing import List, Dict, Optional

from mjq_logging import get_logger, log_llm_call

logger = get_logger(__name__)
LAST_LLM_ERROR = None

# 从 .env 文件读取配置
def load_env_file(path):
    """加载 .env 文件"""
    env_vars = {}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, val = line.split('=', 1)
                    env_vars[key.strip()] = val.strip()
    return env_vars

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def current_env():
    """Reload .env on each call so config changes take effect without restart."""
    workspace_env = load_env_file(os.path.join(PROJECT_DIR, '.env'))
    return {**os.environ, **workspace_env}

def load_yaml_config():
    try:
        from config_store import load_config
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'config.yaml')
        return load_config(config_path)
    except Exception:
        return {}


def resolve_env_value(value: str) -> str:
    import re
    if not isinstance(value, str):
        return ''
    match = re.fullmatch(r'\$\{([^}]+)\}', value.strip())
    if match:
        return current_env().get(match.group(1), '')
    return value


def normalize_base_url(base_url: str) -> str:
    base_url = (base_url or '').rstrip('/')
    if not base_url:
        return 'https://coding.dashscope.aliyuncs.com/v1'
    if base_url.endswith('/v1'):
        return base_url
    # Common OpenAI-compatible providers, including DeepSeek, expose /v1.
    if 'dashscope' in base_url or 'deepseek' in base_url or base_url.endswith(':11434'):
        return f'{base_url}/v1'
    return base_url


MODEL_ENV_FIELDS = {
    'llm': {
        'api_key': 'LLM_API_KEY',
        'base_url': 'LLM_BASE_URL',
        'model': 'LLM_MODEL',
        'provider': 'LLM_PROVIDER',
    },
    'vision_model': {
        'api_key': 'VISION_MODEL_API_KEY',
        'base_url': 'VISION_MODEL_BASE_URL',
        'model': 'VISION_MODEL_MODEL',
        'provider': 'VISION_MODEL_PROVIDER',
    },
    'ocr_model': {
        'api_key': 'OCR_MODEL_API_KEY',
        'base_url': 'OCR_MODEL_BASE_URL',
        'model': 'OCR_MODEL_MODEL',
        'provider': 'OCR_MODEL_PROVIDER',
    },
}


def current_llm_config(role: str = 'llm'):
    all_yaml = load_yaml_config()
    env = current_env()
    yaml_config = all_yaml.get(role, {}) or {}
    fallback = all_yaml.get('llm', {}) or {}
    fields = MODEL_ENV_FIELDS.get(role, MODEL_ENV_FIELDS['llm'])
    base_url = (
        env.get(fields['base_url'])
        or yaml_config.get('base_url')
        or env.get('LLM_BASE_URL')
        or fallback.get('base_url')
        or 'https://coding.dashscope.aliyuncs.com/v1'
    )
    api_key = (
        env.get(fields['api_key'])
        or yaml_config.get('api_key')
        or env.get('LLM_API_KEY')
        or env.get('BAILIAN_API_KEY')
        or fallback.get('api_key')
        or ''
    )
    model = env.get(fields['model']) or yaml_config.get('model') or fallback.get('model') or 'qwen3.5-plus'
    provider = (env.get(fields['provider']) or yaml_config.get('provider') or fallback.get('provider') or '').lower()
    # 深度思考 thinking：DeepSeek V4 / Reasoner 等模型支持。开启后请求体加：
    #   reasoning_effort: "high" | "medium" | "low"
    #   thinking: {"type": "enabled"}
    # 角色级 thinking 缺省时，不会从 fallback(llm) 继承——视觉/OCR 模型默认与文本模型独立
    thinking = bool(yaml_config.get('thinking', False))
    reasoning_effort = str(yaml_config.get('reasoning_effort') or 'high').lower()
    if reasoning_effort not in {'low', 'medium', 'high'}:
        reasoning_effort = 'high'
    return {
        'provider': provider,
        'base_url': normalize_base_url(base_url),
        'api_key': resolve_env_value(api_key),
        'model': model,
        'thinking': thinking,
        'reasoning_effort': reasoning_effort,
    }


def _apply_thinking(payload: Dict, config: Dict) -> Dict:
    """thinking 开启时，往 payload 注入 DeepSeek 风格的 reasoning 字段。

    样例（用户提供）：
        reasoning_effort="high"
        extra_body={"thinking": {"type": "enabled"}}
    OpenAI SDK 的 extra_body 只是把内层键合并到顶层，所以原生 HTTP 直接放顶层即可。
    其他厂商（Anthropic / Qwen）的 thinking 形状不同，需要时再单独适配。
    """
    if not config.get('thinking'):
        return payload
    payload['reasoning_effort'] = config.get('reasoning_effort', 'high')
    payload['thinking'] = {'type': 'enabled'}
    return payload


def _prompt_chars(messages: List[Dict]) -> int:
    return sum(len(m.get('content', '') or '') for m in messages)


def chat_completion(messages: List[Dict], temperature: float = 0.1, max_tokens: int = 4000, role: str = 'llm') -> Optional[str]:
    """调用 LLM 完成对话。

    返回 LLM 文本；失败返回 None。
    每次调用都写一行结构化日志到 data/llm_calls.jsonl，便于离线分析耗时与失败原因。
    """
    global LAST_LLM_ERROR
    LAST_LLM_ERROR = None
    config = current_llm_config(role)
    is_ollama = config.get('provider') == 'ollama' or config['base_url'].startswith('http://localhost:11434') or config['base_url'].startswith('http://127.0.0.1:11434')
    prompt_chars = _prompt_chars(messages)

    if not config['api_key'] and not is_ollama:
        logger.warning("LLM_API_KEY 未配置，跳过 LLM 调用 (role=%s)", role)
        LAST_LLM_ERROR = 'no_api_key'
        log_llm_call(role, config['model'], config['base_url'], 0, 'skipped',
                     prompt_chars=prompt_chars, error='no_api_key')
        return None

    headers = {'Content-Type': 'application/json'}
    if config['api_key']:
        headers['Authorization'] = f"Bearer {config['api_key']}"

    payload = {
        'model': config['model'],
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
    }
    _apply_thinking(payload, config)

    t0 = time.time()
    try:
        response = requests.post(
            f"{config['base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
        latency_ms = int((time.time() - t0) * 1000)

        # 记录非 2xx 时的响应体，方便排查 (rate limit / model not found / auth 等)
        if not response.ok:
            body = response.text[:500] if response.text else ''
            err = f"HTTP {response.status_code}: {body}"
            logger.error("LLM 调用失败 role=%s model=%s latency=%dms %s",
                         role, config['model'], latency_ms, err)
            LAST_LLM_ERROR = err
            log_llm_call(role, config['model'], config['base_url'], latency_ms, 'error',
                         prompt_chars=prompt_chars, error=err,
                         extra={'status_code': response.status_code})
            return None

        data = response.json()
        text = data['choices'][0]['message']['content']
        usage = data.get('usage') or {}
        log_llm_call(role, config['model'], config['base_url'], latency_ms, 'ok',
                     prompt_chars=prompt_chars, response_chars=len(text or ''),
                     extra={'usage': usage} if usage else None)
        logger.info("LLM ok role=%s model=%s latency=%dms in=%d out=%d",
                    role, config['model'], latency_ms, prompt_chars, len(text or ''))
        return text
    except requests.Timeout as exc:
        latency_ms = int((time.time() - t0) * 1000)
        logger.error("LLM 调用超时 role=%s model=%s latency=%dms", role, config['model'], latency_ms)
        LAST_LLM_ERROR = f'timeout: {exc}'
        log_llm_call(role, config['model'], config['base_url'], latency_ms, 'timeout',
                     prompt_chars=prompt_chars, error=str(exc))
        return None
    except Exception as exc:
        latency_ms = int((time.time() - t0) * 1000)
        logger.exception("LLM 调用异常 role=%s model=%s latency=%dms", role, config['model'], latency_ms)
        LAST_LLM_ERROR = f"{type(exc).__name__}: {exc}"
        log_llm_call(role, config['model'], config['base_url'], latency_ms, 'error',
                     prompt_chars=prompt_chars, error=f"{type(exc).__name__}: {exc}")
        return None


def last_llm_error() -> Optional[str]:
    return LAST_LLM_ERROR


def vision_extract_text(image_path: str, *, role: str = 'ocr_model',
                        prompt: str = None, timeout: int = 60) -> Optional[str]:
    """用视觉 LLM 提取图片中的文字（OpenAI 兼容多模态格式）。

    优先用 ocr_model；未配置（无 model 或无 api_key）时退回 vision_model；
    都没配置则返回 None，由调用方决定下一步（如降级到 Tesseract）。

    适配：OpenAI / DashScope (Qwen-VL) / DeepSeek（不支持视觉时会报错，由上层 catch）。
    返回纯文字，不含解释；空字符串视作失败。
    """
    import base64, mimetypes

    # 角色降级：ocr_model 没配 → 试 vision_model
    candidates = [role] if role else []
    if 'vision_model' not in candidates:
        candidates.append('vision_model')

    config = None
    chosen_role = None
    for r in candidates:
        cfg = current_llm_config(r)
        if cfg.get('model') and cfg.get('api_key'):
            config = cfg
            chosen_role = r
            break
    if not config:
        logger.info("vision_extract_text: 未配置 ocr_model / vision_model，跳过视觉 OCR")
        return None

    try:
        with open(image_path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('ascii')
        mime = mimetypes.guess_type(image_path)[0] or 'image/png'
        data_url = f"data:{mime};base64,{b64}"
    except Exception as exc:
        logger.warning("vision_extract_text: 图片读取失败 path=%s err=%s", image_path, exc)
        return None

    user_prompt = prompt or (
        '请提取图片中所有可见文字，按原文顺序输出，不要加任何解释、标题或 Markdown 格式。'
        '如果图片不包含文字，请只回复"无文字"。'
    )

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {config['api_key']}",
    }
    payload = {
        'model': config['model'],
        'messages': [{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': user_prompt},
                {'type': 'image_url', 'image_url': {'url': data_url}},
            ],
        }],
        'temperature': 0.0,
        'max_tokens': 4000,
    }

    t0 = time.time()
    prompt_chars = len(user_prompt) + len(b64)
    try:
        response = requests.post(
            f"{config['base_url']}/chat/completions",
            headers=headers, json=payload, timeout=timeout,
        )
        latency_ms = int((time.time() - t0) * 1000)
        if not response.ok:
            err = f"HTTP {response.status_code}: {response.text[:300]}"
            logger.error("vision OCR 失败 role=%s model=%s %s", chosen_role, config['model'], err)
            log_llm_call(chosen_role, config['model'], config['base_url'], latency_ms, 'error',
                         prompt_chars=prompt_chars, error=err)
            return None
        data = response.json()
        text = data['choices'][0]['message']['content'] or ''
        logger.info("vision OCR ok role=%s model=%s latency=%dms out=%d",
                    chosen_role, config['model'], latency_ms, len(text))
        log_llm_call(chosen_role, config['model'], config['base_url'], latency_ms, 'ok',
                     prompt_chars=prompt_chars, response_chars=len(text))
        cleaned = text.strip()
        if cleaned in {'无文字', '无文字。', ''}:
            return ''
        return cleaned
    except Exception as exc:
        latency_ms = int((time.time() - t0) * 1000)
        logger.exception("vision OCR 异常 role=%s model=%s", chosen_role, config['model'])
        log_llm_call(chosen_role, config['model'], config['base_url'], latency_ms, 'error',
                     prompt_chars=prompt_chars, error=f"{type(exc).__name__}: {exc}")
        return None


def stream_chat(messages: List[Dict], temperature: float = 0.1, max_tokens: int = 4000, role: str = 'llm'):
    """流式调用 LLM（生成器）"""
    config = current_llm_config(role)
    is_ollama = config.get('provider') == 'ollama' or config['base_url'].startswith('http://localhost:11434') or config['base_url'].startswith('http://127.0.0.1:11434')
    if not config['api_key'] and not is_ollama:
        logger.warning("LLM_API_KEY 未配置 (stream, role=%s)", role)
        return
    
    headers = {
        'Content-Type': 'application/json',
    }
    if config['api_key']:
        headers['Authorization'] = f"Bearer {config['api_key']}"
    
    payload = {
        'model': config['model'],
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'stream': True
    }
    _apply_thinking(payload, config)
    
    try:
        response = requests.post(
            f"{config['base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
            stream=True
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    if data_str == '[DONE]':
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data['choices'][0].get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
    except Exception as exc:
        logger.exception("LLM 流式调用失败 role=%s", role)
