<template>
  <div class="paper-list-page">
    <div class="header">
      <h1>📚 我的论文库</h1>
      <a-button type="primary" @click="triggerFileInput">上传论文</a-button>
      <input ref="fileInput" type="file" accept=".pdf" style="display:none" @change="onFileSelected" />
    </div>
    <div class="paper-list">
      <a-spin :loading="loading">
        <a-list>
          <a-list-item v-for="paper in papers" :key="paper.id">
            <a-list-item-meta>
              <template #avatar><a-avatar :style="{ backgroundColor: '#165dff' }">📄</a-avatar></template>
              <template #title><a-link @click="$router.push(`/paper/${paper.id}`)">{{ paper.title }}</a-link></template>
              <template #description><span>{{ paper.authors || '未知作者' }}</span><span> • </span><span>{{ formatDate(paper.upload_at) }}</span></template>
            </a-list-item-meta>
            <template #actions>
              <a-button type="text" size="small" @click="$router.push(`/paper/${paper.id}`)">阅读</a-button>
              <a-button type="text" size="small" @click="$router.push(`/paper/${paper.id}/qa`)">问答</a-button>
              <a-button type="text" size="small" status="danger" @click="handleDelete(paper.id)">删除</a-button>
            </template>
          </a-list-item>
        </a-list>
        <a-empty v-if="!loading && papers.length === 0" description="还没有论文，点击右上角上传" />
      </a-spin>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import { getPaperList, uploadPaper, deletePaper } from '@/api/paper'
import dayjs from 'dayjs'

const loading = ref(false)
const papers = ref<any[]>([])
const fileInput = ref<HTMLInputElement | null>(null)

const loadPapers = async () => {
  loading.value = true
  try {
    const response = await getPaperList({})
    papers.value = response.papers || []
  } catch (e) {
    Message.error('加载论文列表失败')
  } finally {
    loading.value = false
  }
}

const triggerFileInput = () => {
  fileInput.value?.click()
}

const onFileSelected = async (e: Event) => {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  if (!file.name.endsWith('.pdf')) { Message.warning('请选择 PDF 文件'); return }

  loading.value = true
  try {
    Message.info({ content: '正在上传并解析论文...', duration: 5000 })
    const res = await uploadPaper(file)
    Message.success(`上传成功: ${res.title || file.name}`)
    loadPapers()
  } catch (e: any) {
    Message.error('上传失败: ' + (e?.response?.data?.detail || e?.message || '请重试'))
  } finally {
    loading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

const handleDelete = (paperId: string) => {
  Modal.warning({ title: '确认删除', content: '确定要删除这篇论文吗？', okText: '删除',
    onOk: async () => { try { await deletePaper(paperId); Message.success('删除成功'); loadPapers() } catch (e) { Message.error('删除失败') } }
  })
}

const formatDate = (date: string) => dayjs(date).format('YYYY-MM-DD')

onMounted(() => { loadPapers() })
</script>

<style scoped>
.paper-list-page { min-height: 100vh; background: #f5f5f5; padding: 24px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.header h1 { margin: 0; }
.paper-list { background: white; border-radius: 8px; padding: 16px; }
</style>
