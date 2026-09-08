<template>
  <div class="page">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="时评文章" name="articles">
        <ArticlesTab />
      </el-tab-pane>
      <el-tab-pane label="规范词分类" name="categories">
        <TermCategoriesTab />
      </el-tab-pane>
      <el-tab-pane label="骨架模版" name="skeletons">
        <SkeletonsTab />
      </el-tab-pane>
      <el-tab-pane label="论证方法" name="argumentMethods">
        <ArgumentMethodsTab />
      </el-tab-pane>
      <el-tab-pane label="句式类型" name="sentenceTypes">
        <SentenceTypesTab />
      </el-tab-pane>
      <el-tab-pane label="三刀导入" name="threeKnife">
        <ThreeKnifeImportTab />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ArticlesTab from './ArticlesTab.vue'
import TermCategoriesTab from './TermCategoriesTab.vue'
import SkeletonsTab from './SkeletonsTab.vue'
import ArgumentMethodsTab from './ArgumentMethodsTab.vue'
import SentenceTypesTab from './SentenceTypesTab.vue'
import ThreeKnifeImportTab from './ThreeKnifeImportTab.vue'

const activeTab = ref('articles')
</script>
