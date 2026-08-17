<template>
  <el-config-provider :locale="locale">
    <div class="app-container">
      <el-container>
        <el-header class="app-header">
          <div class="header-left">
            <h1 class="logo">GM China 舆情监控</h1>
          </div>
          <div class="header-nav">
            <el-radio-group v-model="activeBrand" @change="switchBrand" size="large">
              <el-radio-button :value="0">全部</el-radio-button>
              <el-radio-button :value="1">别克</el-radio-button>
              <el-radio-button :value="2">凯迪拉克</el-radio-button>
              <el-radio-button :value="3">雪佛兰</el-radio-button>
            </el-radio-group>
          </div>
          <div class="header-right">
            <el-dropdown>
              <span class="user-info">
                <el-icon><User /></el-icon>
                管理员
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item>系统设置</el-dropdown-item>
                  <el-dropdown-item divided>退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>

        <el-main class="app-main">
          <router-view :brand-id="activeBrand" />
        </el-main>
      </el-container>
    </div>
  </el-config-provider>
</template>

<script setup>
import { ref } from 'vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

const locale = zhCn
const activeBrand = ref(0)

function switchBrand(val) {
  // 品牌切换后，子组件通过 prop 响应
}
</script>

<style lang="scss">
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: #f0f2f5;
  color: #333;
}

.app-container {
  min-height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  height: 60px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  .logo {
    font-size: 18px;
    font-weight: 600;
    color: #1a1a2e;
    white-space: nowrap;
  }
}

.header-nav {
  flex: 1;
  display: flex;
  justify-content: center;
}

.header-right {
  .user-info {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    color: #666;
  }
}

.app-main {
  padding: 20px 24px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}
</style>
