<template>
  <div class="qa-page">
    <div class="header">
      <a-button @click="$router.push(`/paper/${id}`)">返回阅读</a-button>
      <h2>{{ paper?.title || '论文问答' }}</h2>
    </div>
    <div class="qa-container">
      <div class="qa-content">
        <div class="qa-list" v-if="qaHistory.length > 0" ref="qaListRef">
          <div v-for="(qa, idx) in qaHistory" :key="qa.id" class="qa-item">
            <div class="question">
              <div class="avatar">👤</div>
              <div class="content"><div class="label">问题</div><div class="text">{{ qa.question }}</div></div>
            </div>
            <div class="answer">
              <div class="avatar">🤖</div>
              <div class="content">
                <div class="label">
                  回答
                  <a-tag v-if="qa.intent" :color="getIntentColor(qa.intent)">{{ qa.intent }}</a-tag>
                  <span v-if="qa.streaming" style="color:#165dff;margin-left:8px">生成中<span class="cursor">▌</span></span>
                </div>
                <div class="text">
                  {{ qa.answer }}
                  <span v-if="qa.streaming" class="cursor">▌</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <a-empty v-else description="在下方输入问题开始提问" style="margin-top:80px" />
        <div class="input-area">
          <a-textarea v-model="question" placeholder="请输入您关于这篇论文的问题..." :auto-size="{ minRows: 2, maxRows: 4 }" :disabled="loading" @keyup.enter.ctrl="handleAsk" />
          <div class="input-actions">
            <div class="quick-questions">
              <a-tag v-for="q in quickQuestions" :key="q" clickable @click="question = q">{{ q }}</a-tag>
            </div>
            <a-space>
              <a-button v-if="loading" @click="handleStop">停止生成</a-button>
              <a-button type="primary" :loading="loading" @click="handleAsk">提问</a-button>
            </a-space>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { getPaper, askPaperQuestionStream } from '@/api/paper'

const route = useRoute()
const id = route.params.id as string

const loading = ref(false)
const paper = ref<any>(null)
const question = ref('')
const qaHistory = ref<any[]>([])
const qaListRef = ref<HTMLElement | null>(null)
let abortController: AbortController | null = null

const quickQuestions = ['这篇论文的主要贡献是什么？', '论文使用的主要方法是什么？', '实验结果如何？', '论文的局限性有哪些？']

const scrollToBottom = async () => {
  await nextTick()
  if (qaListRef.value) {
    qaListRef.value.scrollTop = qaListRef.value.scrollHeight
  }
}

const loadPaper = async () => {
  try { paper.value = await getPaper(id) } catch { }
}

const handleAsk = async () => {
  if (!question.value.trim()) { Message.warning('请输入问题'); return }
  if (loading.value) return

  const currentQuestion = question.value
  question.value = ''
  loading.value = true

  // 先插入一个占位条目，answer 为空，标记 streaming
  const entry: any = {
    id: Date.now().toString(),
    question: currentQuestion,
    answer: '',
    intent: '',
    streaming: true,
  }
  qaHistory.value.push(entry)
  await scrollToBottom()

  abortController = askPaperQuestionStream(
    id,
    currentQuestion,
    // onToken: 每次收到新 token，追加到 answer
    (token: string) => {
      const last = qaHistory.value[qaHistory.value.length - 1]
      if (last) {
        last.answer += token
      }
    },
    // onDone: 流结束，去掉 streaming 标记
    (data: { intent: string; qa_id?: string }) => {
      const last = qaHistory.value[qaHistory.value.length - 1]
      if (last) {
        last.intent = data.intent
        last.id = data.qa_id || last.id
        last.streaming = false
      }
      loading.value = false
      abortController = null
    },
    // onError
    (err: Error) => {
      const last = qaHistory.value[qaHistory.value.length - 1]
      if (last) {
        last.answer += '\n\n[生成出错，请重试]'
        last.streaming = false
      }
      Message.error('生成失败')
      loading.value = false
      abortController = null
    },
  )
}

const handleStop = () => {
  if (abortController) {
    abortController.abort()
    const last = qaHistory.value[qaHistory.value.length - 1]
    if (last) {
      last.streaming = false
      if (!last.answer) last.answer = '[已停止生成]'
    }
    loading.value = false
    abortController = null
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
.content { flex: 1; min-width: 0; }
.label { font-size: 12px; color: #999; margin-bottom: 4px; }
.text { padding: 16px; background: white; border-radius: 8px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
.question .text { background: #f5f5f5; }
.input-area { padding: 24px; background: white; border-top: 1px solid #e5e6eb; }
.input-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 12px; }
.quick-questions { display: flex; gap: 8px; flex-wrap: wrap; flex: 1; }
.cursor { color: #165dff; animation: blink 0.8s infinite; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
</style>
