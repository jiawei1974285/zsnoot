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
          <el-button type="primary" size="large" :loading="authSubmitting" class="auth-primary-button" @click="submitRegister">
            注册并登录
          </el-button>
        </el-form>

        <div v-if="authMode === 'login'" class="auth-divider"><span>或</span></div>
        <button v-if="authMode === 'login'" type="button" class="auth-local-button" @click="localModeLogin">
          <el-icon><Box /></el-icon>
          使用本机账户登录
        </button>
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
              @click="item.key === 'knowledge' ? toggleKnowledgeTree() : setActiveView(item.key)"
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
              <strong>{{ currentUser || '张警官' }}</strong>
              <span>XX公安局 刑侦支队</span>
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
            <div class="status-pill agent-status-pill" :class="agentStatusClass">
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
          <template v-if="activeView === 'home'">
            <div class="section-header">
              <div>
                <div class="section-title">首页</div>
                <div class="section-caption">本地知识库一览：入库与活跃情况、实体分布、最近问答、常见问题。</div>
              </div>
              <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
            </div>

            <!-- KPI 大字行 -->
            <div class="dashboard-kpi-row">
              <div class="kpi-card">
                <div class="kpi-label">入库文件</div>
                <div class="kpi-value">{{ homeStats.ingested_files || 0 }}</div>
                <div class="kpi-sub">{{ homeStats.batches || 0 }} 个批次</div>
              </div>
              <div class="kpi-card">
                <div class="kpi-label">知识卡片</div>
                <div class="kpi-value">{{ homeStats.pages || 0 }}</div>
                <div class="kpi-sub">分布在 {{ Object.keys(homeStats.by_type || {}).length }} 类目录</div>
              </div>
              <div class="kpi-card">
                <div class="kpi-label">实体总数</div>
                <div class="kpi-value">{{ entityTotal }}</div>
                <div class="kpi-sub">
                  <template v-for="(n, t, idx) in homeStats.by_type" :key="t">
                    <span v-if="idx < 3">{{ typeLabel(t) }} {{ n }}<span v-if="idx < 2">·</span></span>
                  </template>
                </div>
              </div>
              <div class="kpi-card">
                <div class="kpi-label">本周对话</div>
                <div class="kpi-value">{{ homeStats.this_week?.chat || 0 }}</div>
                <div class="kpi-sub">
                  <span v-if="weekDelta.chat > 0" class="kpi-delta-up">↑ 比上周 +{{ weekDelta.chat }}</span>
                  <span v-else-if="weekDelta.chat < 0" class="kpi-delta-down">↓ 比上周 {{ weekDelta.chat }}</span>
                  <span v-else>与上周持平</span>
                </div>
              </div>
            </div>

            <!-- 图表区 -->
            <div class="dashboard-charts">
              <section class="dashboard-chart-card">
                <v-chart class="dashboard-chart" :option="dailyTrendOption" autoresize />
              </section>
              <section class="dashboard-chart-card dashboard-chart-narrow">
                <v-chart v-if="entityTotal > 0" class="dashboard-chart" :option="typeDistributionOption" autoresize />
                <div v-else class="dashboard-chart-empty">
                  <el-icon><Box /></el-icon>
                  <div>还没有任何实体页面，先去上传材料吧</div>
                </div>
              </section>
            </div>

            <!-- 列表区 -->
            <div class="home-overview">
              <section class="home-panel">
                <div class="section-title section-title-sm">最近添加批次</div>
                <div class="batch-list compact">
                  <button
                    v-for="batch in recentBatches"
                    :key="batch.id"
                    class="batch-row"
                    @click="openRecentBatch(batch)"
                  >
                    <span class="batch-status-dot" :class="statusType(batch.status)"></span>
                    <span class="batch-name">{{ summarizeBatchTitle(batch) }}</span>
                    <span class="batch-date">{{ formatTime(batch.created_at) }}</span>
                    <el-tag size="small" :type="statusType(batch.status)">{{ statusLabel(batch.status) }}</el-tag>
                  </button>
                  <div v-if="!recentBatches.length" class="detail-item">还没有入库记录</div>
                </div>
              </section>

              <section class="home-panel">
                <div class="section-title section-title-sm">最近问答</div>
                <div class="qa-list">
                  <button
                    v-for="qa in homeStats.recent_qa || []"
                    :key="qa.slug"
                    class="qa-row"
                    @click="openQAFromHome(qa)"
                  >
                    <div class="qa-title">{{ qa.title }}</div>
                    <div class="qa-snippet">{{ qa.snippet || '（无摘要）' }}</div>
                    <div class="qa-date">{{ qa.created }}</div>
                  </button>
                  <div v-if="!homeStats.recent_qa?.length" class="detail-item">最近还没有对话查询</div>
                </div>
              </section>
            </div>

            <!-- FAQ 静态说明 -->
            <section class="home-panel home-faq">
              <div class="section-title section-title-sm">使用问答（FAQ）</div>
              <el-collapse>
                <el-collapse-item v-for="(item, idx) in faqItems" :key="idx" :name="idx">
                  <template #title>
                    <span class="faq-q">{{ item.q }}</span>
                  </template>
                  <div class="faq-a">{{ item.a }}</div>
                </el-collapse-item>
              </el-collapse>
            </section>
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
                  {{ message.content }}
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
              </section>

              <section class="config-card">
                <div class="section-title section-title-sm">入库与检索</div>
                <el-form-item label="模型温度">
                  <el-slider v-model="configForm.llm.temperature" :min="0" :max="1" :step="0.1" show-input />
                </el-form-item>
                <el-form-item label="最大输出 Token">
                  <el-input-number v-model="configForm.llm.max_tokens" :min="512" :max="32000" :step="512" style="width: 100%" />
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
                <div class="section-caption">检查断链、孤立页面、过期内容和需要补充的线索。</div>
              </div>
              <el-button type="primary" :loading="lintLoading" :icon="CircleCheck" @click="runLint">
                开始体检
              </el-button>
            </div>
            <div class="detail-list">
              <div v-for="suggestion in lint.suggestions || []" :key="suggestion" class="detail-item">
                {{ suggestion }}
              </div>
              <div v-if="lint.broken_links?.length" class="detail-item lint-row">
                <span>断链关联：{{ lint.broken_links.length }} 条</span>
                <el-button size="small" type="primary" @click="openLintFix('broken_links')">处理</el-button>
              </div>
              <div v-if="lint.orphan_pages?.length" class="detail-item lint-row">
                <span>孤立页面：{{ lint.orphan_pages.length }} 个</span>
                <el-button size="small" type="primary" @click="openLintFix('orphan_pages')">处理</el-button>
              </div>
              <div v-if="lint.stale_pages?.length" class="detail-item lint-row">
                <span>过期内容：{{ lint.stale_pages.length }} 个</span>
                <el-button size="small" type="primary" @click="openLintFix('stale_pages')">处理</el-button>
              </div>
              <div v-if="!lint.suggestions" class="detail-item">尚未运行体检</div>
            </div>

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
                <el-table-column v-if="lintFixDialog.category !== 'broken_links'" label="页面" prop="slug" />
                <el-table-column v-if="lintFixDialog.category !== 'broken_links'" label="类型" prop="type" width="100" />
                <el-table-column v-if="lintFixDialog.category === 'stale_pages'" label="上次更新" prop="last_updated" width="140" />
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
          <div class="page-preview-actions">
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
  UploadFilled,
  View,
} from '@element-plus/icons-vue'
import { GRAPH_LAYOUTS, layoutTargets } from './graphLayouts'

const navItems = [
  { key: 'home', label: '首页', icon: HomeFilled },
  { key: 'ingest', label: '上传材料', icon: Box },
  { key: 'chat', label: '对话查询', icon: ChatDotRound },
  { key: 'knowledge', label: '知识卡片', icon: Collection },
  { key: 'graph', label: '关系图谱', icon: Connection },
  { key: 'lint', label: '知识库体检', icon: CircleCheck },
  { key: 'config', label: '系统配置', icon: Setting },
]

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
})
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
})
const homeActivity = ref([])

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
const selectedBatch = ref(null)
const expandedBatchId = ref(null)
const selectedBatchIds = ref([])
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
const pageSortBy = ref('updated_desc') // updated_desc | updated_asc | created_desc | title_asc
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
  const map = { broken_links: '修复断链', orphan_pages: '处理孤立页面', stale_pages: '处理过期页面' }
  return map[lintFixDialog.value.category] || '体检处理'
})

function lintFixActionOptions(category) {
  if (category === 'broken_links') {
    return [
      { value: 'remove', label: '删除该链接' },
      { value: 'create_stub', label: '创建占位页' },
    ]
  }
  if (category === 'orphan_pages') {
    return [
      { value: 'enrich', label: '自动补充关联' },
      { value: 'ignore', label: '标记独立(忽略)' },
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
  // 排序：复制后再排，避免修改原数组（pages 是源数据）
  const sorted = list.slice()
  const cmp = (a, b, key) => String(a[key] || '').localeCompare(String(b[key] || ''))
  switch (pageSortBy.value) {
    case 'updated_asc':
      sorted.sort((a, b) => cmp(a, b, 'updated'))
      break
    case 'created_desc':
      sorted.sort((a, b) => cmp(b, a, 'created'))
      break
    case 'title_asc':
      sorted.sort((a, b) => String(a.title || '').localeCompare(String(b.title || ''), 'zh-CN'))
      break
    case 'updated_desc':
    default:
      sorted.sort((a, b) => cmp(b, a, 'updated'))
  }
  return sorted
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
const categoryOptions = computed(() => {
  const defaults = [
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
  const response = await fetch(path, { credentials: 'same-origin', ...options })
  const data = await response.json().catch(() => ({}))
  if (response.status === 401 && !path.startsWith('/api/auth/')) {
    // session 失效或未登录,踢回登录页
    authState.value = 'login'
    currentUser.value = null
    throw new Error(data.error || '请先登录')
  }
  if (!response.ok) {
    throw new Error(data.error || `请求失败：${response.status}`)
  }
  return data
}

// === 鉴权流程 ===
async function checkAuth() {
  try {
    const status = await api('/api/auth/status')
    if (!status.has_user) {
      authState.value = 'setup'
    } else if (!status.logged_in) {
      authState.value = 'login'
      authMode.value = 'login'
    } else {
      currentUser.value = status.username
      currentRole.value = status.role || null
      authState.value = 'authed'
      // 进入主应用,加载初始数据
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
      body: JSON.stringify({ username: f.username.trim(), password: f.password }),
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
    authState.value = 'authed'
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
    authState.value = 'authed'
    loginForm.value.password = ''
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
      }),
    })
    ElMessage.success('注册成功，已自动登录')
    currentUser.value = res.username
    currentRole.value = res.role || null
    authState.value = 'authed'
    // 清掉密码字段，留下其他便于参考
    registerForm.value.password = ''
    registerForm.value.password_confirm = ''
    registerForm.value.invite_code = ''
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

function setActiveView(view) {
  activeView.value = view
  if (view === 'graph' && !graph.value.nodes.length) {
    loadGraph()
  } else if (view === 'graph') {
    nextTick(scheduleRenderGraph)
  } else if (view === 'config' && currentRole.value === 'admin') {
    loadInvites()
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
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collide', d3.forceCollide().radius((item) => item.radius + graphCollisionGap(nodes.length)))
    .force('boundsX', d3.forceX((item) => graphBoundaryTarget(item.x, width, padding)).strength(graphBoundaryStrength(nodes.length)))
    .force('boundsY', d3.forceY((item) => graphBoundaryTarget(item.y, height, padding)).strength(graphBoundaryStrength(nodes.length)))

  if (graphLayout.value !== 'force') {
    simulation
      .force('x', d3.forceX((item) => targets.get(item.id)?.x || width / 2).strength(0.28))
      .force('y', d3.forceY((item) => targets.get(item.id)?.y || height / 2).strength(0.28))
  } else {
    simulation
      .force('x', d3.forceX(width / 2).strength(0.025))
      .force('y', d3.forceY(height / 2).strength(0.025))
  }

  const ticked = () => {
    nodes.forEach((item) => {
      item.x = clamp(item.x, padding, width - padding)
      item.y = clamp(item.y, padding, height - padding)
    })
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
    resetGraphZoom()
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
  const spread = Math.max(1, Math.sqrt(Math.max(count, 1) / 55))
  const padding = count > 180 ? 240 : count > 90 ? 220 : 180
  return {
    width: Math.round(Math.max(visibleWidth, visibleWidth * Math.min(3.1, spread))),
    height: Math.round(Math.max(visibleHeight, visibleHeight * Math.min(2.8, spread * 0.98))),
    padding,
  }
}

function graphLinkDistance(count, edge) {
  const base = count > 240 ? 150 : count > 120 ? 132 : 108
  return base + Math.min(28, (edge.weight || 1) * 4)
}

function graphNodeRadius(count) {
  if (count > 180) return 8
  if (count > 90) return 9
  return 10
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

function graphBoundaryTarget(value, size, padding) {
  if (!Number.isFinite(value)) return size / 2
  return clamp(value, padding, size - padding)
}

function graphBoundaryStrength(count) {
  if (graphLayout.value !== 'force') return 0.08
  if (count > 120) return 0.14
  return 0.1
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
  d3.select(graphSvgRef.value).transition().duration(220).call(graphZoomBehavior.transform, d3.zoomIdentity)
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
  const slug = `note-${ts.getFullYear()}${pad(ts.getMonth() + 1)}${pad(ts.getDate())}-${pad(ts.getHours())}${pad(ts.getMinutes())}${pad(ts.getSeconds())}`
  const title = `新建笔记 ${ts.getFullYear()}-${pad(ts.getMonth() + 1)}-${pad(ts.getDate())} ${pad(ts.getHours())}:${pad(ts.getMinutes())}`
  try {
    await api('/api/wiki/pages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        slug,
        type: 'notes',
        meta: { title, tags: [], related: [] },
        body: '',
      }),
    })
    selectedPage.value = await api(`/api/wiki/pages/${encodeURIComponent(slug)}?type=notes`)
    pageEditDraft.value = { title, body: '' }
    pageEditMode.value = true
    pageDrawer.value = true
    await loadPages()
  } catch (error) {
    ElMessage.error(error.message)
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
  await refreshAll()
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
    const sources = result.sources?.length ? `\n\n来源：${result.sources.map((source) => source.title).join('、')}` : ''
    messages.value.push({ id: id + 1, role: 'assistant', content: `${result.response}${sources}` })
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

function renderMarkdownPreview(markdown) {
  const lines = String(markdown || '').split('\n')
  const html = lines
    .map((line) => {
      const escaped = escapeHtml(line)
        .replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, '<button class="wiki-link" data-slug="$1">$2</button>')
        .replace(/\[\[([^\]]+)\]\]/g, '<button class="wiki-link" data-slug="$1">$1</button>')
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
</script>
