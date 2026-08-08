<template>
  <div class="login-page">
    <div class="login-card">
      <div class="logo"><h1>📚 PaperAI</h1><p>智能论文精读助手</p></div>
      <div style="margin-bottom:16px">
        <label>用户名</label>
        <input v-model="form.username" placeholder="请输入用户名" style="width:100%;padding:10px;margin:8px 0;border:1px solid #ccc;border-radius:4px" @keyup.enter="handleLogin"/>
      </div>
      <div style="margin-bottom:16px">
        <label>密码</label>
        <input v-model="form.password" type="password" placeholder="请输入密码" style="width:100%;padding:10px;margin:8px 0;border:1px solid #ccc;border-radius:4px" @keyup.enter="handleLogin"/>
      </div>
      <button @click="handleLogin" :disabled="loading" style="width:100%;padding:12px;background:#165dff;color:white;border:none;border-radius:4px;font-size:16px;cursor:pointer">
        {{ loading ? '登录中...' : '登录' }}
      </button>
      <div v-if="errorMsg" style="color:red;margin-top:12px;text-align:center">{{ errorMsg }}</div>
      <div v-if="successMsg" style="color:green;margin-top:12px;text-align:center">{{ successMsg }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '@/api/auth'

const router = useRouter()
const form = ref({ username: '', password: '' })
const loading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

const handleLogin = async () => {
  console.log('handleLogin called', form.value)
  errorMsg.value = ''
  successMsg.value = ''

  if (!form.value.username || !form.value.password) {
    errorMsg.value = '请填写用户名和密码'
    return
  }
  loading.value = true
  try {
    console.log('calling login API...')
    const response = await login(form.value)
    console.log('login response:', response)
    localStorage.setItem('access_token', response.access_token)
    localStorage.setItem('user', JSON.stringify(response.user))
    successMsg.value = '登录成功，跳转中...'
    setTimeout(() => router.push('/home'), 500)
  } catch (error: any) {
    console.error('login error:', error)
    errorMsg.value = '登录失败：' + (error?.message || '请重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { display: flex; justify-content: center; align-items: center; min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 24px; }
.login-card { width: 100%; max-width: 400px; padding: 40px; background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
.logo { text-align: center; margin-bottom: 32px; }
.logo h1 { font-size: 32px; margin-bottom: 8px; }
.logo p { color: #666; font-size: 14px; }
</style>
