"""mjq-handynotes 云端控制面。

P1 阶段职责（按计划文件 1-2-whimsical-waffle.md）：
  - 用户认证 / 邀请码注册（复用根目录 auth.py 的逻辑，仅切换 project_dir）
  - 颁发短期 JWT 给浏览器，让浏览器拿着 token 直连本机 agent
  - 不接触任何用户语料（wiki / raw / data 文件夹都在本机）

P2+ 才会加：模板分发、Schema 合成、心跳、admin 控制台。
"""
