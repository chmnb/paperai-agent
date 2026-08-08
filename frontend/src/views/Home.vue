<template>
  <div class="home-page">
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="title">📚 PaperAI</h1>
        <p class="subtitle">智能论文精读助手，让阅读更高效</p>
        <div class="actions">
          <a-button type="primary" size="large" @click="$router.push('/papers')">上传论文</a-button>
          <a-button size="large" @click="$router.push('/login')">登录账号</a-button>
        </div>
      </div>
    </div>
    <div class="features-section">
      <h2>核心功能</h2>
      <a-row :gutter="[24, 24]">
        <a-col :span="6"><a-card hoverable><template #cover><div class="feature-icon">📄</div></template><a-card-meta title="智能解析" description="自动提取论文结构,快速定位关键内容" /></a-card></a-col>
        <a-col :span="6"><a-card hoverable><template #cover><div class="feature-icon">💬</div></template><a-card-meta title="交互问答" description="针对论文内容提问,即问即答" /></a-card></a-col>
        <a-col :span="6"><a-card hoverable><template #cover><div class="feature-icon">📝</div></template><a-card-meta title="笔记管理" description="结构化笔记,分类整理,方便回顾" /></a-card></a-col>
        <a-col :span="6"><a-card hoverable><template #cover><div class="feature-icon">🔍</div></template><a-card-meta title="知识检索" description="基于RAG技术,实现智能知识检索" /></a-card></a-col>
      </a-row>
    </div>
  </div>
</template>

<style scoped>
.home-page { min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.hero-section { display: flex; justify-content: center; align-items: center; min-height: 500px; padding: 60px 24px; }
.hero-content { text-align: center; color: white; }
.title { font-size: 64px; font-weight: 700; margin-bottom: 16px; }
.subtitle { font-size: 24px; opacity: 0.9; margin-bottom: 40px; }
.actions { display: flex; gap: 16px; justify-content: center; }
.features-section { background: white; padding: 80px 24px; }
.features-section h2 { text-align: center; font-size: 32px; margin-bottom: 48px; }
.feature-icon { font-size: 64px; padding: 40px 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
</style>
