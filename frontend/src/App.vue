<template>
  <div v-if="authState === 'loading'" class="auth-screen">
    <div class="auth-loading">正在加载…</div>
  </div>

  <div v-else-if="authState === 'setup' || authState === 'login'" class="auth-screen auth-hero-screen">
    <div class="auth-window-controls" aria-hidden="true">
      <span></span>
      <span></span>
      <span></span>
    </div>

    <section class="auth-hero-copy">
      <div class="auth-brand-lockup">
        <img class="auth-company-logo" src="/shuhe-logo.png" alt="数合云智" />
        <div>
          <div class="auth-product-name">知枢</div>
          <div class="auth-product-subtitle">本地知识中枢</div>
        </div>
      </div>

      <h1>让知识在本地<br />有序<span>沉淀与连接</span></h1>
      <p class="auth-hero-subtitle">轻量级本地知识组织与连接工作台</p>
      <div class="auth-feature-row">
        <span><el-icon><CircleCheck /></el-icon>本地优先</span>
        <i></i>
        <span><el-icon><Key /></el-icon>安全可控</span>
        <i></i>
        <span><el-icon><Connection /></el-icon>轻量高效</span>
        <i></i>
        <span><el-icon><Collection /></el-icon>灵活扩展</span>
      </div>

      <div class="auth-knowledge-scene" aria-hidden="true">
        <div class="auth-orbit orbit-one"></div>
        <div class="auth-orbit orbit-two"></div>
        <div class="auth-cube-main"><Collection /></div>
        <div class="auth-cube-card card-doc"><Document /></div>
        <div class="auth-cube-card card-link"><Connection /></div>
        <div class="auth-cube-card card-search"><Search /></div>
        <div class="auth-cube-shield"><Key /></div>
      </div>

      <div class="auth-footer-line">
        <span>© 2026 数合云智 版权所有</span>
        <i></i>
        <span>版本：v1.0.0</span>
        <i></i>
        <span>本地运行</span>
      </div>
    </section>

    <div class="auth-card auth-login-panel">
      <div class="auth-card-header">
        <h1 class="auth-title">
          {{ authState === 'setup' ? '初始化知枢' : (authMode === 'register' ? '注册账号' : '欢迎登录知枢') }}
        </h1>
        <p class="auth-subtitle">
          <template v-if="authState === 'setup'">创建管理员账号，开启本地知识中枢</template>
          <template v-else-if="authMode === 'register'">凭管理员发放的邀请码注册新账号</template>
          <template v-else>登录本地知识中枢，开启您的知识之旅</template>
        </p>
      </div>

      <template v-if="authState === 'setup'">
        <el-form class="auth-form" label-position="top" @submit.prevent="submitSetup">
          <el-form-item>
            <el-input v-model="setupForm.username" :prefix-icon="User" placeholder="请输入管理员用户名" autocomplete="username" size="large" />
          </el-form-item>
          <el-form-item>
            <el-input v-model="setupForm.password" :prefix-icon="Key" type="password" show-password placeholder="请输入密码（至少 6 位）" autocomplete="new-password" size="large" />
          </el-form-item>
          <el-form-item>
            <el-input v-model="setupForm.password_confirm" :prefix-icon="Key" type="password" show-password placeholder="请再次输入密码" autocomplete="new-password" size="large" @keyup.enter="submitSetup" />
          </el-form-item>
          <div class="auth-setup-mode">
            <el-radio-group v-model="setupForm.raw_mode">
              <el-radio value="default">默认 raw/ 目录</el-radio>
              <el-radio value="custom">自定义路径</el-radio>
            </el-radio-group>
            <el-input
              v-if="setupForm.raw_mode === 'custom'"
              v-model="setupForm.raw_dir"
              placeholder="例如 D:\mjq-raw"
              size="large"
            />
          </div>
          <el-button type="primary" size="large" :loading="authSubmitting" class="auth-primary-button" @click="submitSetup">
            创建并登录
          </el-button>
        </el-form>
      </template>

      <template v-else>
        <div class="auth-tabs">
          <button type="button" :class="{ active: authMode === 'login' }" @click="authMode = 'login'">账号登录</button>
          <button type="button" :class="{ active: authMode === 'register' }" @click="authMode = 'register'">注册</button>
        </div>

        <el-form v-if="authMode === 'login'" class="auth-form" label-position="top" @submit.prevent="submitLogin">
          <el-form-item>
            <el-input v-model="loginForm.username" :prefix-icon="User" placeholder="请输入用户名" autocomplete="username" size="large" />
          </el-form-item>
          <el-form-item>
            <el-input v-model="loginForm.password" :prefix-icon="Key" type="password" show-password placeholder="请输入密码" autocomplete="current-password" size="large" @keyup.enter="submitLogin" />
          </el-form-item>
          <div class="auth-options">
            <el-checkbox v-model="loginRemember">记住我</el-checkbox>
            <button type="button" @click="forgotPassword">忘记密码?</button>
          </div>
          <el-button type="primary" size="large" :loading="authSubmitting" class="auth-primary-button" @click="submitLogin">
            登录
          </el-button>
        </el-form>

        <el-form v-else class="auth-form" label-position="top" @submit.prevent="submitRegister">
          <el-form-item>
            <el-input v-model="registerForm.invite_code" :prefix-icon="Key" placeholder="邀请码（向管理员索取）" size="large" maxlength="12" />
          </el-form-item>
          <el-form-item>
            <el-input v-model="registerForm.username" :prefix-icon="User" placeholder="用户名" autocomplete="username" size="large" />
          </el-form-item>
          <el-form-item>
            <el-input v-model="registerForm.password" :prefix-icon="Key" type="password" show-password placeholder="密码（至少 6 位）" autocomplete="new-password" size="large" />
          </el-form-item>
          <el-form-item>
            <el-input v-model="registerForm.password_confirm" :prefix-icon="Key" type="password" show-password placeholder="再次输入密码" autocomplete="new-password" size="large" />
          </el-form-item>
          <el-form-item>
            <el-input v-model="registerForm.unit" placeholder="单位（必填，如：朝阳分局网安大队）" size="large" />
          </el-form-item>
          <el-form-item>
            <el-input v-model="registerForm.title" placeholder="职务（必填，如：民警 / 队长）" size="large" />
          </el-form-item>
          <el-form-item>
            <el-input v-model="registerForm.email" placeholder="邮箱（选填）" size="large" @keyup.enter="submitRegister" />
          </el-form-item>
          <el-form-item v-if="schemaTemplates.length">
            <div class="schema-template-picker">
              <div class="schema-template-label">选择适合你工作场景的 Schema 模板</div>
              <div class="schema-template-grid">
                <button
                  v-for="tpl in schemaTemplates"
                  :key="tpl.key"
                  type="button"
                  class="schema-template-card"
                  :class="{ active: registerForm.template_key === tpl.key }"
                  @click="registerForm.template_key = tpl.key"
                >
                  <div class="schema-template-card-title">{{ tpl.label }}</div>
                  <div class="schema-template-card-desc">{{ tpl.description }}</div>
                  <div class="schema-template-card-meta">
                    {{ tpl.category_count }} 类目 · {{ tpl.type_count }} 节点类型
                  </div>
                </button>
              </div>
            </div>
          </el-form-item>
          <el-button type="primary" size="large" :loading="authSubmitting" class="auth-primary-button" @click="submitRegister">
            注册并登录
          </el-button>
        </el-form>

        <div v-if="authMode === 'login'" class="auth-divider"><span>或</span></div>
        <button v-if="authMode === 'login'" type="button" class="auth-local-button" @click="localModeLogin">
          <el-icon><Box /></el-icon>
          使用本机账户登录
        </button>

        <a v-if="SPLIT_MODE_ENABLED" href="/downloads/zsnoot-agent-v1.0.0.zip" class="auth-download-button" download>
          <el-icon><Download /></el-icon>
          <span>
            <strong>下载本机客户端</strong>
            <small>解压后双击 setup.bat，按提示输入用户名即可</small>
          </span>
        </a>
      </template>

      <div class="auth-card-footer">
        <button type="button" @click="openLoginSettings"><el-icon><Setting /></el-icon>系统设置</button>
        <i></i>
        <button type="button">简体中文⌄</button>
      </div>
    </div>
  </div>

  <div v-else class="app-shell">
    <main class="main-layout">
      <aside class="side-rail">
        <div class="brand">
          <img class="brand-mark" src="/logo.png" alt="数合云智" />
          <div>
            <div class="brand-title">知枢</div>
            <div class="brand-subtitle">本地知识库工作台 · 数合云智</div>
          </div>
        </div>

        <nav class="rail-nav" aria-label="主导航">
          <div
            v-for="item in navItems"
            :key="item.key"
            class="rail-nav-group"
          >
            <button
              class="rail-button"
              :class="{ active: activeView === item.key, 'has-tree': item.key === 'knowledge' }"
              @click="handleNavItemClick(item)"
            >
              <el-icon><component :is="item.icon" /></el-icon>
              <span class="rail-label">{{ item.label }}</span>
              <span
                v-if="item.key === 'knowledge'"
                class="rail-collapse-icon"
                :class="{ expanded: knowledgeTreeExpanded }"
              >
                <el-icon><ArrowRight /></el-icon>
              </span>
            </button>
            <div v-if="item.key === 'knowledge' && knowledgeTreeExpanded" class="rail-tree">
              <button
                v-for="group in knowledgeFolders"
                :key="group.type"
                class="rail-tree-item"
                @click="jumpToKnowledge(group.type)"
              >
                <el-icon><Document /></el-icon>
                <span>{{ group.label }}</span>
                <strong>{{ group.count }}</strong>
              </button>
              <button class="rail-tree-item rail-tree-add" @click="addCustomCategory">
                <el-icon><Plus /></el-icon>
                <span>新建分类</span>
              </button>
            </div>
          </div>
        </nav>

        <div class="rail-spacer"></div>

        <button class="rail-button rail-maintenance-button" @click="openMaintenance">
          <el-icon><Tools /></el-icon>
          <span class="rail-label">知识维护</span>
        </button>

        <div class="rail-user-card">
          <div class="connection-line">
            <span class="chip-dot"></span>
            本地知识库已连接
          </div>
          <div class="rail-user-main">
            <div class="avatar-badge">
              <el-icon><User /></el-icon>
            </div>
            <div>
              <strong>{{ currentUser || '未登录' }}</strong>
              <span>{{ currentAffiliation || '未填写单位 / 职务' }}</span>
            </div>
          </div>
          <button class="logout-button" @click="logoutUser">
            <el-icon><SwitchButton /></el-icon>
            退出登录
          </button>
        </div>
      </aside>

      <section class="workspace-shell">
        <header class="topbar">
          <div></div>
          <div class="topbar-status">
            <div class="status-pill agent-status-pill" :class="agentStatusClass" :title="agentStatusLabel">
              <span class="status-label">智能体</span>
              <strong>{{ agentStatusLabel }}</strong>
            </div>
            <div class="status-pill">
              <span class="status-label">知识页</span>
              <strong>{{ stats.pages }}</strong>
            </div>
            <div class="status-pill">
              <span class="status-label">批次</span>
              <strong>{{ batches.length }}</strong>
            </div>
            <div class="status-pill">
              <span class="status-label">模型</span>
              <strong>{{ modelName }}</strong>
            </div>
          </div>
        </header>
        <div class="workspace-header workspace-header-compact">
          <div class="workspace-tools">
            <div class="workspace-chip">
              <span class="chip-dot"></span>
              本地知识库已连接
            </div>
          </div>
        </div>

        <section class="content-surface">
          <!-- 门户模式首页：仅展示"开始使用本机客户端"引导 -->
          <template v-if="activeView === 'home' && IS_PORTAL_MODE">
            <div class="portal-home">
              <div class="portal-hero">
                <div class="portal-hero-icon">🚀</div>
                <h1>欢迎回来，{{ currentUser }}</h1>
                <p class="portal-hero-sub">
                  {{ currentProfile.unit ? `${currentProfile.unit} · ${currentProfile.title}` : '账号已就绪' }}
                </p>
              </div>

              <div class="portal-tip">
                <strong>这里是"账号门户"，不是工作区。</strong>
                你的所有数据都在本机；要上传材料、做对话、看图谱，请打开本机客户端：
              </div>

              <div class="portal-actions">
                <a class="portal-action portal-action-primary" href="http://localhost:5004" target="_blank">
                  <div class="portal-action-icon">💻</div>
                  <div class="portal-action-body">
                    <strong>打开本机客户端</strong>
                    <small>http://localhost:5004 — 必须先双击桌面"知枢"图标启动 agent</small>
                  </div>
                </a>

                <a class="portal-action" href="/downloads/zsnoot-agent-v1.0.0.zip" download>
                  <div class="portal-action-icon">📦</div>
                  <div class="portal-action-body">
                    <strong>下载本机客户端</strong>
                    <small>首次使用 / 换机器 / 重装 — 解压后双击 setup.bat</small>
                  </div>
                </a>

                <a class="portal-action" v-if="currentRole === 'admin'" @click="setActiveView('config')">
                  <div class="portal-action-icon">👥</div>
                  <div class="portal-action-body">
                    <strong>管理员控制台</strong>
                    <small>邀请码 · 用户列表 · 心跳监控</small>
                  </div>
                </a>
              </div>

              <div class="portal-footer-tip">
                <small>
                  下次使用建议：双击桌面"知枢"图标 → 浏览器会自动开 localhost:5004，不需要回这个门户页。
                </small>
              </div>
            </div>
          </template>

          <!-- 正常模式首页（本机 agent 服务的 SPA） -->
          <template v-else-if="activeView === 'home'">
            <!-- ── 页头 ── -->
            <div class="home-page-header">
              <div>
                <div class="section-title">首页</div>
                <div class="section-caption">{{ homeGreeting }}，{{ currentUser || '警官' }} · 知识库动态一览</div>
              </div>
              <div class="home-header-actions">
                <div v-if="staleCount > 0" class="home-stale-badge" @click="setActiveView('ingest')">
                  ⚠ {{ staleCount }} 个页面待精炼
                </div>
                <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
              </div>
            </div>

            <div class="home-body-grid">
              <!-- ══ 左列 ══ -->
              <div class="home-left-col">

                <!-- 快捷操作 -->
                <div class="home-action-grid">
                  <button class="home-action-card primary" @click="setActiveView('ingest')">
                    <div class="home-action-icon blue">📥</div>
                    <strong>入库材料</strong>
                    <span>上传文件，LLM 自动整理</span>
                  </button>
                  <button class="home-action-card" @click="openNoteDialog">
                    <div class="home-action-icon green">✏️</div>
                    <strong>新建笔记</strong>
                    <span>随手记，系统自动结构化</span>
                  </button>
                  <button class="home-action-card" @click="setActiveView('chat')">
                    <div class="home-action-icon purple">💬</div>
                    <strong>对话查询</strong>
                    <span>自然语言检索知识库</span>
                  </button>
                  <button class="home-action-card" @click="setActiveView('graph')">
                    <div class="home-action-icon amber">🕸️</div>
                    <strong>知识图谱</strong>
                    <span>查看实体关联网络</span>
                  </button>
                </div>

                <!-- KPI 六格 -->
                <div class="home-kpi-grid">
                  <!-- 入库文件 -->
                  <div class="home-kpi-card">
                    <div class="home-kpi-header">
                      <span class="home-kpi-label">入库文件</span>
                      <span v-if="weekDelta.ingest > 0" class="home-kpi-delta up">+{{ weekDelta.ingest }}</span>
                      <span v-else-if="weekDelta.ingest < 0" class="home-kpi-delta down">{{ weekDelta.ingest }}</span>
                    </div>
                    <div class="home-kpi-value">{{ homeStats.ingested_files || 0 }}</div>
                    <div class="home-kpi-sub">{{ homeStats.batches || 0 }} 个批次</div>
                    <svg class="home-kpi-spark" viewBox="0 0 120 28" preserveAspectRatio="none">
                      <polyline :points="sparkPoints(homeStats.daily_activity, 'ingest')" fill="none" stroke="#3b82f6" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                  </div>
                  <!-- 知识卡片 -->
                  <div class="home-kpi-card">
                    <div class="home-kpi-header">
                      <span class="home-kpi-label">知识卡片</span>
                    </div>
                    <div class="home-kpi-value">{{ homeStats.pages || 0 }}</div>
                    <div class="home-kpi-sub">
                      <template v-for="(n, t, idx) in homeStats.by_type" :key="t">
                        <span v-if="idx < 3">{{ typeLabel(t) }} {{ n }}<span v-if="idx < 2"> · </span></span>
                      </template>
                    </div>
                    <svg class="home-kpi-spark" viewBox="0 0 120 28" preserveAspectRatio="none">
                      <polyline :points="sparkPoints(homeStats.daily_activity, 'create_page')" fill="none" stroke="#3b82f6" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                  </div>
                  <!-- 实体总数 -->
                  <div class="home-kpi-card">
                    <div class="home-kpi-header">
                      <span class="home-kpi-label">实体总数</span>
                    </div>
                    <div class="home-kpi-value">{{ entityTotal }}</div>
                    <div class="home-kpi-sub">分布在 {{ Object.keys(homeStats.by_type || {}).length }} 类目录</div>
                    <svg class="home-kpi-spark" viewBox="0 0 120 28" preserveAspectRatio="none">
                      <polyline :points="sparkPoints(homeStats.daily_activity, 'edit_page')" fill="none" stroke="#3b82f6" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                  </div>
                  <!-- 今日对话 -->
                  <div class="home-kpi-card">
                    <div class="home-kpi-header">
                      <span class="home-kpi-label">今日对话</span>
                      <span v-if="weekDelta.chat > 0" class="home-kpi-delta up">+{{ weekDelta.chat }}</span>
                      <span v-else-if="weekDelta.chat < 0" class="home-kpi-delta down">{{ weekDelta.chat }}</span>
                    </div>
                    <div class="home-kpi-value">{{ homeStats.today?.chat || 0 }}</div>
                    <div class="home-kpi-sub">本周共 {{ homeStats.this_week?.chat || 0 }} 次</div>
                    <svg class="home-kpi-spark" viewBox="0 0 120 28" preserveAspectRatio="none">
                      <polyline :points="sparkPoints(homeStats.daily_activity, 'chat')" fill="none" stroke="#3b82f6" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                  </div>
                  <!-- 待精炼 -->
                  <div class="home-kpi-card" :class="{ 'home-kpi-alert': staleCount > 0 }">
                    <div class="home-kpi-header">
                      <span class="home-kpi-label">待精炼页面</span>
                      <span v-if="staleCount > 0" class="home-kpi-delta warn">需处理</span>
                    </div>
                    <div class="home-kpi-value" :class="{ 'kpi-val-alert': staleCount > 0 }">{{ staleCount }}</div>
                    <div class="home-kpi-sub">解析不完整，需重跑</div>
                    <svg class="home-kpi-spark" viewBox="0 0 120 28" preserveAspectRatio="none">
                      <line x1="0" y1="20" x2="120" y2="20" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="4 4"/>
                    </svg>
                  </div>
                  <!-- 健康度（点开跳到体检页） -->
                  <button class="home-kpi-card home-kpi-health home-kpi-clickable" @click="setActiveView('lint')" :title="lint.summary?.formula || '点击查看详情'">
                    <div class="home-kpi-header">
                      <span class="home-kpi-label">知识库健康度</span>
                      <span class="home-kpi-delta up">{{ lintHealthScore }}%</span>
                    </div>
                    <div class="home-kpi-value kpi-val-health">{{ lintHealthScore }}%</div>
                    <div class="home-kpi-sub">
                      断链 {{ lint.broken_links?.length || 0 }} · 孤立 {{ lint.orphan_pages?.length || 0 }} · 过期 {{ lint.stale_pages?.length || 0 }} · 占位 {{ lint.placeholder_pages?.length || 0 }}
                    </div>
                    <div class="home-health-bar-wrap">
                      <div class="home-health-bar" :style="{ width: lintHealthScore + '%' }"></div>
                    </div>
                  </button>
                </div>

                <!-- Activity Feed -->
                <div class="home-feed-panel">
                  <div class="home-feed-header">
                    <span class="home-feed-title">近期动态</span>
                  </div>
                  <div class="home-feed-list">
                    <button
                      v-for="item in homeFeedItems"
                      :key="item.id"
                      class="home-feed-item"
                      @click="item.onClick && item.onClick()"
                    >
                      <div class="home-feed-ico" :class="item.icoClass">{{ item.ico }}</div>
                      <div class="home-feed-body">
                        <div class="home-feed-name">{{ item.title }}</div>
                        <div class="home-feed-meta">{{ item.meta }}</div>
                      </div>
                      <div class="home-feed-time">{{ item.time }}</div>
                    </button>
                    <div v-if="!homeFeedItems.length" class="detail-item">暂无近期动态</div>
                  </div>
                </div>
              </div>

              <!-- ══ 右列 ══ -->
              <div class="home-right-col">
                <div class="home-cal-label">对话日历 <span>点击日期查看记录</span></div>

                <!-- 月历 -->
                <div class="home-cal-panel">
                  <div class="home-cal-header">
                    <span class="home-cal-month">{{ calMonthLabel }}</span>
                    <div class="home-cal-nav">
                      <button class="home-cal-nav-btn" @click="calPrevMonth">‹</button>
                      <button class="home-cal-nav-btn" @click="calNextMonth">›</button>
                    </div>
                  </div>
                  <div class="home-cal-grid">
                    <div class="home-cal-weekdays">
                      <span v-for="w in ['一','二','三','四','五','六','日']" :key="w" class="home-cal-wd">{{ w }}</span>
                    </div>
                    <div class="home-cal-days">
                      <div
                        v-for="(cell, idx) in calCells"
                        :key="idx"
                        class="home-cal-day"
                        :class="[
                          cell.day ? '' : 'empty',
                          cell.isToday ? 'today' : '',
                          cell.isSelected ? 'selected' : '',
                          cell.chatCount > 0 ? 'level-' + cell.level : '',
                        ]"
                        @click="cell.day && selectCalDay(cell)"
                      >
                        <span v-if="cell.day" class="home-cal-day-num">{{ cell.day }}</span>
                        <span v-if="cell.chatCount > 0" class="home-cal-dot"></span>
                      </div>
                    </div>
                  </div>
                  <div class="home-cal-legend">
                    <span>对话次数：</span>
                    <div class="home-cal-legend-items">
                      <span>少</span>
                      <div v-for="c in ['#dbeafe','#bfdbfe','#93c5fd','#60a5fa']" :key="c" class="home-cal-legend-box" :style="{ background: c }"></div>
                      <span>多</span>
                    </div>
                  </div>
                </div>

                <!-- 健康度详情 -->
                <div class="home-health-card">
                  <div class="home-feed-title" style="margin-bottom:10px">知识库健康度</div>
                  <button v-for="h in healthItems" :key="h.label" class="home-health-row home-health-row-clickable"
                    @click="goLintCategory(h.category)" :title="`点击处理 ${h.count} 项`">
                    <span class="home-health-label">{{ h.label }}</span>
                    <div class="home-health-bar-wrap" style="flex:1">
                      <div class="home-health-bar" :style="{ width: h.val + '%', background: h.color }"></div>
                    </div>
                    <span class="home-health-val">{{ h.count }}</span>
                  </button>
                  <button class="home-health-link" @click="setActiveView('lint')">前往体检 →</button>
                </div>
              </div>
            </div>

            <!-- 日历抽屉 -->
            <div v-if="calDrawerOpen" class="home-cal-drawer-overlay" @click.self="calDrawerOpen = false">
              <div class="home-cal-drawer">
                <div class="home-cal-drawer-header">
                  <div>
                    <div class="home-cal-drawer-title">对话记录</div>
                    <div class="home-cal-drawer-date">{{ calDrawerDateLabel }} · {{ calDrawerQA.length }} 条</div>
                  </div>
                  <button class="home-cal-drawer-close" @click="calDrawerOpen = false">✕</button>
                </div>
                <div class="home-cal-drawer-body">
                  <div v-if="!calDrawerQA.length" class="home-cal-drawer-empty">
                    <div style="font-size:32px;opacity:.4">💬</div>
                    <span>当日暂无对话记录</span>
                  </div>
                  <button
                    v-for="qa in calDrawerQA"
                    :key="qa.slug"
                    class="home-qa-item"
                    @click="openQAFromHome(qa); calDrawerOpen = false"
                  >
                    <div class="home-qa-q">
                      <span class="home-qa-q-icon">Q</span>
                      {{ qa.title }}
                    </div>
                    <div class="home-qa-snippet">{{ qa.snippet || '（无摘要）' }}</div>
                    <div class="home-qa-meta">
                      <span class="home-qa-tag">问答记忆</span>
                      <span>{{ qa.created }}</span>
                    </div>
                  </button>
                </div>
              </div>
            </div>
          </template>


          <template v-else-if="activeView === 'ingest'">
            <div class="section-header">
              <div>
                <div class="section-title">材料入库</div>
                <div class="section-caption">把文件丢进来，系统会自动解析、整理和建立关联线索。</div>
              </div>
              <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
            </div>

            <div class="workbench-grid ingest-workbench">
              <div class="upload-panel">
                <div class="panel-topline">
                  <span class="panel-badge">RAW</span>
                  <span class="panel-hint">支持 Word、PDF、Markdown、Excel、图片和文本</span>
                </div>
                <el-upload
                  drag
                  multiple
                  :auto-upload="false"
                  :file-list="fileList"
                  :show-file-list="false"
                  :on-change="handleFileChange"
                  :on-remove="handleFileRemove"
                >
                  <div class="upload-drop">
                    <el-icon class="upload-icon"><UploadFilled /></el-icon>
                    <div class="upload-text">拖入材料或点击选择</div>
                    <div class="upload-hint">上传后自动归档原始材料，并编译到知识库</div>
                  </div>
                </el-upload>

                <div v-if="fileList.length" class="upload-queue">
                  <div class="upload-queue-head">
                    <div>
                      <strong>待入库文件</strong>
                      <span>{{ fileList.length }} 个文件 · {{ uploadTotalSize }}</span>
                    </div>
                    <div class="upload-queue-actions">
                      <button
                        v-if="fileList.length > uploadPreviewLimit"
                        type="button"
                        @click="uploadFilesExpanded = !uploadFilesExpanded"
                      >
                        {{ uploadFilesExpanded ? '收起' : `展开全部 ${fileList.length}` }}
                      </button>
                      <button type="button" @click="clearQueuedFiles">清空</button>
                    </div>
                  </div>
                  <div class="upload-file-grid">
                    <div
                      v-for="item in visibleUploadFiles"
                      :key="item.uid || item.name"
                      class="upload-file-row"
                    >
                      <el-icon><Document /></el-icon>
                      <span class="upload-file-name">{{ item.name }}</span>
                      <span class="upload-file-size">{{ formatFileSize(item.size || item.raw?.size || 0) }}</span>
                      <button type="button" class="upload-file-remove" @click="removeQueuedFile(item)">
                        ×
                      </button>
                    </div>
                    <button
                      v-if="uploadHiddenCount > 0"
                      type="button"
                      class="upload-file-more"
                      @click="uploadFilesExpanded = true"
                    >
                      还有 {{ uploadHiddenCount }} 个文件已自动折叠，点击展开
                    </button>
                  </div>
                </div>

                <el-button
                  type="primary"
                  size="large"
                  :loading="uploading"
                  :disabled="!fileList.length"
                  style="width: 100%; margin-top: 14px"
                  @click="uploadFiles"
                >
                  开始入库
                </el-button>

                <div v-if="currentBatch" class="steps-card">
                  <el-steps :active="currentStep" finish-status="success" direction="vertical">
                    <el-step title="保存原始材料" />
                    <el-step title="解析正文内容" />
                    <el-step title="生成知识页面" />
                    <el-step title="建立关联线索" />
                    <el-step title="写入本地检索" />
                  </el-steps>
                </div>
              </div>

              <section class="batch-table-card">
                <div class="batch-table-head">
                  <div>
                    <strong>最近添加批次</strong>
                    <el-tag round>{{ batches.length }} 个批次</el-tag>
                  </div>
                  <div class="batch-table-actions">
                    <el-button size="small">全部批次</el-button>
                    <el-button size="small" :icon="Delete" :disabled="!selectedBatchIds.length" :loading="deletingBatches" @click="deleteSelectedBatches">
                      删除所选
                    </el-button>
                    <el-button size="small" type="danger" plain :disabled="!batches.length" :loading="deletingBatches" @click="deleteAllBatches">
                      一键清空
                    </el-button>
                  </div>
                </div>
                <div class="batch-table">
                  <div class="batch-table-row batch-table-row-head">
                    <span>
                      <el-checkbox
                        :model-value="allPagedBatchesSelected"
                        :indeterminate="selectedBatchIds.length > 0 && !allPagedBatchesSelected"
                        @change="togglePagedBatchSelection"
                      />
                    </span>
                    <span>批次名称</span>
                    <span>材料数量</span>
                    <span>知识页</span>
                    <span>更新时间</span>
                    <span>状态</span>
                    <span>操作</span>
                  </div>
                  <button
                    v-for="batch in pagedBatches"
                    :key="batch.id"
                    class="batch-table-row"
                    @click="openBatch(batch.id)"
                  >
                    <span @click.stop>
                      <el-checkbox
                        :model-value="selectedBatchSet.has(batch.id)"
                        @change="toggleBatchSelection(batch.id)"
                      />
                    </span>
                    <span class="batch-title-cell">
                      <i class="batch-status-dot" :class="statusType(batch.status)"></i>
                      <span>
                        <strong>{{ summarizeBatchTitle(batch) }}</strong>
                        <small>批次ID：{{ batch.id }}</small>
                      </span>
                    </span>
                    <span>{{ batch.original_files?.length || batch.file_names?.length || 0 }} 份</span>
                    <span>{{ batch.generated_files?.length || 0 }} 页</span>
                    <span>{{ formatTime(batch.updated_at || batch.created_at) }}</span>
                    <span>
                      <el-tag size="small" :type="batchStatusType(batch)">
                        {{ batchStatusLabel(batch) }}
                      </el-tag>
                    </span>
                    <span class="row-actions">
                      <el-button size="small" :icon="FolderOpened" @click.stop="openBatchSourceFolder(batch)" />
                      <el-button size="small" :icon="View" @click.stop="openBatch(batch.id)" />
                      <el-button
                        size="small"
                        :icon="Refresh"
                        :loading="reparsingBatchSet.has(batch.id)"
                        @click.stop="reparseBatch(batch)"
                      >再次解析</el-button>
                      <el-button size="small" type="danger" plain :icon="Delete" :loading="deletingBatches" @click.stop="deleteBatch(batch)" />
                    </span>
                  </button>
                  <div v-if="!batches.length" class="detail-item">暂无入库批次</div>
                </div>
                <div v-if="batches.length > batchPageSize" class="batch-pagination">
                  <span>共 {{ batches.length }} 条</span>
                  <el-pagination
                    v-model:current-page="batchPage"
                    v-model:page-size="batchPageSize"
                    :page-sizes="[7, 10, 20, 50]"
                    :total="batches.length"
                    layout="sizes, prev, pager, next"
                    small
                    background
                  />
                </div>
              </section>
            </div>
          </template>

          <template v-else-if="activeView === 'chat'">
            <div class="section-header">
              <div>
                <div class="section-title">对话查询</div>
                <div class="section-caption">面向日常研判和处置问答，答案会自动回填为问答记忆。</div>
              </div>
            </div>
            <div class="chat-layout">
              <div class="chat-messages">
                <div v-for="message in messages" :key="message.id" class="message" :class="message.role">
                  <div class="message-content">{{ message.content }}</div>
                  <div v-if="message.role === 'assistant' && message.sources?.length" class="message-sources">
                    <div class="message-sources-title">知识来源</div>
                    <button
                      v-for="source in message.sources"
                      :key="`${source.type}-${source.slug}`"
                      type="button"
                      class="message-source-link"
                      @click="openChatSource(source)"
                    >
                      <span>{{ source.title }}</span>
                      <small>{{ typeLabel(source.type) }}</small>
                    </button>
                  </div>
                </div>
              </div>
              <div class="chat-toolbar">
                <div class="chat-toolbar-label">按 `Ctrl + Enter` 发送</div>
                <div class="chat-toolbar-chip">来源自动引用</div>
              </div>
              <div class="chat-input-row">
                <el-input
                  v-model="chatInput"
                  :autosize="{ minRows: 2, maxRows: 5 }"
                  type="textarea"
                  placeholder="输入要查询的案件、人员、地点、线索或法规"
                  @keydown.ctrl.enter="sendChat"
                />
                <el-button
                  class="chat-send-btn"
                  type="primary"
                  :loading="chatLoading"
                  :icon="Promotion"
                  circle
                  size="large"
                  :disabled="!chatInput.trim()"
                  @click="sendChat"
                />
              </div>
            </div>
          </template>

          <template v-else-if="activeView === 'knowledge'">
            <div class="section-header">
              <div>
                <div class="section-title">整理后的知识</div>
                <div class="section-caption">底层仍是开放的 Wiki 结构，但界面只展示对民警有用的信息。</div>
              </div>
              <div class="knowledge-toolbar">
                <el-input
                  v-model="pageSearch"
                  :prefix-icon="Search"
                  placeholder="搜索标题 / 摘要 / 标签 / slug"
                  clearable
                  style="width: 260px"
                />
                <el-select v-model="pageFilter" style="width: 160px" @change="loadPages">
                  <el-option label="全部类别" value="all" />
                  <el-option
                    v-for="item in categoryOptions"
                    :key="item.key"
                    :label="item.label"
                    :value="item.key"
                  />
                </el-select>
                <el-select v-model="pageSortBy" style="width: 150px">
                  <el-option label="最后导入" value="imported_desc" />
                  <el-option label="最早导入" value="imported_asc" />
                  <el-option label="最近更新" value="updated_desc" />
                  <el-option label="最早更新" value="updated_asc" />
                  <el-option label="最近创建" value="created_desc" />
                  <el-option label="标题 A→Z" value="title_asc" />
                </el-select>
                <div class="knowledge-count">
                  共 {{ filteredPages.length }} 条<span v-if="pageSearch && filteredPages.length !== pages.length"> / {{ pages.length }}</span>
                </div>
                <el-checkbox
                  :model-value="currentPageAllSelected"
                  :indeterminate="currentPageIndeterminate"
                  :disabled="!pagedPages.length"
                  @change="toggleSelectCurrentPage"
                >全选本页</el-checkbox>
                <span class="knowledge-count">已选 {{ selectedPageKeys.length }} 项</span>
                <el-button
                  v-if="canDeleteWikiPages"
                  size="small"
                  type="danger"
                  :disabled="!selectedPageKeys.length"
                  @click="deleteSelectedPages"
                >批量删除</el-button>
              </div>
            </div>
            <div class="page-grid">
              <div v-if="!pages.length" class="detail-item">暂无知识页面</div>
              <div v-else-if="!filteredPages.length" class="detail-item">没有匹配「{{ pageSearch }}」的页面</div>
              <article
                v-for="page in pagedPages"
                :key="`${page.type}-${page.slug}`"
                class="page-item page-item-compact clickable"
                :class="{ selected: isPageSelected(page) }"
                @click="openPagePreview(page)"
              >
                <div class="page-item-topline">
                  <el-checkbox
                    class="page-item-check"
                    :model-value="isPageSelected(page)"
                    @click.stop
                    @change="togglePageSelection(page)"
                  />
                  <el-tag size="small">{{ typeLabel(page.type) }}</el-tag>
                  <span class="page-item-path">{{ page.type }}/{{ page.slug }}</span>
                  <el-popconfirm
                    v-if="canDeleteWikiPages"
                    title="确认删除该页面?(只删 markdown 文件,索引和反向链接不会自动清理)"
                    confirm-button-text="删除"
                    cancel-button-text="取消"
                    width="260"
                    @confirm="deletePage(page)"
                  >
                    <template #reference>
                      <el-button class="page-item-delete" size="small" type="danger" link @click.stop>删除</el-button>
                    </template>
                  </el-popconfirm>
                </div>
                <div class="page-title">{{ page.title }}</div>
                <div class="page-preview">{{ page.body_preview || '暂无摘要' }}</div>
              </article>
            </div>
            <div v-if="filteredPages.length > pageSize" class="page-pagination">
              <el-pagination
                v-model:current-page="pageNumber"
                v-model:page-size="pageSize"
                :page-sizes="[12, 24, 48, 96]"
                layout="sizes, prev, pager, next, jumper"
                :total="filteredPages.length"
                background
              />
            </div>
          </template>

          <template v-else-if="activeView === 'graph'">
            <div class="section-header graph-page-header">
              <div>
                <div class="section-title">关系图谱</div>
                <div class="section-caption">通过可视化展示实体之间的关联关系，发现隐藏的线索与规律。</div>
              </div>
            </div>

            <div class="graph-summary graph-summary-compact">
              <div class="metric graph-stat-card">
                <span class="graph-stat-icon"><Connection /></span>
                <div>
                  <div class="metric-label">节点数</div>
                  <div class="metric-value">{{ graphVisibleNodes.length }}</div>
                </div>
              </div>
              <div class="metric graph-stat-card">
                <span class="graph-stat-icon"><Connection /></span>
                <div>
                  <div class="metric-label">关系数</div>
                  <div class="metric-value">{{ graphVisibleEdges.length }}</div>
                </div>
              </div>
              <div class="metric graph-stat-card">
                <span class="graph-stat-icon"><Collection /></span>
                <div>
                  <div class="metric-label">子图数</div>
                  <div class="metric-value">{{ graphVisibleCommunityCount }}</div>
                </div>
              </div>
              <div class="metric graph-stat-card">
                <span class="graph-stat-icon"><User /></span>
                <div>
                  <div class="metric-label">选中节点</div>
                  <div class="metric-value">{{ selectedNode ? 1 : 0 }}</div>
                </div>
              </div>
            </div>

            <div class="graph-panel graph-workbench">
              <div ref="graphCanvasRef" class="graph-canvas-wrap">
                <svg ref="graphSvgRef" class="graph-svg" viewBox="0 0 1400 900" role="img" aria-label="知识关系图谱"></svg>

                <div class="graph-floating-card graph-legend-card">
                  <div class="graph-card-title">图例</div>
                  <div class="legend-list">
                    <span v-for="item in graphLegend" :key="item.type" class="legend-item">
                      <i :style="{ background: item.color }"></i>{{ item.label }}
                    </span>
                  </div>
                  <div class="graph-line-legend">
                    <span><i class="line-solid"></i>直接关系</span>
                    <span><i class="line-dashed"></i>间接关系</span>
                  </div>
                </div>

                <div class="graph-floating-card graph-minimap">
                  <div class="graph-minimap-grid">
                    <i
                      v-for="node in graphVisibleNodes.slice(0, 48)"
                      :key="node.id"
                      :style="{ background: nodeColor(node.type) }"
                    ></i>
                  </div>
                  <div class="graph-minimap-window"></div>
                </div>

                <div class="graph-zoom-stack">
                  <button type="button" @click="nudgeGraphZoom(1.2)">+</button>
                  <button type="button" @click="nudgeGraphZoom(0.82)">−</button>
                  <button type="button" @click="resetGraphZoom">⌖</button>
                </div>
              </div>

              <aside class="graph-control-side">
                <div class="graph-control-panel">
                  <div class="graph-card-title">图谱控制</div>
                  <el-input
                    v-model="graphSearch"
                    :prefix-icon="Search"
                    clearable
                    placeholder="搜索实体、关键词"
                    @input="scheduleRenderGraph"
                    @clear="scheduleRenderGraph"
                  />
                  <div class="graph-control-grid">
                    <label>实体类型</label>
                    <el-select v-model="graphTypeFilter" placeholder="实体类型" @change="scheduleRenderGraph">
                      <el-option label="全部类型" value="all" />
                      <el-option
                        v-for="item in graphTypeOptions"
                        :key="item.type"
                        :label="item.label"
                        :value="item.type"
                      />
                    </el-select>
                    <label>布局方式</label>
                    <el-select v-model="graphLayout" @change="scheduleRenderGraph">
                      <el-option
                        v-for="layout in GRAPH_LAYOUTS"
                        :key="layout.value"
                        :label="layout.label"
                        :value="layout.value"
                      />
                    </el-select>
                  </div>
                  <div class="graph-control-checks">
                    <el-checkbox v-model="graphLabels" @change="scheduleRenderGraph">标签</el-checkbox>
                    <el-checkbox v-model="graphShowRelations" @change="scheduleRenderGraph">关系</el-checkbox>
                    <el-checkbox v-model="graphMerged" @change="loadGraph">聚合节点</el-checkbox>
                    <el-checkbox v-model="graphMotion" @change="scheduleRenderGraph">动态</el-checkbox>
                  </div>
                  <div class="graph-control-actions">
                    <el-button :disabled="!focusedNodeId" @click="resetFocus">重置视图</el-button>
                    <el-button @click="clearGraphFilters">清空筛选</el-button>
                    <el-button type="primary" :icon="Refresh" :loading="graphLoading" @click="loadGraph">刷新图谱</el-button>
                  </div>
                </div>
              </aside>

              <aside class="graph-side">
                <div class="graph-side-top">
                  <div class="section-title section-title-sm">节点详情</div>
                  <button type="button" class="graph-side-close" @click="selectedNode = null">×</button>
                </div>
                <template v-if="selectedNode">
                  <div class="graph-node-profile">
                    <span class="graph-node-avatar" :style="{ background: nodeColor(selectedNode.type) }">
                      <component :is="selectedNodeIcon(selectedNode.type)" />
                    </span>
                    <div>
                      <h3>{{ selectedNode.label }}</h3>
                      <el-tag size="small" effect="light">{{ typeLabel(selectedNode.type) }}</el-tag>
                    </div>
                  </div>
                  <div class="graph-detail-list">
                    <div><span>节点编号：</span><strong>{{ selectedNode.id }}</strong></div>
                    <div><span>关联数：</span><strong>{{ selectedNode.linkCount || selectedNodeRelations.length }}</strong></div>
                    <div><span>线索簇：</span><strong>{{ selectedNode.community ?? '未分组' }}</strong></div>
                    <div v-if="selectedNode.members?.length"><span>合并成员：</span><strong>{{ selectedNode.members.join('、') }}</strong></div>
                  </div>
                  <div class="graph-card-title graph-relation-title">关联关系（{{ selectedNodeRelations.length }}）</div>
                  <div class="graph-relation-tabs">
                    <button type="button" class="active">全部</button>
                    <button type="button">直接关系</button>
                    <button type="button">间接关系</button>
                  </div>
                  <div class="graph-relation-list">
                    <button
                      v-for="relation in selectedNodeRelations.slice(0, 7)"
                      :key="relation.key"
                      type="button"
                      class="graph-relation-row"
                      @click="focusNodeById(relation.node.id)"
                    >
                      <span class="relation-dot" :style="{ background: nodeColor(relation.node.type) }"></span>
                      <span>{{ relation.node.label }}</span>
                      <em>{{ relation.label }}</em>
                    </button>
                    <div v-if="!selectedNodeRelations.length" class="detail-item">暂无关联关系</div>
                  </div>
                </template>
                <div v-else class="detail-item">点击图中的节点查看详情</div>
                <div class="graph-side-actions">
                  <el-button type="primary" :disabled="!selectedNode" @click="selectedNode && openPageBySlug(selectedNode.id)">查看详情</el-button>
                  <el-button :disabled="!selectedNode" @click="resetFocus">路径分析</el-button>
                  <el-button :disabled="!selectedNode">更多操作</el-button>
                </div>
              </aside>
            </div>
          </template>

          <template v-else-if="activeView === 'config'">
            <div class="section-header">
              <div>
                <div class="section-title">系统配置</div>
                <div class="section-caption">本地模型、内网云端模型和检索参数都集中放在这里。</div>
              </div>
              <el-button-group>
                <el-button type="primary" :icon="CircleCheck" :loading="configSaving" @click="saveConfig">
                  保存配置
                </el-button>
              </el-button-group>
            </div>

            <el-form label-position="top" class="config-grid">
              <section class="config-card">
                <div class="config-card-title-row">
                  <div class="section-title section-title-sm">文本模型</div>
                  <el-button size="small" :icon="Connection" :loading="configTesting.llm" @click="testModelConnection('llm')">
                    测试连接
                  </el-button>
                </div>
                <el-form-item label="模型提供方">
                  <el-select v-model="configForm.llm.provider">
                    <el-option label="阿里百炼 / DashScope" value="dashscope" />
                    <el-option label="OpenAI 兼容接口" value="openai" />
                    <el-option label="Ollama 本地模型" value="ollama" />
                    <el-option label="自定义内网模型" value="custom" />
                  </el-select>
                </el-form-item>
                <el-form-item label="模型名称">
                  <el-input v-model="configForm.llm.model" placeholder="例如 qwen3.5-plus / qwen2.5 / local-model" />
                </el-form-item>
                <el-form-item label="接口地址">
                  <el-input v-model="configForm.llm.base_url" placeholder="例如 http://127.0.0.1:11434/v1" />
                </el-form-item>
                <el-form-item v-if="configForm.llm.provider !== 'ollama'" label="API Key 或环境变量">
                  <el-input v-model="configForm.llm.api_key" show-password placeholder="${BAILIAN_API_KEY}" />
                </el-form-item>
                <el-form-item label="深度思考 (thinking)">
                  <el-switch v-model="configForm.llm.thinking" />
                  <el-select
                    v-if="configForm.llm.thinking"
                    v-model="configForm.llm.reasoning_effort"
                    style="width: 140px; margin-left: 12px"
                  >
                    <el-option label="低" value="low" />
                    <el-option label="中" value="medium" />
                    <el-option label="高" value="high" />
                  </el-select>
                  <div class="form-help">DeepSeek V4 / Reasoner 等推理模型支持；普通模型请保持关闭</div>
                </el-form-item>
              </section>

              <section class="config-card">
                <div class="config-card-title-row">
                  <div class="section-title section-title-sm">视觉模型</div>
                  <el-button size="small" :icon="Connection" :loading="configTesting.vision_model" @click="testModelConnection('vision_model')">
                    测试连接
                  </el-button>
                </div>
                <el-form-item label="模型提供方">
                  <el-select v-model="configForm.vision_model.provider">
                    <el-option label="跟随文本模型" value="" />
                    <el-option label="阿里百炼 / DashScope" value="dashscope" />
                    <el-option label="OpenAI 兼容接口" value="openai" />
                    <el-option label="Ollama 本地模型" value="ollama" />
                    <el-option label="自定义内网模型" value="custom" />
                  </el-select>
                </el-form-item>
                <el-form-item label="模型名称">
                  <el-input v-model="configForm.vision_model.model" placeholder="例如 qwen-vl-plus / gpt-4o-mini" />
                </el-form-item>
                <el-form-item label="接口地址">
                  <el-input v-model="configForm.vision_model.base_url" placeholder="留空则跟随文本模型接口" />
                </el-form-item>
                <el-form-item v-if="configForm.vision_model.provider !== 'ollama'" label="API Key 或环境变量">
                  <el-input v-model="configForm.vision_model.api_key" show-password placeholder="${VISION_MODEL_API_KEY}" />
                </el-form-item>
                <el-form-item label="深度思考 (thinking)">
                  <el-switch v-model="configForm.vision_model.thinking" />
                  <el-select
                    v-if="configForm.vision_model.thinking"
                    v-model="configForm.vision_model.reasoning_effort"
                    style="width: 140px; margin-left: 12px"
                  >
                    <el-option label="低" value="low" />
                    <el-option label="中" value="medium" />
                    <el-option label="高" value="high" />
                  </el-select>
                </el-form-item>
              </section>

              <section class="config-card">
                <div class="config-card-title-row">
                  <div class="section-title section-title-sm">OCR 模型</div>
                  <el-button size="small" :icon="Connection" :loading="configTesting.ocr_model" @click="testModelConnection('ocr_model')">
                    测试连接
                  </el-button>
                </div>
                <el-form-item label="模型提供方">
                  <el-select v-model="configForm.ocr_model.provider">
                    <el-option label="跟随文本模型" value="" />
                    <el-option label="阿里百炼 / DashScope" value="dashscope" />
                    <el-option label="OpenAI 兼容接口" value="openai" />
                    <el-option label="Ollama 本地模型" value="ollama" />
                    <el-option label="自定义内网模型" value="custom" />
                  </el-select>
                </el-form-item>
                <el-form-item label="模型名称">
                  <el-input v-model="configForm.ocr_model.model" placeholder="例如 qwen-vl-ocr / ocr-specialist" />
                </el-form-item>
                <el-form-item label="接口地址">
                  <el-input v-model="configForm.ocr_model.base_url" placeholder="留空则跟随文本模型接口" />
                </el-form-item>
                <el-form-item v-if="configForm.ocr_model.provider !== 'ollama'" label="API Key 或环境变量">
                  <el-input v-model="configForm.ocr_model.api_key" show-password placeholder="${OCR_MODEL_API_KEY}" />
                </el-form-item>
                <el-form-item label="深度思考 (thinking)">
                  <el-switch v-model="configForm.ocr_model.thinking" />
                  <el-select
                    v-if="configForm.ocr_model.thinking"
                    v-model="configForm.ocr_model.reasoning_effort"
                    style="width: 140px; margin-left: 12px"
                  >
                    <el-option label="低" value="low" />
                    <el-option label="中" value="medium" />
                    <el-option label="高" value="high" />
                  </el-select>
                </el-form-item>
              </section>

              <section class="config-card">
                <div class="section-title section-title-sm">入库与检索</div>
                <el-form-item label="模型温度">
                  <el-slider v-model="configForm.llm.temperature" :min="0" :max="1" :step="0.1" show-input />
                </el-form-item>
                <el-form-item label="最大输出 Token">
                  <el-input-number v-model="configForm.llm.max_tokens" :min="512" :max="32000" :step="512" style="width: 100%" />
                </el-form-item>
                <el-form-item label="默认并发数">
                  <el-input-number v-model="configForm.ingest.max_workers" :min="1" :max="16" :step="1" style="width: 100%" />
                  <div class="form-help">默认 5 路并发，可按机器性能调整。</div>
                </el-form-item>
              </section>

              <section class="config-card">
                <div class="section-title section-title-sm">数据存储</div>
                <el-form-item label="原始材料目录 (raw)">
                  <el-input
                    v-model="configForm.raw_dir"
                    placeholder="留空则使用项目内 raw/。可填绝对路径,如 D:\mjq-raw 或 \\\\nas\\police\\raw"
                  />
                  <div class="form-help">改动后下次入库生效,旧批次仍指向原路径</div>
                </el-form-item>
              </section>

              <section class="config-card">
                <div class="section-title section-title-sm">知识目录</div>
                <div class="config-category-list">
                  <div
                    v-for="(category, index) in configForm.wiki.custom_categories"
                    :key="`category-${index}`"
                    class="config-category-row"
                  >
                    <el-input v-model="category.key" placeholder="目录键，例如 clues" />
                    <el-input v-model="category.label" placeholder="显示名称，例如 线索" />
                    <el-button text type="primary" :loading="configSaving" @click="confirmCustomCategory(index)">确定</el-button>
                    <el-button text type="danger" @click="removeCustomCategory(index)">删除</el-button>
                  </div>
                </div>
                <el-button text type="primary" @click="addCustomCategory">新增目录</el-button>
                <el-alert
                  title="默认目录会一直保留；这里新增的是你自己的知识分类，保存后会自动创建对应目录。"
                  type="info"
                  show-icon
                  :closable="false"
                />
              </section>

              <section class="config-card config-card-wide">
                <div class="section-title section-title-sm">智能体技能</div>
                <div class="config-category-list">
                  <div
                    v-for="(skill, index) in configForm.agent.skills"
                    :key="`skill-${index}`"
                    class="config-skill-row"
                  >
                    <el-switch v-model="skill.enabled" />
                    <el-input v-model="skill.name" placeholder="技能名称，例如 OCR预检" />
                    <el-input v-model="skill.description" placeholder="技能说明：用于识别扫描件、图片票据等" />
                    <el-input v-model="skill.trigger" placeholder="触发条件：图片/扫描PDF/正文为空" />
                    <el-button text type="danger" @click="removeSkill(index)">删除</el-button>
                  </div>
                </div>
                <el-button text type="primary" @click="addSkill">新增技能</el-button>
                <el-alert
                  title="技能会作为智能体可用能力写入提示词，由智能体自主选择；当前不会执行任意脚本。"
                  type="info"
                  show-icon
                  :closable="false"
                />
              </section>

              <section class="config-card">
                <div class="section-title section-title-sm">本地服务</div>
                <el-form-item label="监听地址">
                  <el-input v-model="configForm.server.host" />
                </el-form-item>
                <el-form-item label="端口">
                  <el-input-number v-model="configForm.server.port" :min="1000" :max="65535" style="width: 100%" />
                </el-form-item>
                <el-form-item label="原始材料目录">
                  <el-input v-model="configForm.watcher.inbox_dir" />
                </el-form-item>
                <el-alert
                  title="保存后新配置会写入 config/config.yaml；部分服务端启动参数需要重启后生效。"
                  type="info"
                  show-icon
                  :closable="false"
                />
              </section>

              <section v-if="currentRole === 'admin'" class="config-card config-card-wide">
                <div class="config-card-title-row">
                  <div class="section-title section-title-sm">用户与邀请码</div>
                  <el-button size="small" type="primary" :icon="Plus" :loading="invitesCreating" @click="openCreateInviteDialog">
                    生成邀请码
                  </el-button>
                </div>
                <el-table :data="invitesList" size="small" empty-text="还没有邀请码，点击右上角生成">
                  <el-table-column prop="code" label="邀请码" width="120">
                    <template #default="{ row }">
                      <code class="invite-code">{{ row.code }}</code>
                    </template>
                  </el-table-column>
                  <el-table-column prop="note" label="备注" min-width="160" show-overflow-tooltip />
                  <el-table-column prop="created_by" label="创建者" width="100" />
                  <el-table-column prop="created_at" label="生成时间" width="160">
                    <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
                  </el-table-column>
                  <el-table-column label="状态" width="160">
                    <template #default="{ row }">
                      <el-tag v-if="row.used_at" type="info" size="small">已被 {{ row.used_by }} 使用</el-tag>
                      <el-tag v-else type="success" size="small">未使用</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="160">
                    <template #default="{ row }">
                      <el-button size="small" link type="primary" @click="copyInvite(row.code)">复制</el-button>
                      <el-popconfirm
                        title="撤销后该邀请码失效，无法恢复。"
                        confirm-button-text="撤销"
                        cancel-button-text="取消"
                        @confirm="revokeInviteAction(row.code)"
                      >
                        <template #reference>
                          <el-button size="small" link type="danger" :disabled="!!row.used_at">撤销</el-button>
                        </template>
                      </el-popconfirm>
                    </template>
                  </el-table-column>
                </el-table>
                <el-alert
                  title="邀请码一次性使用：成员凭码注册后，码自动标为已用并保留审计痕迹。"
                  type="info"
                  show-icon
                  :closable="false"
                />
              </section>
            </el-form>

            <el-dialog v-model="createInviteDialog.open" title="生成新邀请码" width="420px">
              <el-form label-position="top">
                <el-form-item label="备注（可选，方便记录给谁）">
                  <el-input v-model="createInviteDialog.note" placeholder="例如：给小张 / 朝阳网安" maxlength="40" show-word-limit />
                </el-form-item>
              </el-form>
              <template #footer>
                <el-button @click="createInviteDialog.open = false">取消</el-button>
                <el-button type="primary" :loading="invitesCreating" @click="submitCreateInvite">生成</el-button>
              </template>
            </el-dialog>
          </template>

          <template v-else>
            <div class="section-header">
              <div>
                <div class="section-title">知识库体检</div>
                <div class="section-caption">
                  断链 · 孤立 · 过期 · 占位 —— 唯一的健康度入口
                  <span v-if="lint.summary?.health_score !== undefined" class="lint-formula" :title="lint.summary?.formula">
                    · 当前健康度 {{ lint.summary.health_score }}%
                  </span>
                </div>
              </div>
              <el-button type="primary" :loading="lintLoading" :icon="CircleCheck" @click="runLint">
                开始体检
              </el-button>
            </div>

            <!-- 4 类问题概览（始终显示，无问题就 0） -->
            <div class="lint-overview-grid">
              <div class="lint-overview-card" :class="{ active: (lint.broken_links?.length || 0) > 0 }">
                <div class="lint-overview-label">断链</div>
                <div class="lint-overview-num">{{ lint.broken_links?.length || 0 }}</div>
                <div class="lint-overview-desc">页面引用了不存在的实体</div>
                <el-button v-if="(lint.broken_links?.length || 0) > 0" size="small" type="primary" @click="openLintFix('broken_links')">处理</el-button>
                <span v-else class="lint-overview-clean">✓ 无问题</span>
              </div>
              <div class="lint-overview-card" :class="{ active: (lint.orphan_pages?.length || 0) > 0 }">
                <div class="lint-overview-label">孤立页面</div>
                <div class="lint-overview-num">{{ lint.orphan_pages?.length || 0 }}</div>
                <div class="lint-overview-desc">无人引用、自身也无外联</div>
                <el-button v-if="(lint.orphan_pages?.length || 0) > 0" size="small" type="primary" @click="openLintFix('orphan_pages')">处理</el-button>
                <span v-else class="lint-overview-clean">✓ 无问题</span>
              </div>
              <div class="lint-overview-card" :class="{ active: (lint.stale_pages?.length || 0) > 0 }">
                <div class="lint-overview-label">过期内容</div>
                <div class="lint-overview-num">{{ lint.stale_pages?.length || 0 }}</div>
                <div class="lint-overview-desc">长期未更新（>180 天）</div>
                <el-button v-if="(lint.stale_pages?.length || 0) > 0" size="small" type="primary" @click="openLintFix('stale_pages')">处理</el-button>
                <span v-else class="lint-overview-clean">✓ 无问题</span>
              </div>
              <div class="lint-overview-card" :class="{ active: (lint.placeholder_pages?.length || 0) > 0 }">
                <div class="lint-overview-label">占位页</div>
                <div class="lint-overview-num">{{ lint.placeholder_pages?.length || 0 }}</div>
                <div class="lint-overview-desc">系统自动生成、待补充</div>
                <el-button v-if="(lint.placeholder_pages?.length || 0) > 0" size="small" type="primary" @click="openLintFix('placeholder_pages')">处理</el-button>
                <span v-else class="lint-overview-clean">✓ 无问题</span>
              </div>
            </div>

            <div v-if="lint.suggestions?.length" class="lint-suggestions">
              <div v-for="(suggestion, i) in lint.suggestions" :key="i" class="lint-suggestion">{{ suggestion }}</div>
            </div>
            <div v-if="!lint.suggestions" class="detail-item">尚未运行体检，点右上角「开始体检」</div>

            <el-dialog
              v-model="lintFixDialog.open"
              :title="lintFixDialogTitle"
              width="720"
              destroy-on-close
            >
              <el-table
                ref="lintFixTableRef"
                :data="lintFixDialog.items"
                @selection-change="onLintFixSelectionChange"
                max-height="420"
              >
                <el-table-column type="selection" width="48" />
                <el-table-column v-if="lintFixDialog.category === 'broken_links'" label="源页面" prop="from" />
                <el-table-column v-if="lintFixDialog.category === 'broken_links'" label="断链目标" prop="to" />
                <el-table-column v-if="lintFixDialog.category !== 'broken_links'" label="页面" prop="title" />
                <el-table-column v-if="lintFixDialog.category !== 'broken_links'" label="slug" prop="slug" width="180" />
                <el-table-column v-if="lintFixDialog.category !== 'broken_links'" label="类型" prop="type" width="100" />
                <el-table-column v-if="lintFixDialog.category === 'stale_pages'" label="上次更新" prop="updated" width="140" />
                <el-table-column width="220">
                  <template #header>
                    <div class="lint-action-header">
                      <span>动作</span>
                      <el-select
                        v-model="lintFixBulkAction"
                        size="small"
                        placeholder="全部设为"
                        @change="applyLintFixBulkAction"
                      >
                        <el-option
                          v-for="opt in lintFixActionOptions(lintFixDialog.category)"
                          :key="opt.value"
                          :label="opt.label"
                          :value="opt.value"
                        />
                      </el-select>
                    </div>
                  </template>
                  <template #default="scope">
                    <el-select v-model="scope.row.action" size="small" @change="syncLintFixBulkAction">
                      <el-option
                        v-for="opt in lintFixActionOptions(lintFixDialog.category)"
                        :key="opt.value"
                        :label="opt.label"
                        :value="opt.value"
                      />
                    </el-select>
                  </template>
                </el-table-column>
              </el-table>
              <template #footer>
                <span style="margin-right: 12px; color: #909399; font-size: 13px">
                  已选 {{ lintFixDialog.selected.length }} / {{ lintFixDialog.items.length }}
                </span>
                <el-button @click="lintFixDialog.open = false">取消</el-button>
                <el-button type="primary" :loading="lintFixSubmitting" :disabled="!lintFixDialog.selected.length" @click="submitLintFix">
                  确认修复
                </el-button>
              </template>
            </el-dialog>
          </template>
        </section>
      </section>
    </main>

    <el-drawer v-model="batchDrawer" size="46%" title="入库结果">
      <div v-if="selectedBatch" class="detail-list">
        <div class="result-grid">
          <div class="metric">
            <div class="metric-value">{{ selectedBatch.original_files?.length || 0 }}</div>
            <div class="metric-label">原始材料</div>
          </div>
          <div class="metric">
            <div class="metric-value">{{ selectedBatch.generated_files?.length || 0 }}</div>
            <div class="metric-label">知识页面</div>
          </div>
          <div class="metric">
            <div class="metric-value">{{ selectedBatch.links?.length || 0 }}</div>
            <div class="metric-label">关联线索</div>
          </div>
        </div>

        <el-divider content-position="left">生成页面</el-divider>
        <div v-for="item in selectedBatch.generated_files || []" :key="item" class="detail-item">{{ item }}</div>
        <div v-if="!selectedBatch.generated_files?.length" class="detail-item">未生成页面</div>

        <el-divider content-position="left">提取实体</el-divider>
        <div v-for="entity in selectedBatch.entities || []" :key="`${entity.type}-${entity.name}`" class="detail-item">
          {{ entity.name }} · {{ entity.type || '实体' }} {{ entity.role ? `· ${entity.role}` : '' }}
        </div>
        <div v-if="!selectedBatch.entities?.length" class="detail-item">暂无实体</div>

        <el-divider content-position="left">处理日志</el-divider>
        <div v-for="entry in selectedBatch.log || []" :key="`${entry.time}-${entry.message}`" class="detail-item">
          {{ formatTime(entry.time) }} · {{ entry.message }}
        </div>
      </div>
    </el-drawer>

    <el-dialog v-model="noteDialog" title="新建笔记" width="720px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="noteForm.title" maxlength="80" placeholder="例如：走访记录 / 线索摘录 / 关系备注" />
        </el-form-item>
        <el-form-item label="URL">
          <el-input v-model="noteForm.url" placeholder="粘贴网页链接后点击提取">
            <template #append>
              <el-button :loading="noteUrlExtracting" :disabled="!noteForm.url.trim()" @click="extractNoteUrl">提取</el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="内容">
          <el-input
            v-model="noteForm.content"
            type="textarea"
            :autosize="{ minRows: 8, maxRows: 16 }"
            placeholder="输入笔记内容。示例：黄超和何思雨是夫妻。系统会自动抽取实体、关系并写入知识图谱。"
          />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="noteForm.tagsText" placeholder="多个标签用逗号分隔，例如：走访, 关系, 重点人员" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="noteDialog = false">取消</el-button>
        <el-button type="primary" :loading="noteSubmitting" :disabled="!noteForm.content.trim()" @click="submitCreateNote">
          创建并抽取
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="firstRunDialog"
      title="初始化设置"
      width="520"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <p style="color: #606266; margin-bottom: 14px">
        首次使用,请选择原始材料(raw)的存放位置。后续上传的所有原始文档会归档到这里。
      </p>
      <el-radio-group v-model="firstRunForm.mode" style="display: flex; flex-direction: column; gap: 12px">
        <el-radio value="default">
          <strong>使用默认</strong>
          <div style="color: #909399; font-size: 12px; margin-top: 2px">项目内 raw/(随项目一起)</div>
        </el-radio>
        <el-radio value="custom">
          <strong>自定义路径</strong>
          <div style="color: #909399; font-size: 12px; margin-top: 2px">放到 D 盘 / 网盘 / 共享目录</div>
        </el-radio>
      </el-radio-group>
      <el-input
        v-if="firstRunForm.mode === 'custom'"
        v-model="firstRunForm.custom"
        placeholder="例如 D:\mjq-raw 或 \\\\nas\\police\\raw"
        style="margin-top: 14px"
      />
      <template #footer>
        <el-button type="primary" :loading="firstRunSaving" @click="submitFirstRun">保存并开始使用</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="pageDrawer" size="52%" :title="pageEditMode ? '编辑页面' : '知识页面预览'">
      <div v-if="selectedPage" class="page-preview-drawer">
        <div class="page-preview-header">
          <el-tag>{{ typeLabel(selectedPage.type) }}</el-tag>
          <h2 v-if="!pageEditMode">{{ selectedPage.meta?.title || selectedPage.title || selectedPage.slug }}</h2>
          <p>{{ selectedPage.meta?.updated || selectedPage.meta?.created || '' }}</p>
          <div v-if="!wikiReadOnly" class="page-preview-actions">
            <template v-if="!pageEditMode">
              <el-button size="small" :icon="EditPen" @click="startEditPage">编辑</el-button>
            </template>
            <template v-else>
              <el-button size="small" @click="cancelEditPage">取消</el-button>
              <el-button size="small" type="primary" :loading="pageSaving" @click="saveEditPage">保存</el-button>
            </template>
          </div>
        </div>

        <template v-if="!pageEditMode">
          <div class="relation-strip">
            <div>
              <strong>指向实体</strong>
              <div class="relation-tags">
                <el-tag
                  v-for="link in selectedPage.outlinks || []"
                  :key="link"
                  class="relation-tag"
                  @click="openPageBySlug(link)"
                >
                  {{ link }}
                </el-tag>
                <span v-if="!selectedPage.outlinks?.length" class="muted">暂无</span>
              </div>
            </div>
            <div>
              <strong>反向关联</strong>
              <div class="relation-tags">
                <el-tag
                  v-for="link in selectedPage.backlinks || []"
                  :key="`${link.type}-${link.slug}`"
                  type="success"
                  class="relation-tag"
                  @click="openPagePreview(link)"
                >
                  {{ link.title }}
                </el-tag>
                <span v-if="!selectedPage.backlinks?.length" class="muted">暂无</span>
              </div>
            </div>
          </div>

          <article class="markdown-preview" @click="handleMarkdownClick" v-html="renderMarkdownPreview(selectedPage.body || '')"></article>
        </template>

        <template v-else>
          <div class="page-edit-form">
            <el-input v-model="pageEditDraft.title" placeholder="标题" size="large" />
            <el-input
              v-model="pageEditDraft.body"
              type="textarea"
              :autosize="{ minRows: 18, maxRows: 32 }"
              placeholder="开始撰写 Markdown 内容…&#10;&#10;支持 [[wiki-link]] 双向链接、## 标题、- 列表 等语法。"
              resize="vertical"
            />
          </div>
        </template>
      </div>
    </el-drawer>

    <!-- 新建定时任务（P4） -->
    <el-dialog v-model="newScheduleTaskDialog" title="新建定时任务" width="520px">
      <el-form label-width="86px" label-position="left">
        <el-form-item label="名称">
          <el-input v-model="newScheduleTask.name" placeholder="例如：每天凌晨 2 点扫 inbox" />
        </el-form-item>
        <el-form-item label="任务类型">
          <el-select v-model="newScheduleTask.kind" style="width: 100%">
            <el-option label="扫描 inbox（统计待入库文件）" value="inbox_scan" />
            <el-option label="自动补齐 dangling 占位页（不调 LLM）" value="orphan_auto_fill" />
            <el-option label="刷新孤页索引区块" value="orphan_index_refresh" />
            <el-option label="wiki lint 体检" value="wiki_lint" />
          </el-select>
        </el-form-item>
        <el-form-item label="调度方式">
          <el-radio-group v-model="newScheduleTask.scheduleType">
            <el-radio label="cron">cron 表达式</el-radio>
            <el-radio label="interval">间隔分钟</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="newScheduleTask.scheduleType === 'cron'" label="cron">
          <el-input v-model="newScheduleTask.cron" placeholder="例如：0 2 * * *（每天 02:00）" />
          <span class="maintenance-stats" style="margin-top:4px;display:block">
            5 段：分 时 日 月 周；时区 Asia/Shanghai
          </span>
        </el-form-item>
        <el-form-item v-else label="间隔">
          <el-input-number v-model="newScheduleTask.interval" :min="1" :max="1440" />
          <span style="margin-left:6px">分钟</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="newScheduleTaskDialog = false">取消</el-button>
        <el-button type="primary" :loading="scheduleSubmitting" @click="submitScheduleTask">创建</el-button>
      </template>
    </el-dialog>

    <!-- 知识维护：孤立实体 + Schema 合成（P3） -->
    <el-drawer v-model="maintenanceDrawer" size="48%" title="知识维护">
      <el-tabs v-model="maintenanceTab">
        <!-- A 整改：「孤立实体 / 孤立页面」tab 已移除，统一去左栏「知识库体检」处理。
             这里只留系统层面的事：连接状态 / 定时任务 / 源预览 / Schema 合成。 -->
        <el-tab-pane label="连接状态" name="connection">
          <div class="conn-status-grid">
            <div class="conn-status-card" :class="connStatus.local.ok ? 'ok' : 'fail'">
              <div class="conn-status-title">本机 agent</div>
              <div class="conn-status-state">{{ connStatus.local.ok ? '✓ 已连接' : '✗ 未连接' }}</div>
              <div class="conn-status-meta" v-if="connStatus.local.ok">
                绑定用户：{{ connStatus.local.bound_user || '(legacy 模式)' }}
              </div>
              <div class="conn-status-meta" v-else>
                提示：先运行 <code>python app.py</code>，并 <code>python -m scripts.bind_user bind &lt;name&gt;</code>
              </div>
            </div>
            <div class="conn-status-card" :class="connStatus.cloud.ok ? 'ok' : 'fail'">
              <div class="conn-status-title">云端控制面</div>
              <div class="conn-status-state">{{ connStatus.cloud.ok ? '✓ 已连接' : (SPLIT_MODE_ENABLED ? '✗ 未连接' : '— 单体模式') }}</div>
              <div class="conn-status-meta" v-if="connStatus.cloud.ok">
                Schema 合成 LLM：{{ connStatus.cloud.llm_configured ? '已配置' : 'mock 模式' }}
              </div>
              <div class="conn-status-meta" v-else-if="!SPLIT_MODE_ENABLED">
                未启用云本机分离；如需启用请配置 <code>VITE_CLOUD_API</code>
              </div>
            </div>
          </div>
          <el-button @click="probeConnections" :loading="connProbing">重新探测</el-button>
        </el-tab-pane>

        <el-tab-pane v-if="currentRole === 'admin' &amp;&amp; SPLIT_MODE_ENABLED" label="用户与心跳（admin）" name="admin">
          <div class="maintenance-actions">
            <el-button @click="loadAdminUsers" :loading="adminUsersLoading">刷新用户列表</el-button>
            <span class="maintenance-stats" v-if="adminUsers.length">
              共 {{ adminUsers.length }} 个云端用户
            </span>
          </div>
          <el-empty v-if="!adminUsers.length" description="无数据；点刷新加载" />
          <ul v-else class="maintenance-list maintenance-list-detailed">
            <li v-for="u in adminUsers" :key="u.username">
              <div>
                <strong>{{ u.username }}</strong>
                <el-tag size="small" :type="u.role === 'admin' ? 'warning' : 'info'">{{ u.role }}</el-tag>
                <code v-if="u.template_key">{{ u.template_key }}{{ u.has_custom_schema ? '*' : '' }}</code>
                <span v-if="u.unit">· {{ u.unit }} {{ u.title }}</span>
              </div>
              <div class="maintenance-task-meta">
                注册：{{ u.created_at || '?' }}
                <span v-if="u.last_heartbeat_at">· 心跳：{{ u.last_heartbeat_at }} · agent {{ u.agent_version }}</span>
                <span v-else class="status-err">· 从未上报心跳</span>
              </div>
              <div v-if="u.last_heartbeat_at" class="maintenance-task-meta">
                wiki 页：{{ u.pages_total || 0 }} · 入库：{{ u.last_ingest_at || '从未' }} · 定时任务：{{ u.scheduled_tasks_active || 0 }}
                <span v-if="u.schema_key_runtime &amp;&amp; u.schema_key_runtime !== u.template_key" class="status-err">
                  · runtime schema 不一致：{{ u.schema_key_runtime }}
                </span>
              </div>
            </li>
          </ul>
        </el-tab-pane>

        <el-tab-pane label="定时任务" name="schedule">
          <div class="maintenance-actions">
            <el-button @click="loadScheduleTasks">刷新</el-button>
            <el-button type="primary" @click="newScheduleTaskDialog = true">新建任务</el-button>
          </div>
          <el-empty v-if="!scheduleTasks.length" description="无定时任务" />
          <ul v-else class="maintenance-list maintenance-list-detailed">
            <li v-for="t in scheduleTasks" :key="t.id">
              <div>
                <strong>{{ t.name }}</strong>
                <code>{{ t.kind }}</code>
                <span v-if="t.schedule.type === 'cron'">cron: <code>{{ t.schedule.value }}</code></span>
                <span v-else>每 {{ t.schedule.value }} 分钟</span>
                <el-tag :type="t.enabled ? 'success' : 'info'">{{ t.enabled ? '启用' : '停用' }}</el-tag>
              </div>
              <div class="maintenance-task-meta">
                上次运行：{{ t.last_run_at || '从未' }}
                <span v-if="t.last_status === 'ok'" class="status-ok">✓</span>
                <span v-else-if="t.last_status === 'error'" class="status-err">✗ {{ t.last_error }}</span>
              </div>
              <div class="maintenance-task-actions">
                <el-button size="small" @click="runScheduleNow(t.id)">立即执行</el-button>
                <el-button size="small" @click="toggleScheduleEnabled(t)">
                  {{ t.enabled ? '停用' : '启用' }}
                </el-button>
                <el-button size="small" type="danger" @click="deleteScheduleTask(t.id)">删除</el-button>
              </div>
            </li>
          </ul>
        </el-tab-pane>

        <el-tab-pane label="源文档预览" name="preview">
          <div class="maintenance-actions">
            <el-input v-model="previewForm.path" placeholder="raw 内的相对路径（例如 sources/2024-Q1.pdf）" size="default" style="flex:1" />
            <el-button @click="loadPreviewInfo">查看元信息</el-button>
            <el-button type="primary" @click="loadPreviewText">解析文本</el-button>
            <el-button @click="openPreviewRaw" :disabled="!previewForm.path">浏览器打开（PDF/图片）</el-button>
          </div>
          <div v-if="previewResult.info" class="maintenance-stats">
            <div>{{ previewResult.info.path }} · {{ previewResult.info.file_type }} · {{ formatBytes(previewResult.info.size) }}</div>
          </div>
          <pre v-if="previewResult.text" class="synth-yaml">{{ previewResult.text }}</pre>
          <div v-if="previewResult.truncated" class="maintenance-stats">⚠ 仅显示前 50000 字</div>
        </el-tab-pane>

        <el-tab-pane label="Schema 合成" name="synth">
          <div class="synth-form">
            <el-input v-model="synthForm.goal" placeholder="管理目标，例如：管理我的读书笔记" size="large" />
            <el-input v-model="synthForm.objectsRaw" placeholder="主要对象（用逗号或换行分隔），例如：书,作者,概念,金句" type="textarea" :rows="3" />
            <el-button type="primary" :loading="synthLoading" @click="runSchemaSynth">生成预览</el-button>
          </div>
          <div v-if="synthResult.schema">
            <div class="synth-result-meta">
              来源：<el-tag :type="synthResult.source === 'llm' ? 'success' : 'warning'">{{ synthResult.source }}</el-tag>
              · key: <code>{{ synthResult.schema.key }}</code> · 标签：{{ synthResult.schema.label }}
            </div>
            <h4>派生的知识卡片分类</h4>
            <ul class="maintenance-list">
              <li v-for="c in synthResult.derived_categories" :key="c.key">
                <code>{{ c.key }}</code> — {{ c.label }}
              </li>
            </ul>
            <pre class="synth-yaml">{{ synthYamlPreview }}</pre>
            <el-button type="primary" :loading="synthApplying" @click="applySchemaCustom">应用为我的 Schema（重启 agent 后生效）</el-button>
            <el-button @click="clearCustomSchema">清除 custom，回退模板</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as d3 from 'd3'
import { ElMessage, ElMessageBox } from 'element-plus'
import VChart from 'vue-echarts'
import { use as echartsUse } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DatasetComponent,
} from 'echarts/components'

echartsUse([
  CanvasRenderer,
  LineChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DatasetComponent,
])
import {
  Box,
  ChatDotRound,
  CircleCheck,
  Collection,
  Connection,
  ArrowRight,
  Document,
  EditPen,
  Delete,
  Files,
  HomeFilled,
  Key,
  Plus,
  SwitchButton,
  User,
  FolderOpened,
  Promotion,
  Refresh,
  RefreshLeft,
  Search,
  Setting,
  Tools,
  UploadFilled,
  View,
  Download,
} from '@element-plus/icons-vue'
import { GRAPH_LAYOUTS, layoutTargets } from './graphLayouts'
import { sortKnowledgePages } from './pageSorting'
import { normalizeKnowledgeSources } from './chatSources'
import {
  apiFetch,
  SPLIT_MODE_ENABLED,
  persistTokensFromResponse,
  clearTokens,
} from './apiClient'

// 门户模式：当前页面不是从 localhost 打开（一般指云端公网 IP / 域名）。
// 这时本机 agent 不可达，只展示账号 / 下载相关菜单；隐藏工作菜单。
const IS_PORTAL_MODE = !['localhost', '127.0.0.1'].includes(window.location.hostname)

const _allNavItems = [
  { key: 'home', label: '首页', icon: HomeFilled, portal: true },
  { key: 'ingest', label: '上传材料', icon: Box, portal: false },
  { key: 'new-note', label: '新建笔记', icon: Plus, portal: false },
  { key: 'chat', label: '对话查询', icon: ChatDotRound, portal: false },
  { key: 'knowledge', label: '知识卡片', icon: Collection, portal: false },
  { key: 'graph', label: '关系图谱', icon: Connection, portal: false },
  { key: 'lint', label: '知识库体检', icon: CircleCheck, portal: false },
  { key: 'config', label: '系统配置', icon: Setting, portal: true },  // 配置里有用户/邀请码（admin）
]
const navItems = IS_PORTAL_MODE
  ? _allNavItems.filter(item => item.portal)
  : _allNavItems

const activeView = ref('home')
const batches = ref([])
const pages = ref([])
const allPages = ref([])
const expandedFolders = ref({})
const config = ref({})
const configForm = ref(defaultConfig())
const firstRunDialog = ref(false)
const firstRunForm = ref({ mode: 'default', custom: '' })
const firstRunSaving = ref(false)

// === 鉴权状态 ===
const authState = ref('loading')          // 'loading' | 'setup' | 'login' | 'authed'
const authMode = ref('login')             // 仅 authState='login' 时生效：'login' | 'register'
const currentUser = ref(null)
const currentRole = ref(null)             // 'admin' | 'member' | null
// 用户档案（unit/title/email）—— 登录后由 /api/cloud/auth/status 或 /login 接口写入
const currentProfile = ref({ unit: '', title: '', email: '', template_key: '' })
const currentAffiliation = computed(() => {
  const u = currentProfile.value.unit?.trim() || ''
  const t = currentProfile.value.title?.trim() || ''
  if (u && t) return `${u} ${t}`
  return u || t || ''
})
const authSubmitting = ref(false)
const setupForm = ref({ username: '', password: '', password_confirm: '', raw_mode: 'default', raw_dir: '' })
const loginForm = ref({ username: '', password: '' })
const registerForm = ref({
  invite_code: '',
  username: '',
  password: '',
  password_confirm: '',
  unit: '',
  title: '',
  email: '',
  template_key: '',  // P2 起：注册必选模板
})
// 云端可选 schema 模板列表（P2-A）。仅在分离模式下加载；单体模式下为空数组，不显示选择卡片。
const schemaTemplates = ref([])
const setupTemplateKey = ref('police')  // setup（首位 admin）默认警务模板
const loginRemember = ref(true)
const changePasswordDialog = ref(false)
const changePasswordForm = ref({ old: '', new: '', confirm: '' })

// === 邀请码管理（仅 admin） ===
const invitesList = ref([])
const invitesCreating = ref(false)
const createInviteDialog = ref({ open: false, note: '' })
const changePasswordSubmitting = ref(false)
const userMenuVisible = ref(false)

// 首页数据
const homeStats = ref({
  pages: 0,
  batches: 0,
  ingested_files: 0,
  by_type: {},
  this_week: {},
  last_week: {},
  period_summary: {},
  daily_activity: [],
  recent_qa: [],
  recent_notes: [],
})
const homeActivity = ref([])
// ─────────────────────────────────────────────────────────────────
// 首页重设计补丁 — 追加到 App.vue <script setup> 中
// 找到：const homeActivity = ref([])
// 在该行之后粘贴以下全部内容
// ─────────────────────────────────────────────────────────────────

// ── 日历状态 ──
const calYear = ref(new Date().getFullYear())
const calMonth = ref(new Date().getMonth())   // 0-indexed
const calDrawerOpen = ref(false)
const calSelectedDay = ref(null)  // { year, month, day }

// ── 日历月份标签 ──
const calMonthLabel = computed(() => {
  return new Date(calYear.value, calMonth.value, 1)
    .toLocaleDateString('zh-CN', { year: 'numeric', month: 'long' })
})

// ── 日历翻页 ──
function calPrevMonth() {
  if (calMonth.value === 0) { calYear.value -= 1; calMonth.value = 11 }
  else calMonth.value -= 1
}
function calNextMonth() {
  if (calMonth.value === 11) { calYear.value += 1; calMonth.value = 0 }
  else calMonth.value += 1
}

// ── 从 homeStats.recent_qa 构建按日期索引的对话记录 ──
const qaByDate = computed(() => {
  const map = {}
  const qaList = homeStats.value.recent_qa || []
  qaList.forEach(qa => {
    const d = (qa.created || '').slice(0, 10)  // YYYY-MM-DD
    if (!map[d]) map[d] = []
    map[d].push(qa)
  })
  return map
})

// ── 日历格子数据 ──
const calCells = computed(() => {
  const today = new Date()
  const firstDay = new Date(calYear.value, calMonth.value, 1).getDay()
  const daysInMonth = new Date(calYear.value, calMonth.value + 1, 0).getDate()
  const startOffset = (firstDay + 6) % 7  // 周一为起点

  const cells = []
  for (let i = 0; i < startOffset; i++) cells.push({ day: null, chatCount: 0, level: 0 })
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${calYear.value}-${String(calMonth.value + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    const chatCount = (qaByDate.value[dateStr] || []).length
    let level = 0
    if (chatCount >= 1) level = 1
    if (chatCount >= 2) level = 2
    if (chatCount >= 4) level = 3
    if (chatCount >= 6) level = 4
    const isToday = (
      today.getFullYear() === calYear.value &&
      today.getMonth() === calMonth.value &&
      today.getDate() === d
    )
    const isSelected = (
      calSelectedDay.value?.year === calYear.value &&
      calSelectedDay.value?.month === calMonth.value &&
      calSelectedDay.value?.day === d
    )
    cells.push({ day: d, dateStr, chatCount, level, isToday, isSelected })
  }
  return cells
})

// ── 点击日历日期 ──
function selectCalDay(cell) {
  calSelectedDay.value = { year: calYear.value, month: calMonth.value, day: cell.day }
  calDrawerOpen.value = true
}

// ── 抽屉中的 QA 列表 ──
const calDrawerQA = computed(() => {
  if (!calSelectedDay.value) return []
  const { year, month, day } = calSelectedDay.value
  const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  return qaByDate.value[dateStr] || []
})

// ── 抽屉日期标签 ──
const calDrawerDateLabel = computed(() => {
  if (!calSelectedDay.value) return ''
  const { year, month, day } = calSelectedDay.value
  return new Date(year, month, day).toLocaleDateString('zh-CN', {
    year: 'numeric', month: 'long', day: 'numeric', weekday: 'long'
  })
})

// ── 待精炼数量（从 batches 中统计） ──
const staleCount = computed(() => {
  return batches.value.filter(b => b.status === 'stale' || b.status === 'partial').length
})

// ── 知识库健康度评分 ──
// 后端 graph.run_lint 已计算（断链*3 + 孤立*1 + 过期*0.5 + 占位*1.5）/总页数
// 前端优先用后端值；旧版 / 未跑过体检时退化为本地估算
const lintHealthScore = computed(() => {
  if (typeof lint.value.health_score === 'number') return lint.value.health_score
  const broken = lint.value.broken_links?.length || 0
  const orphan = lint.value.orphan_pages?.length || 0
  const stale = lint.value.stale_pages?.length || 0
  const placeholder = lint.value.placeholder_pages?.length || 0
  const total = broken * 3 + orphan + stale * 0.5 + placeholder * 1.5
  if (total === 0) return 100
  return Math.max(0, Math.round(100 - total * 3))
})

// ── 健康度分项 ──
const healthItems = computed(() => {
  const broken = lint.value.broken_links?.length || 0
  const orphan = lint.value.orphan_pages?.length || 0
  const stale = lint.value.stale_pages?.length || 0
  const placeholder = lint.value.placeholder_pages?.length || 0
  return [
    { label: '断链检测', val: Math.max(0, 100 - broken * 10), color: '#19bf78', count: broken, category: 'broken_links' },
    { label: '孤立页面', val: Math.max(0, 100 - orphan * 8), color: '#f59e0b', count: orphan, category: 'orphan_pages' },
    { label: '内容新鲜', val: Math.max(0, 100 - stale * 5), color: '#3b82f6', count: stale, category: 'stale_pages' },
    { label: '占位页', val: Math.max(0, 100 - placeholder * 8), color: '#a855f7', count: placeholder, category: 'placeholder_pages' },
  ]
})

// ── 首页问候语 ──
const homeGreeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

// ── Sparkline 点位计算 ──
function sparkPoints(dailyActivity, key) {
  const days = (dailyActivity || []).slice(-12)
  if (!days.length) return '0,20 120,20'
  const values = days.map(d => Number(d[key] || 0))
  const max = Math.max(...values, 1)
  if (days.length === 1) {
    const y = Math.round(26 - (Number(days[0][key] || 0) / max) * 22)
    return `0,${y} 120,${y}`
  }
  return days.map((d, i) => {
    const x = Math.round((i / (days.length - 1)) * 120)
    const y = Math.round(26 - (Number(d[key] || 0) / max) * 22)
    return `${x},${y}`
  }).join(' ')
}

// ── Activity Feed（整合批次 + 笔记 + 问答动态） ──
const homeFeedItems = computed(() => {
  const items = []
  // 近期批次
  const recentB = batches.value.slice(0, 4)
  recentB.forEach(b => {
    items.push({
      id: `batch-${b.id}`,
      ico: b.status === 'stale' ? '⚠️' : '📥',
      icoClass: b.status === 'stale' ? 'amber' : 'blue',
      title: summarizeBatchTitle(b) + (b.status === 'stale' ? ' 待精炼' : ' 入库完成'),
      meta: `生成 ${b.generated_files?.length || 0} 个知识页 · ${formatTime(b.created_at)}`,
      time: relativeTime(b.created_at),
      onClick: () => openBatch(b.id),
    })
  })
  // 最近新建笔记
  const recentNotes = (homeStats.value.recent_notes || []).slice(0, 3)
  recentNotes.forEach(note => {
    items.push({
      id: `note-${note.slug}`,
      ico: '✍',
      icoClass: 'green',
      title: note.title,
      meta: `新建笔记 · ${note.created || note.updated || ''}`,
      time: note.created || note.updated || '',
      onClick: () => openNoteFromHome(note),
    })
  })
  // 近期问答
  const recentQA = (homeStats.value.recent_qa || []).slice(0, 3)
  recentQA.forEach(qa => {
    items.push({
      id: `qa-${qa.slug}`,
      ico: '💬',
      icoClass: 'purple',
      title: qa.title,
      meta: `已沉淀为问答记忆 · ${qa.created || ''}`,
      time: qa.created || '',
      onClick: () => openQAFromHome(qa),
    })
  })
  // 按时间排序（简单按插入顺序，批次已经是倒序）
  return items.slice(0, 8)
})

// ── 相对时间格式化 ──
function relativeTime(isoStr) {
  if (!isoStr) return ''
  const diff = Date.now() - new Date(isoStr).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return '刚刚'
  if (m < 60) return `${m}分钟前`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}小时前`
  const d = Math.floor(h / 24)
  if (d < 7) return `${d}天前`
  return formatTime(isoStr).slice(0, 10)
}

// ── 导航跳转辅助（setActiveView 已存在则跳过） ──
function setActiveView(view) {
  activeView.value = view
  if (view === 'graph' && !graph.value.nodes.length) {
    loadGraph()
  } else if (view === 'graph') {
    nextTick(scheduleRenderGraph)
  } else if (view === 'config' && currentRole.value === 'admin') {
    loadInvites()
  } else if (view === 'lint' && !lint.value.summary) {
    runLint()
  }
}

// 从首页健康度 row 跳到体检页 + 自动打开对应类别的修复弹窗
function goLintCategory(category) {
  setActiveView('lint')
  nextTick(() => {
    if ((lint.value[category]?.length || 0) > 0) openLintFix(category)
  })
}

// ── 打开新建笔记对话框 ──
function openNoteDialog() {
  noteDialog.value = true
}


// FAQ 静态内容（直接改这里维护）
const faqItems = [
  { q: '如何上传材料？', a: '左侧「材料入库」→ 拖入文件或点击选择 → 系统会自动归档原始材料并编译为 wiki 页面。支持 Word / PDF / Markdown / Excel / 图片 / 文本。' },
  { q: '上传后多久能看到结果？', a: '单文件 30-90 秒，多文件按 3 路并发；进度实时显示在页面顶部。LLM 调用耗时占大头。' },
  { q: '入库失败的「待精炼」页面怎么处理？', a: '运行 python scripts/retry_stale.py --all 重新处理；源材料还在 raw/sources/ 目录里，重试是无损的。' },
  { q: '怎么查找已有的知识？', a: '「整理后的知识」页面有搜索框（标题/摘要/标签/slug），也可按类型筛选；或在「对话查询」用自然语言提问。' },
  { q: '如何邀请同事使用？', a: '管理员在「系统配置」→「用户与邀请码」处生成邀请码，把 8 位码发给同事，对方在登录页「注册」tab 输入即可。' },
  { q: '我能不能改 LLM 模型？', a: '在「系统配置」最上方修改文本/视觉/OCR 模型的 base_url、模型名和 API key，保存后点「测试连接」确认通畅。' },
]
const configSaving = ref(false)
const wikiReadOnly = true
const canDeleteWikiPages = true
const configTesting = ref({ llm: false, vision_model: false, ocr_model: false })
const agentStatus = ref({ state: 'idle', message: '空闲', updated_at: '' })
const lint = ref({})
const graph = ref({ nodes: [], edges: [], communities: [] })
const graphLoading = ref(false)
const graphMerged = ref(false)
const graphLayout = ref('force')
const graphMotion = ref(true)
const graphLabels = ref(true)
const graphSearch = ref('')
const graphTypeFilter = ref('all')
const graphShowRelations = ref(true)
const graphSvgRef = ref(null)
const graphCanvasRef = ref(null)
const selectedNode = ref(null)
const focusedNodeId = ref(null)
let graphSimulation = null
let graphNodeSelection = null
let graphLinkSelection = null
let graphEdgeLabelSelection = null
let graphZoomBehavior = null
let graphStageSelection = null
let graphRenderTimer = null
let graphLastLayout = { width: 1400, height: 900, padding: 120, nodes: [] }
let batchRefreshTimer = null
let agentStatusTimer = null
const fileList = ref([])
const uploadFilesExpanded = ref(false)
const uploadPreviewLimit = 5
const uploading = ref(false)
const currentBatch = ref(null)
const batchDrawer = ref(false)
const noteDialog = ref(false)
const noteSubmitting = ref(false)
const noteUrlExtracting = ref(false)
const noteForm = ref({ title: '', url: '', content: '', tagsText: '' })
const selectedBatch = ref(null)
const expandedBatchId = ref(null)
const selectedBatchIds = ref([])
const reparsingBatchIds = ref([])
const deletingBatches = ref(false)
const knowledgeTreeExpanded = ref(true)
const pageDrawer = ref(false)
const selectedPage = ref(null)
const pageEditMode = ref(false)
const pageEditDraft = ref({ title: '', body: '' })
const pageSaving = ref(false)
const batchPage = ref(1)
const batchPageSize = ref(7)
const pageFilter = ref('all')
const pageNumber = ref(1)
const pageSize = ref(24)
const pageSearch = ref('')
const pageSortBy = ref('imported_desc')
const selectedPageKeys = ref([])
const messages = ref([
  { id: 1, role: 'assistant', content: '可以直接问我：某个小区最近有哪些警情，某名人员关联了哪些案件，或者这批材料里有什么线索。' },
])
const chatInput = ref('')
const chatLoading = ref(false)
const lintLoading = ref(false)
const lintFixSubmitting = ref(false)
const lintFixDialog = ref({ open: false, category: null, items: [], selected: [] })
const lintFixBulkAction = ref('')

const lintFixDialogTitle = computed(() => {
  const map = {
    broken_links: '修复断链',
    orphan_pages: '处理孤立页面',
    stale_pages: '处理过期页面',
    placeholder_pages: '处理占位页',
  }
  return map[lintFixDialog.value.category] || '体检处理'
})

function lintFixActionOptions(category) {
  if (category === 'broken_links') {
    return [
      { value: 'remove', label: '删除该链接' },
      { value: 'create_stub', label: '创建空白占位页' },
      { value: 'create_stub_smart', label: '智能补齐 (LLM 生成草稿)' },
    ]
  }
  if (category === 'orphan_pages') {
    return [
      { value: 'enrich', label: '自动补充关联' },
      { value: 'ignore', label: '标记独立(忽略)' },
    ]
  }
  if (category === 'placeholder_pages') {
    return [
      { value: 'enrich', label: '智能补全 (LLM)' },
      { value: 'accept', label: '接受存档(清除占位标记)' },
      { value: 'delete', label: '删除占位页' },
    ]
  }
  return [
    { value: 'touch', label: '标记为已确认(更新日期)' },
    { value: 'ignore', label: '标记独立(忽略)' },
  ]
}

const stats = computed(() => ({
  pages: pages.value.length,
  alerts:
    (lint.value.broken_links?.length || 0) +
    (lint.value.orphan_pages?.length || 0) +
    (lint.value.stale_pages?.length || 0),
}))

// 首页 KPI / 图表 computed
const entityTotal = computed(() => {
  const byType = homeStats.value.by_type || {}
  return Object.values(byType).reduce((sum, n) => sum + (Number(n) || 0), 0)
})

const weekDelta = computed(() => {
  const now = homeStats.value.this_week || {}
  const prev = homeStats.value.last_week || {}
  return {
    chat: (now.chat || 0) - (prev.chat || 0),
    ingest: (now.ingest || 0) - (prev.ingest || 0),
  }
})

function _actionLabel(action) {
  return ({ ingest: '入库', chat: '对话', create_page: '新建', edit_page: '编辑' })[action] || action
}

const dailyTrendOption = computed(() => {
  const days = homeStats.value.daily_activity || []
  const dates = days.map((d) => d.date.slice(5))  // MM-DD
  const actions = ['ingest', 'chat', 'create_page', 'edit_page']
  const series = actions.map((act) => ({
    name: _actionLabel(act),
    type: 'line',
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    data: days.map((d) => d[act] || 0),
    areaStyle: act === 'ingest' ? { opacity: 0.08 } : undefined,
  }))
  return {
    title: { text: '近 14 天活动趋势', left: 'left', textStyle: { fontSize: 14, fontWeight: 600 } },
    tooltip: { trigger: 'axis' },
    legend: { right: 0, top: 0, itemWidth: 12, itemHeight: 8 },
    grid: { top: 50, left: 36, right: 16, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', minInterval: 1, axisLabel: { fontSize: 11 } },
    series,
  }
})

const typeDistributionOption = computed(() => {
  const byType = homeStats.value.by_type || {}
  const data = Object.entries(byType)
    .filter(([, n]) => Number(n) > 0)
    .map(([type, n]) => ({ name: typeLabel(type), value: Number(n) }))
    .sort((a, b) => b.value - a.value)
  return {
    title: { text: '实体分布', left: 'left', textStyle: { fontSize: 14, fontWeight: 600 } },
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { type: 'scroll', bottom: 0, itemWidth: 10, itemHeight: 8, textStyle: { fontSize: 11 } },
    series: [{
      type: 'pie',
      radius: ['38%', '62%'],
      center: ['50%', '48%'],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: '#fff', borderWidth: 1 },
      label: { show: false },
      labelLine: { show: false },
      data,
    }],
  }
})

const modelName = computed(() => config.value?.llm?.model || '未配置')
const agentStatusLabel = computed(() => agentStatus.value?.message || agentStateLabel(agentStatus.value?.state))
const agentStatusClass = computed(() => `agent-${agentStatus.value?.state || 'idle'}`)
const currentStep = computed(() => {
  if (!currentBatch.value) return 0
  if (uploading.value) return 2
  if (currentBatch.value.vectorized) return 5
  if (currentBatch.value.generated_files?.length) return 4
  return 1
})

const recentBatches = computed(() => batches.value.slice(0, 6))
const visibleUploadFiles = computed(() => {
  if (uploadFilesExpanded.value) return fileList.value
  return fileList.value.slice(0, uploadPreviewLimit)
})
const uploadHiddenCount = computed(() => Math.max(0, fileList.value.length - visibleUploadFiles.value.length))
const uploadTotalSize = computed(() => {
  const total = fileList.value.reduce((sum, item) => sum + (item.size || item.raw?.size || 0), 0)
  return formatFileSize(total)
})
const pagedBatches = computed(() => {
  const start = (batchPage.value - 1) * batchPageSize.value
  return batches.value.slice(start, start + batchPageSize.value)
})
const selectedBatchSet = computed(() => new Set(selectedBatchIds.value))
const reparsingBatchSet = computed(() => new Set(reparsingBatchIds.value))
const allPagedBatchesSelected = computed(() => {
  if (!pagedBatches.value.length) return false
  return pagedBatches.value.every((batch) => selectedBatchSet.value.has(batch.id))
})
const hasRunningBatches = computed(() => batches.value.some((batch) => batch.status === 'running'))
// 搜索 + 排序：纯前端处理（pages 已经全量加载，无需再请求后端）
// 默认按更新时间倒序（最新→最旧）；搜索匹配 标题/正文摘要/tags/slug，大小写不敏感
const filteredPages = computed(() => {
  let list = pages.value
  const kw = pageSearch.value.trim().toLowerCase()
  if (kw) {
    list = list.filter((p) => {
      const title = String(p.title || '').toLowerCase()
      const preview = String(p.body_preview || '').toLowerCase()
      const slug = String(p.slug || '').toLowerCase()
      const tags = (p.tags || []).map((t) => String(t).toLowerCase()).join(' ')
      return title.includes(kw) || preview.includes(kw) || slug.includes(kw) || tags.includes(kw)
    })
  }
  return sortKnowledgePages(list, pageSortBy.value)
})

const pagedPages = computed(() => {
  const start = (pageNumber.value - 1) * pageSize.value
  return filteredPages.value.slice(start, start + pageSize.value)
})

// 搜索/排序/分类筛选/分页大小变化时回到第 1 页，避免在第 N 页时筛选完不足 N 页显示空白
watch([pageSearch, pageSortBy, pageFilter, pageSize], () => {
  pageNumber.value = 1
})
function pageKey(page) {
  return `${page.type}/${page.slug}`
}
function isPageSelected(page) {
  return selectedPageKeys.value.includes(pageKey(page))
}
const currentPageAllSelected = computed(() => {
  if (!pagedPages.value.length) return false
  return pagedPages.value.every((p) => selectedPageKeys.value.includes(pageKey(p)))
})
const currentPageIndeterminate = computed(() => {
  if (!pagedPages.value.length) return false
  const some = pagedPages.value.some((p) => selectedPageKeys.value.includes(pageKey(p)))
  return some && !currentPageAllSelected.value
})
// P2-A 起：分类列表来自 schema_runtime（/api/wiki/categories）。
// schemaCategories 在 checkAuth 后由 loadSchemaCategories() 拉取；失败则保留警务默认作 fallback。
const schemaCategories = ref([])
async function loadSchemaCategories() {
  try {
    const data = await api('/api/wiki/categories')
    if (Array.isArray(data) && data.length) {
      schemaCategories.value = data
    }
  } catch {
    schemaCategories.value = []  // 保持空 → fallback 默认
  }
}
const categoryOptions = computed(() => {
  const fromSchema = schemaCategories.value
  const defaults = fromSchema.length ? fromSchema : [
    { key: 'cases', label: '案件' },
    { key: 'persons', label: '人员' },
    { key: 'locations', label: '地点' },
    { key: 'laws', label: '法规' },
    { key: 'techniques', label: '技战法' },
    { key: 'notes', label: '笔记' },
    { key: 'summaries', label: '研判' },
    { key: 'outputs', label: '问答记忆' },
  ]
  const custom = (configForm.value?.wiki?.custom_categories || [])
    .map((item) => ({
      key: String(item?.key || '').trim(),
      label: String(item?.label || item?.key || '').trim(),
    }))
    .filter((item) => item.key && item.label)
  const seen = new Set()
  return [...defaults, ...custom].filter((item) => {
    if (seen.has(item.key)) return false
    seen.add(item.key)
    return true
  })
})
const knowledgeFolders = computed(() => {
  return categoryOptions.value
    .map((type) => {
      const items = allPages.value.filter((page) => page.type === type.key)
      return {
        type: type.key,
        label: type.label,
        count: items.length,
        items: items.slice(0, 4),
      }
    })
})

const graphLegend = [
  { type: 'cases', label: '案件', color: '#3478f6' },
  { type: 'persons', label: '人员', color: '#2f9bff' },
  { type: 'locations', label: '地点', color: '#36b3d8' },
  { type: 'laws', label: '法规', color: '#ff8a1f' },
  { type: 'techniques', label: '技战法', color: '#e95664' },
  { type: 'notes', label: '笔记/文档', color: '#7b8ba5' },
]

const graphTypeOptions = computed(() => {
  const types = new Set((graph.value.nodes || []).map((node) => node.type).filter(Boolean))
  return [...types].map((type) => ({ type, label: typeLabel(type) }))
})

const graphVisibleNodes = computed(() => {
  const keyword = graphSearch.value.trim().toLowerCase()
  return (graph.value.nodes || []).filter((node) => {
    if (graphTypeFilter.value !== 'all' && node.type !== graphTypeFilter.value) return false
    if (!keyword) return true
    const haystack = [node.label, node.id, typeLabel(node.type), node.community].join(' ').toLowerCase()
    return haystack.includes(keyword)
  })
})

const graphVisibleEdges = computed(() => {
  if (!graphShowRelations.value) return []
  const ids = new Set(graphVisibleNodes.value.map((node) => node.id))
  return (graph.value.edges || []).filter((edge) => {
    const source = edge.source && typeof edge.source === 'object' ? edge.source.id : edge.source
    const target = edge.target && typeof edge.target === 'object' ? edge.target.id : edge.target
    return ids.has(source) && ids.has(target)
  })
})

const graphVisibleCommunityCount = computed(() => {
  const communities = new Set(graphVisibleNodes.value.map((node) => node.community ?? 'default'))
  return communities.size
})

const selectedNodeRelations = computed(() => {
  if (!selectedNode.value) return []
  const selectedId = selectedNode.value.id
  const nodeMap = new Map((graph.value.nodes || []).map((node) => [node.id, node]))
  return (graph.value.edges || [])
    .map((edge, index) => {
      const sourceId = edge.source && typeof edge.source === 'object' ? edge.source.id : edge.source
      const targetId = edge.target && typeof edge.target === 'object' ? edge.target.id : edge.target
      if (sourceId !== selectedId && targetId !== selectedId) return null
      const otherId = sourceId === selectedId ? targetId : sourceId
      const node = nodeMap.get(otherId)
      if (!node) return null
      return {
        key: `${sourceId}-${targetId}-${index}`,
        node,
        label: edge.label || edge.relation || '关联',
      }
    })
    .filter(Boolean)
})

const graphVisibleNodeMap = computed(() => {
  return new Map(graphVisibleNodes.value.map((node) => [node.id, node]))
})

const graphAdjacencyMap = computed(() => {
  const visible = graphVisibleNodeMap.value
  const map = new Map()
  for (const node of graphVisibleNodes.value) {
    map.set(node.id, { nodes: new Set([node.id]), edges: [] })
  }
  for (const edge of graphVisibleEdges.value) {
    const source = edge.source && typeof edge.source === 'object' ? edge.source.id : edge.source
    const target = edge.target && typeof edge.target === 'object' ? edge.target.id : edge.target
    if (!visible.has(source) || !visible.has(target)) continue
    if (!map.has(source)) map.set(source, { nodes: new Set([source]), edges: [] })
    if (!map.has(target)) map.set(target, { nodes: new Set([target]), edges: [] })
    map.get(source).nodes.add(target)
    map.get(source).edges.push(edge)
    map.get(target).nodes.add(source)
    map.get(target).edges.push(edge)
  }
  return map
})

async function api(path, options = {}) {
  // 单体模式 → same-origin fetch；分离模式 → 走 apiClient（双 baseURL + JWT）
  // 行为对调用方透明，路径仍用 /api/auth/、/api/admin/invites 这类逻辑名
  const response = await apiFetch(path, options)
  const data = await response.json().catch(() => ({}))
  // 登录/注册响应里有 access_token / refresh_token 时自动落盘
  persistTokensFromResponse(data)
  if (response.status === 401 && !path.startsWith('/api/auth/') && !path.startsWith('/api/cloud/auth/')) {
    // session/JWT 失效，踢回登录页
    authState.value = 'login'
    currentUser.value = null
    if (SPLIT_MODE_ENABLED) clearTokens()
    throw new Error(data.error || '请先登录')
  }
  if (!response.ok) {
    throw new Error(data.error || `请求失败：${response.status}`)
  }
  return data
}

// === Schema 模板（P2-A）===
async function loadSchemaTemplates() {
  if (!SPLIT_MODE_ENABLED) {
    schemaTemplates.value = []
    return
  }
  try {
    const res = await api('/api/cloud/schema/templates')
    schemaTemplates.value = Array.isArray(res?.templates) ? res.templates : []
    if (!registerForm.value.template_key && schemaTemplates.value.length) {
      registerForm.value.template_key = schemaTemplates.value[0].key
    }
  } catch (err) {
    // 拉取失败不阻塞注册：单体模式下也走这条路（只是 picker 不显示）
    schemaTemplates.value = []
  }
}

// === 鉴权流程 ===
async function checkAuth() {
  try {
    const status = await api('/api/auth/status')
    // 异步加载模板，不阻塞 status 判断
    loadSchemaTemplates()
    if (!status.has_user) {
      authState.value = 'setup'
    } else if (!status.logged_in) {
      authState.value = 'login'
      authMode.value = 'login'
    } else {
      currentUser.value = status.username
      currentRole.value = status.role || null
      currentProfile.value = {
        unit: status.unit || '',
        title: status.title || '',
        email: status.email || '',
        template_key: status.template_key || '',
      }
      authState.value = 'authed'
      // 进入主应用,加载初始数据
      await loadSchemaCategories()
      await refreshAll()
      await loadHome()
      startBatchPolling()
      startAgentStatusPolling()
    }
  } catch (error) {
    // 后端不可达
    authState.value = 'login'
    ElMessage.error('无法连接后端,请检查服务')
  }
}

async function submitSetup() {
  const f = setupForm.value
  if (!f.username.trim() || !f.password) {
    ElMessage.warning('用户名和密码不能为空')
    return
  }
  if (f.password.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  if (f.password !== f.password_confirm) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  authSubmitting.value = true
  try {
    await api('/api/auth/setup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: f.username.trim(),
        password: f.password,
        // 单体模式下后端会忽略；分离模式下首位 admin 也存一个 template_key
        template_key: setupTemplateKey.value || 'police',
      }),
    })
    // 同时写 raw_dir 配置
    const raw_dir = f.raw_mode === 'custom' ? (f.raw_dir || '').trim() : ''
    await api('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ raw_dir, first_run_done: true }),
    })
    ElMessage.success('初始化完成')
    currentUser.value = f.username.trim()
    currentProfile.value = {
      unit: '', title: '', email: '',
      template_key: setupTemplateKey.value || '',
    }
    authState.value = 'authed'
    await loadSchemaCategories()
    await refreshAll()
    await loadHome()
    startBatchPolling()
    startAgentStatusPolling()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    authSubmitting.value = false
  }
}

async function submitLogin() {
  const f = loginForm.value
  if (!f.username.trim() || !f.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  authSubmitting.value = true
  try {
    const res = await api('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: f.username.trim(), password: f.password }),
    })
    currentUser.value = res.username
    currentRole.value = res.role || null
    currentProfile.value = {
      unit: res.unit || '',
      title: res.title || '',
      email: res.email || '',
      template_key: res.template_key || '',
    }
    authState.value = 'authed'
    loginForm.value.password = ''
    await loadSchemaCategories()
    await refreshAll()
    await loadHome()
    startBatchPolling()
    startAgentStatusPolling()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    authSubmitting.value = false
  }
}

async function submitRegister() {
  const f = registerForm.value
  if (!f.invite_code.trim()) {
    ElMessage.warning('请输入邀请码')
    return
  }
  if (!f.username.trim() || !f.password) {
    ElMessage.warning('用户名和密码不能为空')
    return
  }
  if (f.password.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  if (f.password !== f.password_confirm) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  if (!f.unit.trim()) {
    ElMessage.warning('请填写单位')
    return
  }
  if (!f.title.trim()) {
    ElMessage.warning('请填写职务')
    return
  }
  // 分离模式（云端在线）下，模板必选；单体模式不需要 template_key
  if (SPLIT_MODE_ENABLED && schemaTemplates.value.length && !f.template_key) {
    ElMessage.warning('请选择一个 Schema 模板')
    return
  }
  authSubmitting.value = true
  try {
    const res = await api('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        invite_code: f.invite_code.trim().toUpperCase(),
        username: f.username.trim(),
        password: f.password,
        unit: f.unit.trim(),
        title: f.title.trim(),
        email: f.email.trim(),
        template_key: f.template_key || '',
      }),
    })
    ElMessage.success('注册成功，已自动登录')
    currentUser.value = res.username
    currentRole.value = res.role || null
    currentProfile.value = {
      unit: res.unit || '',
      title: res.title || '',
      email: res.email || '',
      template_key: res.template_key || '',
    }
    authState.value = 'authed'
    // 清掉密码字段，留下其他便于参考
    registerForm.value.password = ''
    registerForm.value.password_confirm = ''
    registerForm.value.invite_code = ''
    await loadSchemaCategories()
    await refreshAll()
    await loadHome()
    startBatchPolling()
    startAgentStatusPolling()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    authSubmitting.value = false
  }
}

function localModeLogin() {
  ElMessage.info('本机账户登录会使用同一套本地账号校验，请输入账号密码后登录')
}

function forgotPassword() {
  ElMessage.info('本地模式下请联系管理员重置密码')
}

function openLoginSettings() {
  ElMessage.info('系统设置登录后可在左侧菜单中配置')
}

async function logoutUser() {
  try {
    await api('/api/auth/logout', { method: 'POST' })
  } catch {
    /* ignore */
  }
  // 分离模式下清掉本地 token，单体模式下是 no-op
  clearTokens()
  currentUser.value = null
  userMenuVisible.value = false
  authState.value = 'login'
  stopBatchPolling()
  stopAgentStatusPolling()
}

async function submitChangePassword() {
  const f = changePasswordForm.value
  if (!f.old || !f.new) {
    ElMessage.warning('请填写完整')
    return
  }
  if (f.new.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (f.new !== f.confirm) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  changePasswordSubmitting.value = true
  try {
    await api('/api/auth/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old: f.old, new: f.new }),
    })
    ElMessage.success('密码已更新')
    changePasswordDialog.value = false
    changePasswordForm.value = { old: '', new: '', confirm: '' }
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    changePasswordSubmitting.value = false
  }
}

async function loadHome() {
  try {
    const [stats, activity] = await Promise.all([
      api('/api/stats'),
      api('/api/activity?limit=20'),
    ])
    homeStats.value = stats
    homeActivity.value = activity
  } catch (error) {
    /* 静默 */
  }
}

async function loadAgentStatus() {
  try {
    agentStatus.value = await api('/api/agent/status')
  } catch {
    agentStatus.value = { state: 'offline', message: '状态不可用' }
  }
}

async function refreshAll() {
  await Promise.all([loadBatches(), loadPages(), loadConfig(), loadAgentStatus()])
  if (activeView.value === 'graph') {
    await loadGraph()
  }
}

async function loadBatches() {
  batches.value = await api('/api/ingest/batches')
  const availableIds = new Set(batches.value.map((batch) => batch.id))
  selectedBatchIds.value = selectedBatchIds.value.filter((id) => availableIds.has(id))
  const maxPage = Math.max(1, Math.ceil(batches.value.length / batchPageSize.value))
  if (batchPage.value > maxPage) {
    batchPage.value = maxPage
  }
  if (selectedBatch.value?.id) {
    const latestSelected = batches.value.find((batch) => batch.id === selectedBatch.value.id)
    if (latestSelected) selectedBatch.value = latestSelected
  }
}

async function loadPages() {
  allPages.value = await api('/api/wiki/pages')
  const url = pageFilter.value === 'all' ? '/api/wiki/pages' : `/api/wiki/pages?type=${pageFilter.value}`
  pages.value = await api(url)
  pageNumber.value = 1
  selectedPageKeys.value = []
  syncExpandedFolders()
}

async function loadConfig() {
  try {
    config.value = await api('/api/config')
    configForm.value = normalizeConfig(config.value)
  } catch {
    config.value = {}
    configForm.value = defaultConfig()
  }
  // 首次启动检测:若 first_run_done 未设置 → 弹初始化向导
  if (!config.value?.first_run_done) {
    firstRunForm.value = { mode: 'default', custom: '' }
    firstRunDialog.value = true
  }
}

async function submitFirstRun() {
  firstRunSaving.value = true
  try {
    const raw_dir = firstRunForm.value.mode === 'custom'
      ? (firstRunForm.value.custom || '').trim()
      : ''
    if (firstRunForm.value.mode === 'custom' && !raw_dir) {
      ElMessage.warning('请填写自定义路径,或选择默认')
      firstRunSaving.value = false
      return
    }
    await api('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ raw_dir, first_run_done: true }),
    })
    ElMessage.success('初始化完成')
    firstRunDialog.value = false
    await loadConfig()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    firstRunSaving.value = false
  }
}

async function loadGraph() {
  graphLoading.value = true
  try {
    const url = graphMerged.value ? '/api/graph/merged' : '/api/graph'
    graph.value = await api(url)
    selectedNode.value = null
    await nextTick()
    renderGraph()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    graphLoading.value = false
  }
}

async function saveConfig() {
  configSaving.value = true
  try {
    const payload = {
      ...configForm.value,
      wiki: {
        ...(configForm.value.wiki || {}),
        custom_categories: (configForm.value.wiki?.custom_categories || []).filter((item) => item.key && item.label),
      },
      agent: {
        ...(configForm.value.agent || {}),
        skills: (configForm.value.agent?.skills || []).filter((item) => item.name && item.description),
      },
    }
    const result = await api('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    config.value = result.config
    configForm.value = normalizeConfig(result.config)
    ElMessage.success('配置已保存')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    configSaving.value = false
  }
}

async function testModelConnection(role = 'llm') {
  const roleLabel = {
    llm: '文本模型',
    vision_model: '视觉模型',
    ocr_model: 'OCR 模型',
  }[role] || '模型'
  configTesting.value = { ...configTesting.value, [role]: true }
  try {
    const result = await api('/api/config/test-llm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role, [role]: configForm.value[role] }),
    })
    ElMessage.success(result.message || `${roleLabel}连接正常`)
  } catch (error) {
    ElMessage.error(`${roleLabel}测试失败：${error.message}`)
  } finally {
    configTesting.value = { ...configTesting.value, [role]: false }
  }
}



function handleNavItemClick(item) {
  if (item.key === 'knowledge') {
    toggleKnowledgeTree()
  } else if (item.key === 'new-note') {
    createNewNote()
  } else {
    setActiveView(item.key)
  }
}

// === 邀请码管理 ===
async function loadInvites() {
  try {
    const list = await api('/api/admin/invites')
    invitesList.value = Array.isArray(list) ? list : []
  } catch (error) {
    // admin 之外用户调用会 403，静默失败
    invitesList.value = []
  }
}

function openCreateInviteDialog() {
  createInviteDialog.value = { open: true, note: '' }
}

async function submitCreateInvite() {
  invitesCreating.value = true
  try {
    const invite = await api('/api/admin/invites', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note: createInviteDialog.value.note }),
    })
    ElMessage.success(`邀请码已生成：${invite.code}`)
    createInviteDialog.value.open = false
    await loadInvites()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    invitesCreating.value = false
  }
}

async function revokeInviteAction(code) {
  try {
    await api(`/api/admin/invites/${encodeURIComponent(code)}`, { method: 'DELETE' })
    ElMessage.success('已撤销')
    await loadInvites()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function copyInvite(code) {
  try {
    await navigator.clipboard.writeText(code)
    ElMessage.success(`已复制：${code}`)
  } catch (error) {
    ElMessage.warning(`复制失败，请手动复制：${code}`)
  }
}

function jumpToKnowledge(type) {
  knowledgeTreeExpanded.value = true
  pageFilter.value = type
  if (type !== 'all') {
    expandedFolders.value = {
      ...expandedFolders.value,
      [type]: true,
    }
  }
  setActiveView('knowledge')
  loadPages()
}

function toggleKnowledgeTree() {
  knowledgeTreeExpanded.value = !knowledgeTreeExpanded.value
  if (knowledgeTreeExpanded.value) {
    setActiveView('knowledge')
  }
}

function toggleBatch(batchId) {
  expandedBatchId.value = expandedBatchId.value === batchId ? null : batchId
}

function isBatchExpanded(batchId) {
  return expandedBatchId.value === batchId
}

function isFolderExpanded(type) {
  return Boolean(expandedFolders.value[type])
}

function toggleFolder(type) {
  expandedFolders.value = {
    ...expandedFolders.value,
    [type]: !expandedFolders.value[type],
  }
}

function syncExpandedFolders() {
  const next = {}
  for (const group of knowledgeFolders.value) {
    next[group.type] =
      expandedFolders.value[group.type] ??
      (pageFilter.value === 'all' ? group.type === knowledgeFolders.value[0]?.type : group.type === pageFilter.value)
  }
  expandedFolders.value = next
}

function openRecentBatch(batch) {
  setActiveView('ingest')
  expandedBatchId.value = batch.id
  openBatch(batch.id)
}

async function openQAFromHome(qa) {
  setActiveView('knowledge')
  pageFilter.value = 'outputs'
  await loadPages()
  // 直接打开预览
  try {
    selectedPage.value = await api(`/api/wiki/pages/${encodeURIComponent(qa.slug)}?type=outputs`)
    pageDrawer.value = true
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function openNoteFromHome(note) {
  setActiveView('knowledge')
  pageFilter.value = 'notes'
  await loadPages()
  try {
    selectedPage.value = await api(`/api/wiki/pages/${encodeURIComponent(note.slug)}?type=notes`)
    pageDrawer.value = true
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function openExplorerPage(page) {
  setActiveView(page.type === 'outputs' ? 'chat' : 'knowledge')
  openPagePreview(page)
}

function renderGraph() {
  const svgEl = graphSvgRef.value
  const rawNodes = graphVisibleNodes.value
  const rawEdges = graphVisibleEdges.value
  if (!svgEl) return
  if (!rawNodes.length) {
    d3.select(svgEl).selectAll('*').remove()
    selectedNode.value = null
    return
  }
  focusedNodeId.value = null
  graphNodeSelection = null
  graphLinkSelection = null
  graphEdgeLabelSelection = null
  const selectedStillVisible = rawNodes.some((node) => node.id === selectedNode.value?.id)
  if (!selectedStillVisible) selectedNode.value = null

  const viewport = graphViewportDimensions(rawNodes.length)
  const { width, height, padding } = viewport
  const nodes = rawNodes.map((node) => ({
    ...node,
    radius: graphNodeRadius(rawNodes.length),
  }))
  const nodeIds = new Set(nodes.map((node) => node.id))
  const links = rawEdges
    .filter((edge) => {
      const source = edge.source && typeof edge.source === 'object' ? edge.source.id : edge.source
      const target = edge.target && typeof edge.target === 'object' ? edge.target.id : edge.target
      return nodeIds.has(source) && nodeIds.has(target)
    })
    .map((edge) => ({ ...edge }))
  graphLastLayout = { width, height, padding, nodes }
  seedGraphPositions(nodes, links, width, height, padding)

  if (graphSimulation) {
    graphSimulation.stop()
    graphSimulation = null
  }

  const svg = d3.select(svgEl)
  svg.selectAll('*').remove()
  svg.attr('viewBox', `0 0 ${width} ${height}`)

  const defs = svg.append('defs')
  const backgroundGradient = defs.append('linearGradient').attr('id', 'graph-bg').attr('x1', '0%').attr('y1', '0%').attr('x2', '100%').attr('y2', '100%')
  backgroundGradient.append('stop').attr('offset', '0%').attr('stop-color', '#ffffff')
  backgroundGradient.append('stop').attr('offset', '100%').attr('stop-color', '#f3f6fa')

  const glow = defs.append('filter').attr('id', 'graph-glow').attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%')
  glow.append('feGaussianBlur').attr('stdDeviation', 3.5).attr('result', 'coloredBlur')
  const glowMerge = glow.append('feMerge')
  glowMerge.append('feMergeNode').attr('in', 'coloredBlur')
  glowMerge.append('feMergeNode').attr('in', 'SourceGraphic')

  graphLegend.forEach((item) => {
    const gradient = defs.append('radialGradient').attr('id', `node-gradient-${item.type}`)
    gradient.append('stop').attr('offset', '0%').attr('stop-color', '#ffffff').attr('stop-opacity', 0.98)
    gradient.append('stop').attr('offset', '42%').attr('stop-color', item.color).attr('stop-opacity', 0.84)
    gradient.append('stop').attr('offset', '100%').attr('stop-color', item.color).attr('stop-opacity', 1)
  })

  svg
    .append('rect')
    .attr('class', 'graph-backdrop')
    .attr('x', 0)
    .attr('y', 0)
    .attr('width', width)
    .attr('height', height)

  const grid = svg.append('g').attr('class', 'graph-grid')
  d3.range(0, width + 1, 46).forEach((x) => {
    grid.append('line').attr('x1', x).attr('y1', 0).attr('x2', x).attr('y2', height)
  })
  d3.range(0, height + 1, 46).forEach((y) => {
    grid.append('line').attr('x1', 0).attr('y1', y).attr('x2', width).attr('y2', y)
  })

  const stage = svg.append('g').attr('class', 'graph-stage')
  graphStageSelection = stage
  const zoom = d3
    .zoom()
    .scaleExtent([0.12, 4])
    .on('zoom', (event) => stage.attr('transform', event.transform))
  graphZoomBehavior = zoom
  svg.call(zoom)

  const targets = layoutTargets(nodes, graphLayout.value, width - padding * 2, height - padding * 2)
  targets.forEach((target) => {
    target.x += padding
    target.y += padding
  })
  const linkLayer = stage.append('g').attr('class', 'graph-link-layer')
  const nodeLayer = stage.append('g').attr('class', 'graph-node-layer')

  const link = linkLayer
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('class', 'graph-edge graph-edge-flow')
    .attr('stroke-width', (edge) => Math.max(1, edge.weight || 1))
  graphLinkSelection = link

  const linkLabel = linkLayer
    .selectAll('text')
    .data(nodes.length <= 140 ? links.filter((edge) => edge.label || edge.relation).slice(0, 120) : [])
    .join('text')
    .attr('class', 'graph-edge-label')
    .text((edge) => shortLabel(edge.label || edge.relation, 8))
  graphEdgeLabelSelection = linkLabel

  const node = nodeLayer
    .selectAll('g')
    .data(nodes)
    .join('g')
    .attr('class', 'graph-node')
    .classed('selected', (item) => item.id === selectedNode.value?.id)
    .on('click', (event, item) => {
      event.stopPropagation()
      focusNodeAndNeighbors(item.id)
    })
  graphNodeSelection = node
    .call(
      d3
        .drag()
        .on('start', (event, item) => {
          if (graphMotion.value && graphSimulation) graphSimulation.alphaTarget(0.25).restart()
          item.fx = item.x
          item.fy = item.y
        })
        .on('drag', (event, item) => {
          item.fx = event.x
          item.fy = event.y
        })
        .on('end', (_, item) => {
          if (graphMotion.value && graphSimulation) graphSimulation.alphaTarget(0)
          item.fx = null
          item.fy = null
        }),
    )

  node
    .append('circle')
    .attr('class', 'graph-halo')
    .attr('r', (item) => item.radius + 5)
    .attr('fill', (item) => nodeColor(item.type))

  node
    .append('circle')
    .attr('class', 'graph-core')
    .attr('r', (item) => item.radius)
    .attr('fill', (item) => nodeGradient(item.type))

  node
    .append('title')
    .text((item) => `${item.label}\n${typeLabel(item.type)} · 关联 ${item.linkCount || 0}`)

  if (graphLabels.value) {
    // 节点过多时只给"有连接"的节点贴标签，避免孤立点拥挤；用户可勾选取消标签彻底关闭
    const labelable = nodes.length > 200
      ? node.filter((item) => (item.linkCount || 0) > 0)
      : node
    labelable
      .append('text')
      .attr('y', (item) => item.radius + 18)
      .attr('text-anchor', 'middle')
      .text((item) => shortLabel(item.label, graphLabelLength(nodes.length)))
  }

  const simulation = d3
    .forceSimulation(nodes)
    .force('link', d3.forceLink(links).id((item) => item.id).distance((edge) => graphLinkDistance(nodes.length, edge)))
    .force('charge', d3.forceManyBody().strength(graphChargeStrength(nodes.length)))
    .force('center', d3.forceCenter(width / 2, height / 2).strength(0.02))
    .force('collide', d3.forceCollide().radius((item) => item.radius + graphCollisionGap(nodes.length)))

  if (graphLayout.value !== 'force') {
    simulation
      .force('x', d3.forceX((item) => targets.get(item.id)?.x || width / 2).strength(0.18))
      .force('y', d3.forceY((item) => targets.get(item.id)?.y || height / 2).strength(0.18))
  } else {
    simulation
      .force('x', d3.forceX(width / 2).strength(0.012))
      .force('y', d3.forceY(height / 2).strength(0.012))
  }

  const ticked = () => {
    link
      .attr('x1', (edge) => edge.source.x)
      .attr('y1', (edge) => edge.source.y)
      .attr('x2', (edge) => edge.target.x)
      .attr('y2', (edge) => edge.target.y)
    linkLabel
      .attr('x', (edge) => ((edge.source.x || 0) + (edge.target.x || 0)) / 2)
      .attr('y', (edge) => ((edge.source.y || 0) + (edge.target.y || 0)) / 2)
    node.attr('transform', (item) => `translate(${item.x}, ${item.y})`)
  }

  simulation.on('tick', ticked)
  graphSimulation = simulation

  const warmupTicks = nodes.length > 250 ? 260 : nodes.length > 120 ? 220 : 170
  if (!graphMotion.value || nodes.length > 180) {
    simulation.stop()
    for (let i = 0; i < warmupTicks; i += 1) simulation.tick()
    ticked()
  } else {
    simulation.alpha(0.8).restart()
  }
  if (selectedNode.value?.id) {
    const selectedId = selectedNode.value.id
    applyFocus(selectedId)
    requestAnimationFrame(() => centerClickedNodeNeighborhood(selectedId))
  } else {
    requestAnimationFrame(() => fitGraphToViewport())
  }
}

function scheduleRenderGraph() {
  window.clearTimeout(graphRenderTimer)
  graphRenderTimer = window.setTimeout(() => {
    renderGraph()
  }, 160)
}

function graphViewportDimensions(count) {
  const rect = graphCanvasRef.value?.getBoundingClientRect()
  const visibleWidth = Math.max(720, Math.floor(rect?.width || 1100))
  const visibleHeight = Math.max(560, Math.floor(rect?.height || 700))
  const spread = Math.max(1, Math.sqrt(Math.max(count, 1) / 32))
  const padding = count > 180 ? 320 : count > 90 ? 280 : 220
  return {
    width: Math.round(Math.max(visibleWidth * 1.18, visibleWidth * Math.min(4.6, spread * 1.9))),
    height: Math.round(Math.max(visibleHeight * 1.12, visibleHeight * Math.min(3.8, spread * 1.55))),
    padding,
  }
}

function graphLinkDistance(count, edge) {
  const base = count > 240 ? 150 : count > 120 ? 132 : 108
  return base + Math.min(28, (edge.weight || 1) * 4)
}

function graphNodeRadius(count) {
  return count > 180 ? 6 : 7
}

function graphChargeStrength(count) {
  if (graphLayout.value !== 'force') return count > 160 ? -80 : -65
  if (count > 260) return -230
  if (count > 140) return -190
  if (count > 80) return -150
  return -120
}

function graphCollisionGap(count) {
  if (count > 220) return 34
  if (count > 120) return 28
  return 22
}

function graphLabelLength(count) {
  if (count > 90) return 6
  if (count > 55) return 8
  return 10
}

function seedGraphPositions(nodes, links, width, height, padding) {
  const connected = new Set()
  links.forEach((edge) => {
    const source = edge.source && typeof edge.source === 'object' ? edge.source.id : edge.source
    const target = edge.target && typeof edge.target === 'object' ? edge.target.id : edge.target
    connected.add(source)
    connected.add(target)
  })
  const innerWidth = Math.max(320, width - padding * 2)
  const innerHeight = Math.max(260, height - padding * 2)
  const columns = Math.max(4, Math.ceil(Math.sqrt(nodes.length * (innerWidth / innerHeight))))
  nodes.forEach((node, index) => {
    const row = Math.floor(index / columns)
    const col = index % columns
    const jitter = connected.has(node.id) ? 18 : 6
    node.x = padding + ((col + 0.5) * innerWidth) / columns + Math.sin(index * 12.9898) * jitter
    node.y = padding + ((row + 0.5) * innerHeight) / Math.ceil(nodes.length / columns) + Math.cos(index * 78.233) * jitter
  })
}

function applyFocus(nodeId) {
  if (!graphNodeSelection || !graphLinkSelection) return
  if (!nodeId) {
    graphNodeSelection.classed('graph-dimmed', false)
    graphLinkSelection.classed('graph-dimmed', false)
    if (graphEdgeLabelSelection) graphEdgeLabelSelection.classed('graph-dimmed', false)
    return
  }
  const visible = graphAdjacencyMap.value.get(nodeId)?.nodes || new Set([nodeId])
  graphNodeSelection.classed('graph-dimmed', (d) => !visible.has(d.id))
  graphLinkSelection.classed('graph-dimmed', (d) => {
    const s = d.source && typeof d.source === 'object' ? d.source.id : d.source
    const t = d.target && typeof d.target === 'object' ? d.target.id : d.target
    return !(visible.has(s) && visible.has(t))
  })
  if (graphEdgeLabelSelection) {
    graphEdgeLabelSelection.classed('graph-dimmed', (d) => {
      const s = d.source && typeof d.source === 'object' ? d.source.id : d.source
      const t = d.target && typeof d.target === 'object' ? d.target.id : d.target
      return !(visible.has(s) && visible.has(t))
    })
  }
}

function resetFocus() {
  focusedNodeId.value = null
  selectedNode.value = null
  applyFocus(null)
  resetGraphZoom()
}

function focusNodeById(nodeId) {
  focusNodeAndNeighbors(nodeId)
}

function focusNodeAndNeighbors(nodeId) {
  const node =
    graphLastLayout.nodes.find((item) => item.id === nodeId) ||
    graphVisibleNodeMap.value.get(nodeId) ||
    (graph.value.nodes || []).find((item) => item.id === nodeId)
  if (!node) return
  selectedNode.value = node
  focusedNodeId.value = node.id
  if (graphNodeSelection) {
    graphNodeSelection.classed('selected', (candidate) => candidate.id === node.id)
  }
  applyFocus(node.id)
  centerClickedNodeNeighborhood(node.id)
}

function centerClickedNodeNeighborhood(nodeId) {
  if (!graphSvgRef.value || !graphZoomBehavior) return
  const focusIds = new Set(graphAdjacencyMap.value.get(nodeId)?.nodes || [nodeId])
  focusIds.add(nodeId)
  const positioned = graphLastLayout.nodes.filter((node) => focusIds.has(node.id) && Number.isFinite(node.x) && Number.isFinite(node.y))
  if (!positioned.length) return
  const pad = positioned.length > 12 ? 140 : 96
  const minX = d3.min(positioned, (node) => node.x - (node.radius || 16)) - pad
  const maxX = d3.max(positioned, (node) => node.x + (node.radius || 16)) + pad
  const minY = d3.min(positioned, (node) => node.y - (node.radius || 16)) - pad
  const maxY = d3.max(positioned, (node) => node.y + (node.radius || 16)) + pad
  const boxWidth = Math.max(160, maxX - minX)
  const boxHeight = Math.max(160, maxY - minY)
  const { width, height } = graphLastLayout
  const scale = clamp(Math.min((width * 0.68) / boxWidth, (height * 0.68) / boxHeight), 0.28, 2.8)
  const centerX = (minX + maxX) / 2
  const centerY = (minY + maxY) / 2
  const transform = d3.zoomIdentity
    .translate(width / 2 - centerX * scale, height / 2 - centerY * scale)
    .scale(scale)
  d3.select(graphSvgRef.value).transition().duration(420).call(graphZoomBehavior.transform, transform)
}

function fitGraphToViewport() {
  if (!graphSvgRef.value || !graphZoomBehavior || !graphLastLayout.nodes.length) return
  const positioned = graphLastLayout.nodes.filter((node) => Number.isFinite(node.x) && Number.isFinite(node.y))
  if (!positioned.length) return
  const pad = 120
  const minX = d3.min(positioned, (node) => node.x - (node.radius || 12)) - pad
  const maxX = d3.max(positioned, (node) => node.x + (node.radius || 12)) + pad
  const minY = d3.min(positioned, (node) => node.y - (node.radius || 12)) - pad
  const maxY = d3.max(positioned, (node) => node.y + (node.radius || 12)) + pad
  const boxWidth = Math.max(240, maxX - minX)
  const boxHeight = Math.max(240, maxY - minY)
  const { width, height } = graphLastLayout
  const scale = clamp(Math.min((width * 0.9) / boxWidth, (height * 0.9) / boxHeight), 0.14, 1.2)
  const centerX = (minX + maxX) / 2
  const centerY = (minY + maxY) / 2
  const transform = d3.zoomIdentity
    .translate(width / 2 - centerX * scale, height / 2 - centerY * scale)
    .scale(scale)
  d3.select(graphSvgRef.value).transition().duration(260).call(graphZoomBehavior.transform, transform)
}

function clearGraphFilters() {
  graphSearch.value = ''
  graphTypeFilter.value = 'all'
  graphShowRelations.value = true
  nextTick(scheduleRenderGraph)
}

function nudgeGraphZoom(scale) {
  if (!graphSvgRef.value || !graphZoomBehavior) return
  d3.select(graphSvgRef.value).transition().duration(180).call(graphZoomBehavior.scaleBy, scale)
}

function resetGraphZoom() {
  if (!graphSvgRef.value || !graphZoomBehavior) return
  fitGraphToViewport()
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value || 0))
}

function handleFileChange(_, files) {
  fileList.value = files
  if (files.length <= uploadPreviewLimit) {
    uploadFilesExpanded.value = false
  }
}

function handleFileRemove(_, files) {
  fileList.value = files
}

function removeQueuedFile(item) {
  fileList.value = fileList.value.filter((file) => {
    if (item.uid && file.uid) return file.uid !== item.uid
    return file.name !== item.name
  })
  if (fileList.value.length <= uploadPreviewLimit) {
    uploadFilesExpanded.value = false
  }
}

function clearQueuedFiles() {
  fileList.value = []
  uploadFilesExpanded.value = false
}

async function uploadFiles() {
  if (!fileList.value.length) return
  uploading.value = true
  currentBatch.value = { status: 'running' }
  const form = new FormData()
  fileList.value.forEach((item) => {
    form.append('files', item.raw)
  })

  try {
    const result = await api('/api/ingest/upload', {
      method: 'POST',
      body: form,
    })
    currentBatch.value = result
    fileList.value = []
    uploadFilesExpanded.value = false
    ElMessage.success('入库完成')
    await loadSchemaCategories()
    await refreshAll()
    await openBatch(result.id)
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    uploading.value = false
  }
}

async function openBatch(batchId) {
  selectedBatch.value = await api(`/api/ingest/batches/${batchId}`)
  batchDrawer.value = true
}

async function openBatchSourceFolder(batch) {
  if (!batch?.id) return
  try {
    await api(`/api/ingest/batches/${encodeURIComponent(batch.id)}/open-source-folder`, { method: 'POST' })
    ElMessage.success('已打开源文件夹')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function toggleBatchSelection(batchId) {
  const selected = new Set(selectedBatchIds.value)
  if (selected.has(batchId)) {
    selected.delete(batchId)
  } else {
    selected.add(batchId)
  }
  selectedBatchIds.value = Array.from(selected)
}

function togglePagedBatchSelection(checked) {
  const selected = new Set(selectedBatchIds.value)
  pagedBatches.value.forEach((batch) => {
    if (checked) {
      selected.add(batch.id)
    } else {
      selected.delete(batch.id)
    }
  })
  selectedBatchIds.value = Array.from(selected)
}

async function deleteBatch(batch) {
  if (!batch?.id) return
  try {
    await ElMessageBox.confirm(
      `确认删除批次记录「${summarizeBatchTitle(batch)}」？不会删除已生成知识页和原始材料。`,
      '删除批次',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  deletingBatches.value = true
  try {
    await api(`/api/ingest/batches/${encodeURIComponent(batch.id)}`, { method: 'DELETE' })
    ElMessage.success('已删除批次记录')
    selectedBatchIds.value = selectedBatchIds.value.filter((id) => id !== batch.id)
    if (selectedBatch.value?.id === batch.id) {
      selectedBatch.value = null
      batchDrawer.value = false
    }
    await refreshAfterBatchDelete()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    deletingBatches.value = false
  }
}

async function deleteSelectedBatches() {
  if (!selectedBatchIds.value.length) return
  await deleteBatchIds(selectedBatchIds.value, `确认删除选中的 ${selectedBatchIds.value.length} 条批次记录？不会删除已生成知识页和原始材料。`)
}

async function deleteAllBatches() {
  if (!batches.value.length) return
  await deleteBatchIds(batches.value.map((batch) => batch.id), `确认一键清空全部 ${batches.value.length} 条批次记录？不会删除已生成知识页和原始材料。`)
}

async function deleteBatchIds(ids, message) {
  const uniqueIds = Array.from(new Set(ids)).filter(Boolean)
  if (!uniqueIds.length) return
  try {
    await ElMessageBox.confirm(message, '批量删除批次', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  deletingBatches.value = true
  try {
    const result = await api('/api/ingest/batches', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: uniqueIds }),
    })
    ElMessage.success(`已删除 ${result.count || uniqueIds.length} 条批次记录`)
    selectedBatchIds.value = selectedBatchIds.value.filter((id) => !uniqueIds.includes(id))
    if (selectedBatch.value?.id && uniqueIds.includes(selectedBatch.value.id)) {
      selectedBatch.value = null
      batchDrawer.value = false
    }
    await refreshAfterBatchDelete()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    deletingBatches.value = false
  }
}

async function refreshAfterBatchDelete() {
  await Promise.all([loadBatches(), loadHome()])
  if (activeView.value === 'graph') {
    await loadGraph()
  }
}

async function openPagePreview(page) {
  selectedPage.value = await api(`/api/wiki/pages/${encodeURIComponent(page.slug)}?type=${page.type}`)
  pageEditMode.value = false
  pageDrawer.value = true
}

async function createNewNote() {
  const ts = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  noteForm.value = {
    title: `新建笔记 ${ts.getFullYear()}-${pad(ts.getMonth() + 1)}-${pad(ts.getDate())} ${pad(ts.getHours())}:${pad(ts.getMinutes())}`,
    url: '',
    content: '',
    tagsText: '',
  }
  noteDialog.value = true
}

async function extractNoteUrl() {
  const url = noteForm.value.url.trim()
  if (!url || noteUrlExtracting.value) return
  noteUrlExtracting.value = true
  try {
    const result = await api('/api/web/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    })
    if (result.title && /^新建笔记\s/.test(noteForm.value.title)) {
      noteForm.value.title = result.title
    }
    const extracted = result.content || ''
    noteForm.value.content = noteForm.value.content.trim()
      ? `${noteForm.value.content.trim()}\n\n${extracted}`
      : extracted
    ElMessage.success('网页内容已提取')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    noteUrlExtracting.value = false
  }
}

async function submitCreateNote() {
  noteSubmitting.value = true
  try {
    const tags = noteForm.value.tagsText
      .split(/[,，]/)
      .map((item) => item.trim())
      .filter(Boolean)
    const result = await api('/api/notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: noteForm.value.title,
        content: noteForm.value.content,
        tags,
        source_url: noteForm.value.url.trim(),
        deep_extract: Boolean(noteForm.value.url.trim()),
      }),
    })
    noteDialog.value = false
    setActiveView('knowledge')
    await loadPages()
    selectedPage.value = await api(`/api/wiki/pages/${encodeURIComponent(result.slug)}?type=notes`)
    pageEditMode.value = false
    pageDrawer.value = true
    if (graph.value.nodes.length || activeView.value === 'graph') {
      await loadGraph()
    }
    const deepCount = result.deep_extract?.generated_files?.length || 0
    ElMessage.success(
      deepCount
        ? `笔记已创建，深度抽取 ${deepCount} 个知识页`
        : `笔记已创建，抽取 ${result.relations?.length || 0} 条关系`,
    )
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    noteSubmitting.value = false
  }
}

function startEditPage() {
  if (!selectedPage.value) return
  pageEditDraft.value = {
    title: selectedPage.value.meta?.title || selectedPage.value.slug,
    body: selectedPage.value.body || '',
  }
  pageEditMode.value = true
}

function cancelEditPage() {
  pageEditMode.value = false
}

async function saveEditPage() {
  if (!selectedPage.value) return
  pageSaving.value = true
  try {
    const meta = { ...(selectedPage.value.meta || {}), title: pageEditDraft.value.title }
    await api(`/api/wiki/pages/${encodeURIComponent(selectedPage.value.slug)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: selectedPage.value.type,
        meta,
        body: pageEditDraft.value.body,
      }),
    })
    selectedPage.value = await api(
      `/api/wiki/pages/${encodeURIComponent(selectedPage.value.slug)}?type=${selectedPage.value.type}`,
    )
    pageEditMode.value = false
    ElMessage.success('已保存')
    await loadPages()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    pageSaving.value = false
  }
}

async function deletePage(page) {
  try {
    await api(`/api/wiki/pages/${encodeURIComponent(page.slug)}?type=${page.type}`, { method: 'DELETE' })
    ElMessage.success(`已删除 ${page.title || page.slug}`)
    await loadPages()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function togglePageSelection(page) {
  const key = pageKey(page)
  const idx = selectedPageKeys.value.indexOf(key)
  if (idx >= 0) {
    selectedPageKeys.value.splice(idx, 1)
  } else {
    selectedPageKeys.value.push(key)
  }
}

function toggleSelectCurrentPage() {
  const keysOnPage = pagedPages.value.map(pageKey)
  if (currentPageAllSelected.value) {
    const set = new Set(keysOnPage)
    selectedPageKeys.value = selectedPageKeys.value.filter((k) => !set.has(k))
  } else {
    const merged = new Set([...selectedPageKeys.value, ...keysOnPage])
    selectedPageKeys.value = [...merged]
  }
}

async function deleteSelectedPages() {
  if (!selectedPageKeys.value.length) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedPageKeys.value.length} 个页面?(只删 markdown 文件,索引和反向链接不会自动清理)`,
      '批量删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  const keys = new Set(selectedPageKeys.value)
  const targets = pages.value.filter((p) => keys.has(pageKey(p)))
  const results = await Promise.allSettled(
    targets.map((p) =>
      api(`/api/wiki/pages/${encodeURIComponent(p.slug)}?type=${p.type}`, { method: 'DELETE' }),
    ),
  )
  const okCount = results.filter((r) => r.status === 'fulfilled').length
  const failCount = results.length - okCount
  if (failCount === 0) {
    ElMessage.success(`已删除 ${okCount} 个页面`)
  } else {
    ElMessage.warning(`成功 ${okCount} 个,失败 ${failCount} 个`)
  }
  selectedPageKeys.value = []
  await loadPages()
}

async function openPageBySlug(slug) {
  try {
    selectedPage.value = await api(`/api/wiki/pages/${encodeURIComponent(slug)}`)
    pageDrawer.value = true
  } catch (error) {
    ElMessage.warning(`未找到页面：${slug}`)
  }
}

async function openChatSource(source) {
  if (!source?.slug || !source?.type) return
  setActiveView(source.type === 'outputs' ? 'chat' : 'knowledge')
  pageFilter.value = source.type
  await openPagePreview(source)
}

function handleMarkdownClick(event) {
  const target = event.target
  if (target?.classList?.contains('wiki-link')) {
    const slug = target.getAttribute('data-slug')
    if (slug) openPageBySlug(slug)
  }
}

async function rollbackBatch(batch) {
  await ElMessageBox.confirm('将撤回本次生成的知识页面和检索条目，原始材料会保留。', '回滚本次入库', {
    confirmButtonText: '回滚',
    cancelButtonText: '取消',
    type: 'warning',
  })
  const result = await api(`/api/ingest/batches/${batch.id}/rollback`, { method: 'POST' })
  ElMessage.success('已回滚')
  selectedBatch.value = result
  await loadSchemaCategories()
  await refreshAll()
}

async function reparseBatch(batch) {
  if (!batch?.id || reparsingBatchSet.value.has(batch.id)) return
  reparsingBatchIds.value = [...reparsingBatchIds.value, batch.id]
  try {
    const result = await api(`/api/ingest/batches/${encodeURIComponent(batch.id)}/reparse`, { method: 'POST' })
    ElMessage.success(`再次解析完成：已合并 ${result.generated_files?.length || 0} 个知识页、${result.entities?.length || 0} 个实体`)
    if (selectedBatch.value?.id === batch.id) {
      selectedBatch.value = result
    }
    await Promise.all([loadBatches(), loadPages(), loadHome()])
    if (activeView.value === 'graph') {
      await loadGraph()
    }
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    reparsingBatchIds.value = reparsingBatchIds.value.filter((id) => id !== batch.id)
  }
}

async function sendChat() {
  const query = chatInput.value.trim()
  if (!query) return
  const id = Date.now()
  messages.value.push({ id, role: 'user', content: query })
  chatInput.value = ''
  chatLoading.value = true
  try {
    const result = await api('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    })
    messages.value.push({
      id: id + 1,
      role: 'assistant',
      content: result.response,
      sources: normalizeKnowledgeSources(result.sources),
    })
    await loadPages()
  } catch (error) {
    messages.value.push({ id: id + 1, role: 'assistant', content: `查询失败：${error.message}` })
  } finally {
    chatLoading.value = false
  }
}

async function runLint() {
  lintLoading.value = true
  try {
    lint.value = await api('/api/lint')
    ElMessage.success('体检完成')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    lintLoading.value = false
  }
}

function openLintFix(category) {
  const defaultAction = {
    broken_links: 'remove',
    orphan_pages: 'enrich',
    stale_pages: 'touch',
    placeholder_pages: 'enrich',
  }[category]
  const source = (lint.value[category] || []).map((row) => ({ ...row, action: defaultAction }))
  lintFixDialog.value = { open: true, category, items: source, selected: [] }
  lintFixBulkAction.value = defaultAction
}

function onLintFixSelectionChange(rows) {
  lintFixDialog.value.selected = rows
}

function syncLintFixBulkAction() {
  const actions = [...new Set(lintFixDialog.value.items.map((item) => item.action).filter(Boolean))]
  lintFixBulkAction.value = actions.length === 1 ? actions[0] : ''
}

function applyLintFixBulkAction(action) {
  if (!action) return
  lintFixDialog.value.items.forEach((item) => {
    item.action = action
  })
}

async function submitLintFix() {
  const { category, selected } = lintFixDialog.value
  if (!selected.length) return
  lintFixSubmitting.value = true
  try {
    const result = await api('/api/lint/fix', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category, items: selected }),
    })
    const okCount = result.succeeded?.length || 0
    const failCount = result.failed?.length || 0
    if (failCount === 0) {
      ElMessage.success(`修复完成,共处理 ${okCount} 项`)
    } else {
      ElMessage.warning(`成功 ${okCount} 项,失败 ${failCount} 项`)
    }
    lintFixDialog.value.open = false
    await runLint()
    await loadPages()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    lintFixSubmitting.value = false
  }
}

function statusLabel(status) {
  return {
    running: '处理中',
    completed: '已完成',
    completed_with_errors: '有异常',
    completed_with_warnings: '已入库待精炼',
    failed: '失败',
    rolled_back: '已回滚',
  }[status] || status || '未知'
}

function statusType(status) {
  return {
    completed: 'success',
    completed_with_warnings: 'warning',
    completed_with_errors: 'warning',
    failed: 'danger',
    rolled_back: 'info',
  }[status] || 'primary'
}

function batchProgress(batch) {
  const total = batch?.file_names?.length || batch?.original_files?.length || 0
  if (!total) return { done: 0, total: 0 }
  const generatedFromFiles = batch?.generated_files?.length || 0
  const generatedFromLogs = (batch?.log || []).filter((entry) => String(entry.message || '').includes('已生成知识页面')).length
  const done = Math.min(total, Math.max(generatedFromFiles, generatedFromLogs))
  return { done, total }
}

function batchStatusLabel(batch) {
  if (!batch) return '未知'
  if (batch.status === 'running') {
    const progress = batchProgress(batch)
    if (progress.total) {
      return `处理中 ${progress.done}/${progress.total}`
    }
  }
  return statusLabel(batch.status)
}

function batchStatusType(batch) {
  return statusType(batch?.status)
}

function agentStateLabel(state) {
  return {
    idle: '空闲',
    archiving: '保存材料',
    parsing: '解析文档',
    analyzing: '分析材料',
    generating: '生成知识页',
    linking: '建立关联',
    error: '异常',
    offline: '状态不可用',
  }[state] || state || '空闲'
}

function typeLabel(type) {
  const builtIn = {
    cases: '案件',
    persons: '人员',
    locations: '地点',
    laws: '法规',
    techniques: '技战法',
    notes: '笔记',
    summaries: '研判',
    outputs: '问答记忆',
  }
  if (builtIn[type]) return builtIn[type]
  const custom = categoryOptions.value.find((item) => item.key === type)
  return custom?.label || type
}

function nodeColor(type) {
  return {
    cases: '#3478f6',
    persons: '#2f9bff',
    locations: '#36b3d8',
    laws: '#ff8a1f',
    techniques: '#e95664',
    notes: '#7b8ba5',
    outputs: '#7b8ba5',
    summaries: '#4b79c9',
  }[type] || '#6f90bc'
}

function nodeGradient(type) {
  const known = graphLegend.some((item) => item.type === type)
  return known ? `url(#node-gradient-${type})` : nodeColor(type)
}

function selectedNodeIcon(type) {
  if (type === 'persons') return User
  if (type === 'locations') return Connection
  if (type === 'cases') return FolderOpened
  if (type === 'laws') return Key
  return Document
}

function shortLabel(label, size = 10) {
  const text = label || ''
  return text.length > size ? `${text.slice(0, size)}…` : text
}

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

// 收集当前 wiki 库里所有可作为内联链接目标的实体（名字+slug）。
// 排除当前正在预览的页面与"输出"类页面，去重，按名字长度倒序，方便最长匹配优先。
function collectLinkableEntities() {
  const currentSlug = selectedPage.value?.slug
  const seen = new Set()
  const out = []
  for (const p of pages.value || []) {
    if (!p || !p.slug) continue
    if (p.slug === currentSlug) continue
    if (p.type === 'outputs') continue
    const name = String(p.title || p.slug).trim()
    if (!name || name.length < 2) continue
    if (seen.has(name)) continue
    seen.add(name)
    out.push({ name, slug: p.slug })
  }
  out.sort((a, b) => b.name.length - a.name.length)
  return out
}

// 在已转义的 HTML 片段中自动给已知实体名包上 wiki-link 按钮，
// 跳过已有的 <button class="wiki-link"> 块与 HTML 实体（&amp; 等），
// 以避免产生嵌套链接或破坏字符引用。
function autolinkEntities(htmlSegment, entities) {
  if (!htmlSegment || !entities.length) return htmlSegment
  const escMap = new Map()
  for (const { name, slug } of entities) {
    const esc = escapeHtml(name)
    if (!escMap.has(esc)) {
      escMap.set(esc, { slug: escapeHtml(slug), display: esc })
    }
  }
  const escNames = Array.from(escMap.keys()).sort((a, b) => b.length - a.length)
  const BUTTON_OPEN = '<button class="wiki-link"'
  const BUTTON_CLOSE = '</button>'
  const result = []
  let i = 0
  const len = htmlSegment.length
  while (i < len) {
    if (htmlSegment.startsWith(BUTTON_OPEN, i)) {
      const closeIdx = htmlSegment.indexOf(BUTTON_CLOSE, i)
      if (closeIdx !== -1) {
        const end = closeIdx + BUTTON_CLOSE.length
        result.push(htmlSegment.slice(i, end))
        i = end
        continue
      }
    }
    if (htmlSegment[i] === '&') {
      const semi = htmlSegment.indexOf(';', i)
      if (semi !== -1 && semi - i < 10) {
        result.push(htmlSegment.slice(i, semi + 1))
        i = semi + 1
        continue
      }
    }
    let matched = false
    for (const escName of escNames) {
      if (htmlSegment.startsWith(escName, i)) {
        const { slug, display } = escMap.get(escName)
        result.push(`<button class="wiki-link" data-slug="${slug}">${display}</button>`)
        i += escName.length
        matched = true
        break
      }
    }
    if (!matched) {
      result.push(htmlSegment[i])
      i++
    }
  }
  return result.join('')
}

function renderMarkdownPreview(markdown) {
  const linkables = collectLinkableEntities()
  const lines = String(markdown || '').split('\n')
  const html = lines
    .map((line) => {
      let escaped = escapeHtml(line)
        .replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, '<button class="wiki-link" data-slug="$1">$2</button>')
        .replace(/\[\[([^\]]+)\]\]/g, '<button class="wiki-link" data-slug="$1">$1</button>')
      escaped = autolinkEntities(escaped, linkables)
      if (escaped.startsWith('### ')) return `<h3>${escaped.slice(4)}</h3>`
      if (escaped.startsWith('## ')) return `<h2>${escaped.slice(3)}</h2>`
      if (escaped.startsWith('# ')) return `<h1>${escaped.slice(2)}</h1>`
      if (escaped.startsWith('- ')) return `<li>${escaped.slice(2)}</li>`
      if (!escaped.trim()) return '<br />'
      return `<p>${escaped}</p>`
    })
    .join('')
  return html
}

function defaultConfig() {
  const modelDefaults = {
    provider: '',
    model: '',
    base_url: '',
    api_key: '',
    temperature: 0.1,
    max_tokens: 8000,
    thinking: false,
    reasoning_effort: 'high',
  }
  return {
    llm: {
      ...modelDefaults,
      provider: 'dashscope',
    },
    vision_model: { ...modelDefaults },
    ocr_model: { ...modelDefaults },
    agent: {
      skills: [
        { enabled: true, name: 'OCR 预检', description: '识别图片、扫描 PDF、正文为空的材料', trigger: '图片/扫描PDF/解析为空' },
        { enabled: true, name: '实体分类', description: '根据 schema 和自定义目录选择实体类型', trigger: '入库生成 wiki 页面' },
      ],
    },
    ingest: {
      max_workers: 5,
    },
    watcher: {
      inbox_dir: 'raw/inbox',
    },
    wiki: {
      custom_categories: [],
    },
    server: {
      host: '0.0.0.0',
      port: 5004,
    },
    raw_dir: '',
    first_run_done: false,
  }
}

function normalizeConfig(raw) {
  const defaults = defaultConfig()
  return {
    ...defaults,
    ...raw,
    llm: { ...defaults.llm, ...(raw?.llm || {}) },
    vision_model: { ...defaults.vision_model, ...(raw?.vision_model || {}) },
    ocr_model: { ...defaults.ocr_model, ...(raw?.ocr_model || {}) },
    agent: {
      ...defaults.agent,
      ...(raw?.agent || {}),
      skills: Array.isArray(raw?.agent?.skills)
        ? raw.agent.skills.map((item) => ({
            enabled: item?.enabled !== false,
            name: String(item?.name || '').trim(),
            description: String(item?.description || '').trim(),
            trigger: String(item?.trigger || '').trim(),
          }))
        : defaults.agent.skills,
    },
    ingest: { ...defaults.ingest, ...(raw?.ingest || {}) },
    watcher: { ...defaults.watcher, ...(raw?.watcher || {}) },
    wiki: {
      ...defaults.wiki,
      ...(raw?.wiki || {}),
      custom_categories: Array.isArray(raw?.wiki?.custom_categories)
        ? raw.wiki.custom_categories.map((item) => ({
            key: String(item?.key || item?.name || '').trim(),
            label: String(item?.label || item?.name || item?.key || '').trim(),
          }))
        : [],
    },
    server: { ...defaults.server, ...(raw?.server || {}) },
  }
}

function addCustomCategory() {
  setActiveView('config')
  configForm.value.wiki.custom_categories.push({ key: '', label: '' })
}

async function confirmCustomCategory(index) {
  const category = configForm.value.wiki.custom_categories[index]
  if (!category?.key?.trim() || !category?.label?.trim()) {
    ElMessage.warning('请填写目录键和显示名称')
    return
  }
  await saveConfig()
  await loadPages()
  knowledgeTreeExpanded.value = true
  ElMessage.success('知识分类已确认，schema 已同步更新')
}

function removeCustomCategory(index) {
  configForm.value.wiki.custom_categories.splice(index, 1)
}

function addSkill() {
  configForm.value.agent.skills.push({ enabled: true, name: '', description: '', trigger: '' })
}

function removeSkill(index) {
  configForm.value.agent.skills.splice(index, 1)
}

function formatTime(value) {
  if (!value) return ''
  return String(value).replace('T', ' ').slice(0, 19)
}

function formatFileSize(bytes) {
  const value = Number(bytes || 0)
  if (!value) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = value
  let unit = 0
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024
    unit += 1
  }
  return `${size >= 10 || unit === 0 ? Math.round(size) : size.toFixed(1)} ${units[unit]}`
}

function shortenName(name, max = 22) {
  const text = String(name || '')
  return text.length > max ? `${text.slice(0, max)}…` : text
}

function summarizeBatchTitle(batch) {
  const names = batch?.file_names || []
  if (!names.length) return batch?.id || '未命名批次'
  if (names.length === 1) return names[0]
  if (names.length === 2) return `${shortenName(names[0], 18)}、${shortenName(names[1], 18)}`
  return `${shortenName(names[0], 18)}、${shortenName(names[1], 18)} 等 ${names.length} 份材料`
}

function startBatchPolling() {
  if (batchRefreshTimer || authState.value !== 'authed') return
  batchRefreshTimer = window.setInterval(async () => {
    if (authState.value !== 'authed') {
      stopBatchPolling()
      return
    }
    if (activeView.value !== 'home' && activeView.value !== 'ingest' && !batchDrawer.value) return
    try {
      await loadBatches()
    } catch {
      stopBatchPolling()
    }
  }, 5000)
}

function startAgentStatusPolling() {
  if (agentStatusTimer || authState.value !== 'authed') return
  agentStatusTimer = window.setInterval(loadAgentStatus, 3000)
}

function stopAgentStatusPolling() {
  if (!agentStatusTimer) return
  window.clearInterval(agentStatusTimer)
  agentStatusTimer = null
}

function stopBatchPolling() {
  if (!batchRefreshTimer) return
  window.clearInterval(batchRefreshTimer)
  batchRefreshTimer = null
}

watch(activeView, (view) => {
  if (view === 'graph') nextTick(scheduleRenderGraph)
  if (view === 'home' || view === 'ingest' || batchDrawer.value || hasRunningBatches.value) {
    startBatchPolling()
  }
})

watch(hasRunningBatches, (running) => {
  if (running) startBatchPolling()
})

watch(batchPageSize, () => {
  batchPage.value = 1
})

function handleGraphResize() {
  if (activeView.value === 'graph') scheduleRenderGraph()
}

onMounted(() => {
  checkAuth()
  window.addEventListener('resize', handleGraphResize)
})

onBeforeUnmount(() => {
  if (graphSimulation) graphSimulation.stop()
  window.clearTimeout(graphRenderTimer)
  window.removeEventListener('resize', handleGraphResize)
  stopBatchPolling()
  stopAgentStatusPolling()
})

// === 知识维护抽屉（P3：孤立实体 + Schema 合成） ===
const maintenanceDrawer = ref(false)
const maintenanceTab = ref('connection')
const orphansLoading = ref(false)
const orphansFilling = ref(false)
const orphansResult = ref({})
const synthForm = ref({ goal: '', objectsRaw: '' })
const synthLoading = ref(false)
const synthApplying = ref(false)
const synthResult = ref({})

const synthYamlPreview = computed(() => {
  if (!synthResult.value.schema) return ''
  try { return JSON.stringify(synthResult.value.schema, null, 2) } catch { return '' }
})

function openMaintenance() { maintenanceDrawer.value = true }
window.__mjq_open_maintenance = openMaintenance  // 临时入口（P3 没接菜单时用 console 也能打开）

async function scanOrphans() {
  orphansLoading.value = true
  try {
    orphansResult.value = await api('/api/orphans/scan')
  } catch (e) { ElMessage.error(e.message) }
  finally { orphansLoading.value = false }
}

async function autoFillOrphans() {
  await ElMessageBox.confirm(
    `将为 ${orphansResult.value.dangling?.length || 0} 个 dangling 链接生成占位页。LLM 调用可能产生费用。`,
    '确认',
    { confirmButtonText: '继续', cancelButtonText: '取消' },
  ).catch(() => null)
  if (!maintenanceDrawer.value) return
  orphansFilling.value = true
  try {
    const res = await api('/api/orphans/dangling/auto-fill', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ use_llm: true }),
    })
    ElMessage.success(`已建占位页 ${res.created.length} 个，跳过 ${res.skipped.length} 个`)
    await scanOrphans()
  } catch (e) { ElMessage.error(e.message) }
  finally { orphansFilling.value = false }
}

async function refreshOrphansIndex() {
  try {
    const res = await api('/api/orphans/index/refresh', { method: 'POST' })
    ElMessage.success(`已写入索引（孤页 ${res.orphan_count} 个）`)
  } catch (e) { ElMessage.error(e.message) }
}

async function runSchemaSynth() {
  if (!SPLIT_MODE_ENABLED) {
    ElMessage.warning('Schema 合成仅在云本机分离模式下可用')
    return
  }
  const goal = synthForm.value.goal.trim()
  const objects = synthForm.value.objectsRaw
    .split(/[,，\n]/).map(s => s.trim()).filter(Boolean)
  if (!goal) { ElMessage.warning('请填写管理目标'); return }
  if (!objects.length) { ElMessage.warning('请至少给一个对象'); return }
  synthLoading.value = true
  try {
    synthResult.value = await api('/api/cloud/schema/synthesize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal, objects }),
    })
  } catch (e) { ElMessage.error(e.message) }
  finally { synthLoading.value = false }
}

async function applySchemaCustom() {
  if (!synthResult.value.schema) return
  await ElMessageBox.confirm(
    '应用后会替换你的 schema.yaml；现有 wiki 内容不会被删除，但目录结构可能不再匹配，请重启本机 agent。',
    '确认应用',
    { confirmButtonText: '应用', cancelButtonText: '取消' },
  ).catch(() => null)
  synthApplying.value = true
  try {
    await api('/api/cloud/schema/apply-custom', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schema: synthResult.value.schema }),
    })
    ElMessage.success('已应用 custom schema，重启本机 agent 后生效')
  } catch (e) { ElMessage.error(e.message) }
  finally { synthApplying.value = false }
}

async function clearCustomSchema() {
  try {
    await api('/api/cloud/schema/clear-custom', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    ElMessage.success('已清除 custom schema，重启本机 agent 后回退到模板')
  } catch (e) { ElMessage.error(e.message) }
}

// === 连接状态探测（P5） ===
const connStatus = ref({
  local: { ok: false, bound_user: null, legacy_mode: false },
  cloud: { ok: false, llm_configured: false },
})
const connProbing = ref(false)

async function probeConnections() {
  connProbing.value = true
  try {
    try {
      const data = await api('/api/health')
      connStatus.value.local = { ok: true, bound_user: data.bound_user, legacy_mode: data.legacy_mode }
    } catch { connStatus.value.local = { ok: false } }
    if (SPLIT_MODE_ENABLED) {
      try {
        const data = await api('/api/cloud/health')
        connStatus.value.cloud = { ok: true, llm_configured: !!data?.schema_synth?.llm_configured }
      } catch { connStatus.value.cloud = { ok: false } }
    } else {
      connStatus.value.cloud = { ok: false, llm_configured: false }
    }
  } finally { connProbing.value = false }
}

// admin 用户与心跳
const adminUsers = ref([])
const adminUsersLoading = ref(false)
async function loadAdminUsers() {
  adminUsersLoading.value = true
  try {
    const res = await api('/api/cloud/admin/users')
    adminUsers.value = res.users || []
  } catch (e) { ElMessage.error(e.message) }
  finally { adminUsersLoading.value = false }
}

// 维护抽屉打开时自动探测连接、加载 admin 数据
watch(maintenanceDrawer, (v) => {
  if (v) probeConnections()
})

// === 定时任务（P4） ===
const scheduleTasks = ref([])
const newScheduleTaskDialog = ref(false)
const newScheduleTask = ref({ name: '', kind: 'inbox_scan', scheduleType: 'cron', cron: '0 2 * * *', interval: 60 })
const scheduleSubmitting = ref(false)

async function loadScheduleTasks() {
  try {
    const res = await api('/api/schedule/tasks')
    scheduleTasks.value = res.tasks || []
  } catch (e) { ElMessage.error(e.message) }
}

async function submitScheduleTask() {
  const f = newScheduleTask.value
  const schedule = f.scheduleType === 'cron'
    ? { type: 'cron', value: f.cron.trim() }
    : { type: 'interval', value: Number(f.interval) }
  scheduleSubmitting.value = true
  try {
    await api('/api/schedule/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: f.name.trim() || f.kind, kind: f.kind, schedule, enabled: true }),
    })
    ElMessage.success('已创建')
    newScheduleTaskDialog.value = false
    await loadScheduleTasks()
  } catch (e) { ElMessage.error(e.message) }
  finally { scheduleSubmitting.value = false }
}

async function runScheduleNow(id) {
  try {
    await api(`/api/schedule/tasks/${id}/run-now`, { method: 'POST' })
    ElMessage.success('已触发；查看 last_status 看结果')
    await loadScheduleTasks()
  } catch (e) { ElMessage.error(e.message) }
}

async function toggleScheduleEnabled(t) {
  try {
    await api(`/api/schedule/tasks/${t.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: !t.enabled }),
    })
    await loadScheduleTasks()
  } catch (e) { ElMessage.error(e.message) }
}

async function deleteScheduleTask(id) {
  await ElMessageBox.confirm('删除任务？', '确认', { type: 'warning' }).catch(() => null)
  if (!maintenanceDrawer.value) return
  try {
    await api(`/api/schedule/tasks/${id}`, { method: 'DELETE' })
    await loadScheduleTasks()
  } catch (e) { ElMessage.error(e.message) }
}

watch(maintenanceTab, (tab) => {
  if (tab === 'schedule' && !scheduleTasks.value.length) loadScheduleTasks()
  if (tab === 'admin' && currentRole.value === 'admin' && SPLIT_MODE_ENABLED && !adminUsers.value.length) loadAdminUsers()
})

// === 源文档预览（P4） ===
const previewForm = ref({ path: '' })
const previewResult = ref({})

function formatBytes(n) {
  if (!n) return '0 B'
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1024 / 1024).toFixed(1) + ' MB'
}

async function loadPreviewInfo() {
  if (!previewForm.value.path.trim()) return
  try {
    const data = await api(`/api/source/preview?path=${encodeURIComponent(previewForm.value.path.trim())}&format=info`)
    previewResult.value = { info: data, text: '' }
  } catch (e) { ElMessage.error(e.message) }
}

async function loadPreviewText() {
  if (!previewForm.value.path.trim()) return
  try {
    const data = await api(`/api/source/preview?path=${encodeURIComponent(previewForm.value.path.trim())}&format=text`)
    previewResult.value = { info: { path: data.path, file_type: data.file_type, size: data.size }, text: data.text || '', truncated: data.truncated }
  } catch (e) { ElMessage.error(e.message) }
}

function openPreviewRaw() {
  const p = previewForm.value.path.trim()
  if (!p) return
  // 单体模式：相对路径直接走 same-origin；分离模式：拼本机 baseURL
  const base = (import.meta.env.VITE_LOCAL_API || '').replace(/\/+$/, '')
  // 注意：分离模式下浏览器直接打开新标签会缺 Bearer token；
  // 这里仅在单体模式下推荐使用。生产可改为先拿一次性下载 token。
  window.open(`${base}/api/source/raw?path=${encodeURIComponent(p)}`, '_blank')
}
</script>
