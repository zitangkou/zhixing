<template>
  <view class="page-profile" :class="themeClass">
    <button v-if="isWeapp" class="avatar-card avatar-btn" open-type="chooseAvatar" @chooseavatar="onChooseAvatar">
      <nut-avatar size="large" class="avatar">
        <image v-if="avatarUrl" class="avatar-img" :src="avatarUrl" mode="aspectFill" />
        <text v-else>{{ nickname.slice(0, 1) || '学' }}</text>
      </nut-avatar>
      <view class="avatar-meta">
        <text class="avatar-title">使用微信头像</text>
        <text class="avatar-tip">点此选择微信头像</text>
      </view>
      <text class="avatar-arrow">›</text>
    </button>
    <view v-else class="avatar-card" @tap="onPickAvatar">
      <nut-avatar size="large" class="avatar">
        <image v-if="avatarUrl" class="avatar-img" :src="avatarUrl" mode="aspectFill" />
        <text v-else>{{ nickname.slice(0, 1) || '学' }}</text>
      </nut-avatar>
      <view class="avatar-meta">
        <text class="avatar-title">点击更换头像</text>
        <text class="avatar-tip">支持 jpg / png，不超过 2MB</text>
      </view>
      <text class="avatar-arrow">›</text>
    </view>

    <view class="form-card">
      <view class="field">
        <text class="label">账号</text>
        <text class="value muted">{{ username || '—' }}</text>
      </view>
      <view class="field">
        <text class="label">昵称</text>
        <input
          v-if="isWeapp"
          class="nick-input"
          type="nickname"
          :value="nickname"
          placeholder="请填写微信昵称"
          maxlength="32"
          @input="onNicknameInput"
          @blur="onNicknameInput"
        />
        <nut-input v-else v-model="nickname" placeholder="请输入昵称" clearable max-length="32" />
      </view>
      <view class="field">
        <text class="label">邮箱</text>
        <nut-input v-model="email" placeholder="选填" clearable />
      </view>
      <view class="field">
        <text class="label">手机号</text>
        <nut-input v-model="phone" type="digit" placeholder="选填，11 位手机号" clearable max-length="11" />
      </view>
      <nut-button
        type="primary"
        block
        class="primary-btn"
        :loading="saving"
        @click="onSaveProfile"
      >
        保存资料
      </nut-button>
    </view>

    <view v-if="username" class="form-card">
      <view class="field">
        <text class="label">原密码</text>
        <nut-input v-model="oldPassword" type="password" placeholder="请输入原密码" clearable />
      </view>
      <view class="field">
        <text class="label">新密码</text>
        <nut-input v-model="newPassword" type="password" placeholder="至少 6 位" clearable />
      </view>
      <view class="field">
        <text class="label">确认密码</text>
        <nut-input v-model="newPasswordConfirm" type="password" placeholder="再次输入新密码" clearable />
      </view>
      <nut-button
        type="primary"
        block
        class="primary-btn"
        :loading="changingPwd"
        @click="onChangePassword"
      >
        修改密码
      </nut-button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Taro, { useLoad } from '@tarojs/taro'
import { Avatar as NutAvatar, Button as NutButton, Input as NutInput } from '@nutui/nutui-taro'
import { useUserStore } from '@/store/user'
import { enterAfterAuth } from '@/utils/auth'
import { resolveMediaUrl } from '@/utils/media'
import { getPlatform, showToast } from '@/utils/platform'
import { useThemeClass } from '@/utils/brandColor'

definePageConfig({ navigationBarTitleText: '个人资料' })

const { themeClass } = useThemeClass()
const userStore = useUserStore()
const isWeapp = getPlatform() === 'weapp'
const setup = ref(false)

useLoad((query) => {
  setup.value = query?.setup === '1'
})

const username = computed(() => userStore.userInfo?.username || '')
const nickname = ref(userStore.userInfo?.nickname || '')
const email = ref(userStore.userInfo?.email || '')
const phone = ref(userStore.userInfo?.phone || '')
const avatarUrl = computed(() => resolveMediaUrl(userStore.userInfo?.avatar))

const oldPassword = ref('')
const newPassword = ref('')
const newPasswordConfirm = ref('')

const saving = ref(false)
const changingPwd = ref(false)
const uploading = ref(false)

async function uploadPicked(filePath: string, file?: File) {
  uploading.value = true
  try {
    await userStore.uploadAvatar(filePath, file)
    showToast('头像已更新', 'success')
  } finally {
    uploading.value = false
  }
}

async function onChooseAvatar(event: { detail?: { avatarUrl?: string } }) {
  const filePath = event.detail?.avatarUrl
  if (!filePath || uploading.value) return
  try {
    await uploadPicked(filePath)
  } catch (e) {
    showToast(e instanceof Error ? e.message : '更换头像失败', 'error')
  }
}

function onNicknameInput(event: { detail?: { value?: string } }) {
  nickname.value = event.detail?.value || ''
}

async function onPickAvatar() {
  if (uploading.value) return
  try {
    const res = await Taro.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
    })
    const filePath = res.tempFilePaths?.[0]
    if (!filePath) return
    const file = (res.tempFiles?.[0] as { originalFileObj?: File } | undefined)?.originalFileObj
    await uploadPicked(filePath, file)
  } catch (e) {
    if (e instanceof Error && /cancel/i.test(e.message)) return
    showToast(e instanceof Error ? e.message : '更换头像失败', 'error')
  }
}

async function onSaveProfile() {
  if (!nickname.value.trim() || (setup.value && nickname.value.trim() === '杜衡阁学员')) {
    showToast('请填写一个自己的昵称', 'error')
    return
  }
  saving.value = true
  try {
    await userStore.updateProfile({
      nickname: nickname.value.trim(),
      email: email.value.trim(),
      phone: phone.value.trim(),
    })
    showToast('资料已保存', 'success')
    if (setup.value) enterAfterAuth()
  } catch (e) {
    showToast(e instanceof Error ? e.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function onChangePassword() {
  if (!oldPassword.value || !newPassword.value || !newPasswordConfirm.value) {
    showToast('请填写完整密码信息', 'error')
    return
  }
  changingPwd.value = true
  try {
    await userStore.changePassword({
      oldPassword: oldPassword.value,
      newPassword: newPassword.value,
      newPasswordConfirm: newPasswordConfirm.value,
    })
    oldPassword.value = ''
    newPassword.value = ''
    newPasswordConfirm.value = ''
    showToast('密码已修改', 'success')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '修改失败', 'error')
  } finally {
    changingPwd.value = false
  }
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.page-profile {
  @include page-padding;
  padding-bottom: 40px;

  .avatar-card {
    @include card;
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 18px 16px;
    border-radius: $radius-lg;
    margin-bottom: 12px;
    text-align: left;
    &.avatar-btn {
      width: 100%;
      line-height: inherit;
      background: $card-bg;
      color: inherit;
    }
    &.avatar-btn::after { border: none; }
    .avatar {
      flex-shrink: 0;
      overflow: hidden;
      background: $primary-light;
      color: $primary-color;
      font-weight: 700;
    }
    .avatar-img {
      width: 100%;
      height: 100%;
    }
    .avatar-meta {
      flex: 1;
      .avatar-title {
        display: block;
        font-size: 15px;
        font-weight: 600;
        margin-bottom: 4px;
      }
      .avatar-tip {
        font-size: 12px;
        color: $text-muted;
      }
    }
    .avatar-arrow {
      color: $text-muted;
      font-size: 20px;
    }
  }

  .form-card {
    @include card;
    padding: 16px;
    border-radius: $radius-lg;
    margin-bottom: 12px;
    .card-title {
      display: block;
      font-size: 15px;
      font-weight: 600;
      margin-bottom: 12px;
    }
    .field {
      margin-bottom: 14px;
      .label {
        display: block;
        font-size: 13px;
        color: $text-secondary;
        margin-bottom: 6px;
      }
      .nick-input {
        width: 100%;
        font-size: 15px;
        color: $text-primary;
      }
      .value {
        display: block;
        font-size: 15px;
        padding: 8px 0;
        &.muted { color: $text-muted; }
      }
    }
    .primary-btn { margin-top: 4px; }
  }
}
</style>
