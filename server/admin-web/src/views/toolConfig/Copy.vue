<template>
  <el-card shadow="never" class="copy-card">
    <div class="title">文案配置</div>
    <p>这里用于集中维护小程序工具的名称、简介、分类和使用说明，后续也可扩展到各类工具的提示词文案。</p>
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="文案管理入口已预留"
      description="当前小程序工具目录仍由项目内置数据提供。本页先作为工具配置的独立入口，待工具目录管理模型确定后，再接入新增、编辑、排序与发布。"
    />
  </el-card>
</template>

<script setup lang="ts"></script>

<style scoped>
.copy-card { border: 1px solid var(--admin-border); }
.title { color: var(--admin-text); font-size: 16px; font-weight: 650; }
p { color: var(--admin-text-muted); font-size: 13px; line-height: 1.7; }
</style>
