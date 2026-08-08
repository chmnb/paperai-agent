<template>
  <div class="reader-page">
    <div class="header">
      <a-button @click="$router.push('/papers')">← 返回论文列表</a-button>
      <h2>{{ paper?.title || '加载中...' }}</h2>
      <a-button type="primary" @click="$router.push(`/paper/${id}/qa`)">AI 问答</a-button>
    </div>
    <div class="content" v-if="paper">
      <a-card title="基本信息" style="margin-bottom: 16px">
        <p><strong>作者：</strong>{{ paper.authors || '未知' }}</p>
        <p><strong>摘要：</strong>{{ paper.abstract || '暂无摘要' }}</p>
        <p><strong>关键词：</strong>{{ paper.keywords?.join(', ') || '无' }}</p>
      </a-card>
      <a-card title="章节内容" v-if="sections?.length">
        <a-collapse>
          <a-collapse-item v-for="(sec, i) in sections" :key="i" :header="sec.section_title || sec.title">
            <p>{{ sec.content || sec.summary || '暂无内容' }}</p>
          </a-collapse-item>
        </a-collapse>
      </a-card>
      <a-empty v-else description="暂无章节解析" />
    </div>
    <a-spin v-else :loading="true" style="margin-top: 200px" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getPaper, getPaperSections } from '@/api/paper'

const route = useRoute()
const id = route.params.id as string
const paper = ref<any>(null)
const sections = ref<any[]>([])

onMounted(async () => {
  try {
    paper.value = await getPaper(id)
  } catch { }
  try {
    const res = await getPaperSections(id)
    sections.value = res.sections || []
  } catch { }
})
</script>

<style scoped>
.reader-page { min-height: 100vh; background: #f5f5f5; }
.header { display: flex; align-items: center; gap: 16px; padding: 12px 24px; background: white; border-bottom: 1px solid #e5e6eb; }
.header h2 { flex: 1; margin: 0; text-align: center; }
.content { max-width: 900px; margin: 24px auto; padding: 0 24px; }
</style>
