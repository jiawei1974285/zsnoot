#!/usr/bin/env python3
"""P1-P5 全链路冒烟测试。

跑法：python tests/test_full_e2e.py

不依赖 pytest；任何断言失败 → 抛 SystemExit('FAIL: ...')。
临时数据全用 tempfile，结束自动清。
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time

# 让脚本能 import 项目根模块
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main():
    print("=" * 60)
    print("知枢 P1-P5 全链路冒烟测试")
    print("=" * 60)

    test_home = tempfile.mkdtemp(prefix="mjq_full_")
    os.environ["MJQ_USER_HOME"] = test_home
    print(f"临时 home: {test_home}")

    # 清现场
    for p in [
        os.path.join(_ROOT, "cloud/data"),
        os.path.join(_ROOT, "data/machine_binding.json"),
        os.path.join(_ROOT, "data/scheduled_tasks.json"),
        os.path.join(_ROOT, "data/schema_binding.json"),
        os.path.join(_ROOT, "config/schema.yaml"),
    ]:
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.isfile(p):
            os.remove(p)

    # 启动云端
    from cloud.main import create_app
    cloud_app = create_app()
    import werkzeug.serving as ws
    threading.Thread(
        target=ws.run_simple,
        args=("127.0.0.1", 5091, cloud_app),
        kwargs={"use_reloader": False, "use_debugger": False, "threaded": True},
        daemon=True,
    ).start()
    time.sleep(0.7)
    os.environ["MJQ_CLOUD_URL"] = "http://127.0.0.1:5091"

    import requests

    def ok(label, cond, *info):
        mark = "PASS" if cond else "FAIL"
        print(f"  [{mark}] {label}", *info)
        if not cond:
            raise SystemExit(f"FAIL: {label}")

    # ═══════ P1 ═══════
    print("\n-- P1: 进程边界 + JWT --")
    r = requests.get("http://127.0.0.1:5091/api/cloud/health")
    ok("cloud health", r.status_code == 200 and r.json()["phase"] == "P5")
    ok(
        "5 templates listed",
        set(r.json()["templates"]) == {"business", "general", "legal", "police", "research"},
    )

    r = requests.post(
        "http://127.0.0.1:5091/api/cloud/auth/setup",
        json={
            "username": "admin",
            "password": "pass1234",
            "unit": "X",
            "title": "Y",
            "template_key": "police",
        },
    )
    ok("admin setup", r.status_code == 200)
    admin_tok = r.json()["access_token"]
    admin_refresh = r.json()["refresh_token"]

    r = requests.post(
        "http://127.0.0.1:5091/api/cloud/auth/refresh",
        json={"refresh_token": admin_refresh},
    )
    ok("refresh access", r.status_code == 200 and "access_token" in r.json())

    r = requests.post(
        "http://127.0.0.1:5091/api/cloud/admin/invites",
        headers={"Authorization": f"Bearer {admin_tok}"},
        json={},
    )
    ok("invite create", r.status_code == 200)
    invite = r.json()["code"]

    # ═══════ P2-A ═══════
    print("\n-- P2-A: 注册时选模板 --")
    r = requests.post(
        "http://127.0.0.1:5091/api/cloud/auth/register",
        json={
            "invite_code": invite,
            "username": "alice",
            "password": "pass1234",
            "unit": "L",
            "title": "P",
            "template_key": "research",
        },
    )
    ok("alice register w/ research", r.status_code == 200 and r.json()["template_key"] == "research")
    alice_tok = r.json()["access_token"]

    r = requests.get(
        "http://127.0.0.1:5091/api/cloud/schema/me",
        headers={"Authorization": f"Bearer {alice_tok}"},
    )
    ok("schema/me returns research", r.json()["schema"]["key"] == "research")

    r = requests.post(
        "http://127.0.0.1:5091/api/cloud/admin/invites",
        headers={"Authorization": f"Bearer {admin_tok}"},
        json={},
    )
    inv2 = r.json()["code"]
    r = requests.post(
        "http://127.0.0.1:5091/api/cloud/auth/register",
        json={
            "invite_code": inv2,
            "username": "mallory",
            "password": "pass1234",
            "unit": "X",
            "title": "Y",
            "template_key": "../../etc/passwd",
        },
    )
    ok("reject malicious template_key", r.status_code == 400)

    # ═══════ P2-B ═══════
    print("\n-- P2-B: 数据目录隔离 + 绑定闸门 --")
    import app as app_mod
    local = app_mod.app.test_client()
    r = local.get("/api/wiki/pages", headers={"Authorization": f"Bearer {alice_tok}"})
    ok(
        "unbound + JWT to 412",
        r.status_code == 412 and r.get_json()["error"] == "agent_not_bound",
    )

    from user_data import bind_machine_to
    bind_machine_to("alice")
    del sys.modules["app"]
    import app as app_mod
    local = app_mod.app.test_client()
    ok(
        "PROJECT_DIR redirected",
        app_mod.PROJECT_DIR == os.path.join(test_home, "alice"),
    )

    r = local.get("/api/wiki/pages", headers={"Authorization": f"Bearer {alice_tok}"})
    ok("bound alice + alice JWT", r.status_code == 200)

    r = requests.post(
        "http://127.0.0.1:5091/api/cloud/admin/invites",
        headers={"Authorization": f"Bearer {admin_tok}"},
        json={},
    )
    inv3 = r.json()["code"]
    r = requests.post(
        "http://127.0.0.1:5091/api/cloud/auth/register",
        json={
            "invite_code": inv3,
            "username": "bob",
            "password": "pass1234",
            "unit": "X",
            "title": "Y",
            "template_key": "general",
        },
    )
    bob_tok = r.json()["access_token"]

    r = local.get("/api/wiki/pages", headers={"Authorization": f"Bearer {bob_tok}"})
    ok(
        "bob JWT on alice machine to 403",
        r.status_code == 403 and r.get_json()["error"] == "wrong_user",
    )

    schema_path = os.path.join(test_home, "alice", "config", "schema.yaml")
    ok("schema.yaml in alice dir", os.path.exists(schema_path))
    ok("install dir clean", not os.path.exists(os.path.join(_ROOT, "config", "schema.yaml")))

    # ═══════ P3 ═══════
    print("\n-- P3: Schema 合成 + 孤立补齐 --")
    r = requests.post(
        "http://127.0.0.1:5091/api/cloud/schema/synthesize",
        headers={"Authorization": f"Bearer {alice_tok}"},
        json={"goal": "Reading", "objects": ["book", "author", "concept"]},
    )
    synth = r.json()
    ok("synth returns schema", "schema" in synth and synth["source"] in ("llm", "mock"))
    ok(
        "synth includes notes/outputs",
        "notes" in synth["schema"]["wiki_dirs"] and "outputs" in synth["schema"]["wiki_dirs"],
    )

    r = requests.post(
        "http://127.0.0.1:5091/api/cloud/schema/apply-custom",
        headers={"Authorization": f"Bearer {alice_tok}"},
        json={"schema": synth["schema"]},
    )
    ok("apply-custom", r.status_code == 200)

    r = requests.get(
        "http://127.0.0.1:5091/api/cloud/schema/me",
        headers={"Authorization": f"Bearer {alice_tok}"},
    )
    ok("schema/me prefers custom", r.json()["source"] == "custom")

    alice_wiki = os.path.join(test_home, "alice", "wiki")
    notes = os.path.join(alice_wiki, "notes")
    os.makedirs(notes, exist_ok=True)
    with open(os.path.join(notes, "note-a.md"), "w", encoding="utf-8") as f:
        f.write("---\ntype: note\ntitle: A\n---\n\nRefs [[ghost]] and [[note-b]].")
    with open(os.path.join(notes, "note-b.md"), "w", encoding="utf-8") as f:
        f.write("---\ntype: note\ntitle: B\n---\n\nIsolated")

    r = local.get("/api/orphans/scan", headers={"Authorization": f"Bearer {alice_tok}"})
    scan = r.get_json()
    ok("orphan scan finds dangling", any(d["target_slug"] == "ghost" for d in scan["dangling"]))
    ok("orphan scan finds orphan note-a", any(o["slug"] == "note-a" for o in scan["orphans"]))

    r = local.post(
        "/api/orphans/dangling/auto-fill",
        headers={"Authorization": f"Bearer {alice_tok}", "Content-Type": "application/json"},
        data=json.dumps({"use_llm": False}),
    )
    ok(
        "auto-fill creates placeholder",
        os.path.exists(os.path.join(notes, "ghost.md")),
    )

    # ═══════ P4 ═══════
    print("\n-- P4: 文档预览 + 定时任务 --")
    raw_dir = os.path.join(test_home, "alice", "raw", "sources")
    os.makedirs(raw_dir, exist_ok=True)
    with open(os.path.join(raw_dir, "doc.txt"), "w", encoding="utf-8") as f:
        f.write("Hello world")

    r = local.get(
        "/api/source/preview?path=sources/doc.txt&format=text",
        headers={"Authorization": f"Bearer {alice_tok}"},
    )
    ok("preview text", r.get_json().get("text", "").startswith("Hello"))

    r = local.get(
        "/api/source/preview?path=../../../etc/passwd&format=info",
        headers={"Authorization": f"Bearer {alice_tok}"},
    )
    ok("preview path traversal blocked", r.status_code == 400)

    r = local.get(
        "/api/source/raw?path=sources/doc.txt",
        headers={"Authorization": f"Bearer {alice_tok}"},
    )
    ok("raw stream", r.status_code == 200 and b"Hello world" in r.data)

    r = local.post(
        "/api/schedule/tasks",
        headers={"Authorization": f"Bearer {alice_tok}", "Content-Type": "application/json"},
        data=json.dumps(
            {"kind": "wiki_lint", "schedule": {"type": "cron", "value": "0 2 * * *"}}
        ),
    )
    ok("create scheduled task", r.status_code == 200)
    task_id = r.get_json()["id"]

    r = local.post(
        f"/api/schedule/tasks/{task_id}/run-now",
        headers={"Authorization": f"Bearer {alice_tok}"},
    )
    ok("run-now last_status=ok", r.get_json()["last_status"] == "ok")

    r = local.post(
        "/api/schedule/tasks",
        headers={"Authorization": f"Bearer {alice_tok}", "Content-Type": "application/json"},
        data=json.dumps(
            {"kind": "rm_rf_universe", "schedule": {"type": "interval", "value": 1}}
        ),
    )
    ok("reject unknown task kind", r.status_code == 400)

    # ═══════ P5 ═══════
    print("\n-- P5: 心跳 + admin 控制台 --")
    r = local.get("/api/health")
    ok(
        "local /api/health public",
        r.status_code == 200 and r.get_json()["bound_user"] == "alice",
    )

    import heartbeat
    ok("heartbeat send", heartbeat.send_once(app_mod.PROJECT_DIR, "alice", alice_tok))

    r = requests.get(
        "http://127.0.0.1:5091/api/cloud/admin/users",
        headers={"Authorization": f"Bearer {admin_tok}"},
    )
    users = r.json()["users"]
    alice_row = next(u for u in users if u["username"] == "alice")
    ok("admin sees alice heartbeat", alice_row["last_heartbeat_at"] is not None)
    ok("admin sees alice agent_version", alice_row["agent_version"] == "0.5.0")

    r = requests.get(
        "http://127.0.0.1:5091/api/cloud/admin/users",
        headers={"Authorization": f"Bearer {bob_tok}"},
    )
    ok("non-admin to 403", r.status_code == 403)

    r = requests.post(
        "http://127.0.0.1:5091/api/cloud/agent/heartbeat",
        headers={"Authorization": f"Bearer {bob_tok}"},
        json={"username": "alice"},
    )
    ok("cross-user heartbeat to 403", r.status_code == 403)

    # ═══════ 收尾 ═══════
    print()
    print("=" * 60)
    print("全链路冒烟测试通过")
    print("=" * 60)

    # Cleanup
    shutil.rmtree(test_home, ignore_errors=True)
    for p in [
        os.path.join(_ROOT, "data/machine_binding.json"),
        os.path.join(_ROOT, "data/scheduled_tasks.json"),
        os.path.join(_ROOT, "data/schema_binding.json"),
        os.path.join(_ROOT, "cloud/data"),
    ]:
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.isfile(p):
            os.remove(p)


if __name__ == "__main__":
    main()
