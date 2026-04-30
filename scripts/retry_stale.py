#!/usr/bin/env python3
"""重试 stale 页面 CLI（后台批量用，不依赖前端）。

用法:
  python scripts/retry_stale.py --list           # 只列出 stale 页面，不动
  python scripts/retry_stale.py --all            # 重试全部 stale (默认成功后删原 stale 页)
  python scripts/retry_stale.py --all --keep     # 重试全部，但不删原 stale 页
  python scripts/retry_stale.py --slug a b c     # 只重试指定的 stale 页面（路径 wiki/notes/x.md）
  python scripts/retry_stale.py --all --limit 10 # 最多重试 10 个，便于试跑

退出码:
  0 全部成功（或没有 stale）
  1 部分仍 stale
  2 致命错误
"""
import argparse
import os
import sys
from pathlib import Path

# 让脚本能直接 import 项目模块
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from mjq_logging import setup_logging  # noqa: E402

setup_logging()

from ingest_service import find_stale_notes, retry_stale_notes  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="重试 wiki/notes/ 下 status: 待精炼 的 fallback 页面")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="只列出 stale 页面")
    group.add_argument("--all", action="store_true", help="重试全部 stale")
    group.add_argument("--slug", nargs="+", help="重试指定 wiki/notes/...md 路径")
    parser.add_argument("--keep", action="store_true", help="重试成功后不删原 stale 页")
    parser.add_argument("--limit", type=int, help="最多重试 N 个（试跑用）")
    args = parser.parse_args(argv)

    project = str(PROJECT_DIR)
    stale = find_stale_notes(project)

    if args.list:
        print(f"Stale 页面总数: {len(stale)}")
        for s in stale:
            mark = "OK " if s["source_exists"] else "??"
            print(f"  [{mark}] {s['stale_path']}")
            print(f"        source_file: {s['source_file']}")
        return 0

    if args.slug:
        wanted = set(args.slug)
        targets = [s["stale_path"] for s in stale if s["stale_path"] in wanted]
        missing = wanted - set(targets)
        if missing:
            print(f"未找到（不是 stale 或路径错）：{sorted(missing)}", file=sys.stderr)
        if not targets:
            print("没有可重试项", file=sys.stderr)
            return 1
        stale_paths = targets
    else:
        stale_paths = [s["stale_path"] for s in stale]

    if args.limit:
        stale_paths = stale_paths[: args.limit]

    if not stale_paths:
        print("无 stale 页面，直接退出。")
        return 0

    print(f"将重试 {len(stale_paths)} 个 stale 页面 (delete={'否' if args.keep else '是'})")
    result = retry_stale_notes(
        project,
        stale_paths=stale_paths,
        delete_on_success=not args.keep,
    )
    print()
    print("=== 结果 ===")
    print(f"  batch_id     = {result['batch_id']}")
    print(f"  总数         = {result['total']}")
    print(f"  真成功       = {result['succeeded']}  (生成正常 wiki 页)")
    print(f"  仍 stale     = {result['still_stale']}  (LLM 又一次失败)")
    print(f"  已删原 stale = {len(result['deleted_stale'])}")
    print(f"  源丢失跳过   = {len(result['skipped_no_source'])}")

    if result["still_stale"] > 0:
        print()
        print("提示：仍 stale 的页面通常是 LLM 配置问题。看 data/llm_calls.jsonl 最新几行：")
        print("  PowerShell> Get-Content data/llm_calls.jsonl -Tail 5")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
