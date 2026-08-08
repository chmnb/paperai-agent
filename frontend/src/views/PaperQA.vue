<template>
  <div class="qa-page">
    <div class="header">
      <a-button @click="$router.push(`/paper/${id}`)">返回阅读</a-button>
      <h2>{{ paper?.title || '论文问答' }}</h2>
    </div>
    <div class="qa-container">
      <div class="qa-content">
        <div class="qa-list" v-if="qaHistory.length > 0">
          <div v-for="qa in qaHistory" :key="qa.id" class="qa-item">
            <div class="question"><div class="avatar">👤</div><div class="content"><div class="label">问题</div><div class="text">{{ qa.question }}</div></div></div>
            <div class="answer"><div class="avatar">🤖</div><div class="content"><div class="label">回答 <a-tag :color="getIntentColor(qa.intent)">{{ qa.intent }}</a-tag></div><div class="text">{{ qa.answer }}</div></div></div>
          </div>
        </div>
        <a-empty v-else description="在下方输入问题开始提问" style="margin-top:80px" />
        <div class="input-area">
          <a-textarea v-model="question" placeholder="请输入您关于这篇论文的问题..." :auto-size="{ minRows: 2, maxRows: 4 }" @keyup.enter.ctrl="handleAsk" />
          <div class="input-actions">
            <div class="quick-questions">
              <a-tag v-for="q in quickQuestions" :key="q" clickable @click="question = q">{{ q }}</a-tag>
            </div>
            <a-button type="primary" :loading="loading" @click="handleAsk">提问</a-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { getPaper, askPaperQuestion } from '@/api/paper'

const route = useRoute()
const id = route.params.id as string

const loading = ref(false)
const paper = ref<any>(null)
const question = ref('')
const qaHistory = ref<any[]>([])

const quickQuestions = ['这篇论文的主要贡献是什么？', '论文使用的主要方法是什么？', '实验结果如何？', '论文的局限性有哪些？']

const loadPaper = async () => {
  try { paper.value = await getPaper(id) } catch { }
}

const handleAsk = async () => {
  if (!question.value.trim()) { Message.warning('请输入问题'); return }
  loading.value = true
  try {
    const response = await askPaperQuestion(id, question.value)
    qaHistory.value.push({ id: response.qa_id, question: question.value, answer: response.answer, intent: response.intent, confidence: response.confidence })
    question.value = ''
    Message.success('回答已生成')
  } catch (e) {
    Message.error('提问失败，请重试')
  } finally {
    loading.value = false
  }
}

const getIntentColor = (intent: string) => {
  const colors: Record<string, string> = { concept: 'green', method: 'blue', experiment: 'orange', code: 'purple', general: 'gray' }
  return colors[intent] || 'gray'
}

onMounted(() => { loadPaper() })
</script>

<style scoped>
.qa-page { height: 100vh; display: flex; flex-direction: column; background: #f5f5f5; }
.header { display: flex; align-items: center; padding: 12px 24px; background: white; border-bottom: 1px solid #e5e6eb; }
.header h2 { flex: 1; text-align: center; margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.qa-container { flex: 1; display: flex; overflow: hidden; }
.qa-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.qa-list { flex: 1; overflow-y: auto; padding: 24px; }
.qa-item { margin-bottom: 24px; }
.question, .answer { display: flex; gap: 12px; margin-bottom: 16px; }
.avatar { width: 40px; height: 40px; border-radius: 50%; background: #f0f0f0; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
.answer .avatar { background: #e6f7ff; }
.content { flex: 1; }
.label { font-size: 12px; color: #999; margin-bottom: 4px; }
.text { padding: 16px; background: white; border-radius: 8px; line-height: 1.6; }
.question .text { background: #f5f5f5; }
.input-area { padding: 24px; background: white; border-top: 1px solid #e5e6eb; }
.input-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 12px; }
.quick-questions { display: flex; gap: 8px; flex-wrap: wrap; }
</style>
