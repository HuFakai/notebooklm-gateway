import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'NotebookLM Gateway',
  description: '基于 notebooklm-py 稳定版公开 API 的多租户薄网关',
  base: '/notebooklm-gateway/',
  cleanUrls: true,
  lastUpdated: true,
  themeConfig: {
    outline: { level: [2, 3], label: '本页目录' },
    nav: [
      { text: '首页', link: '/' },
      { text: 'REST API', link: '/api' },
      { text: '架构', link: '/architecture' },
      { text: '迁移', link: '/migration' },
      { text: 'GitHub', link: 'https://github.com/HuFakai/notebooklm-gateway' }
    ],
    sidebar: [
      {
        text: '指南',
        items: [
          { text: '快速开始', link: '/' },
          { text: 'REST API', link: '/api' },
          { text: '架构决策', link: '/architecture' },
          { text: '旧版迁移', link: '/migration' }
        ]
      }
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/HuFakai/notebooklm-gateway' }
    ],
    search: { provider: 'local' },
    footer: {
      message: '基于 MIT 协议开源 · 非 Google 官方产品',
      copyright: 'Copyright © 2026-present'
    }
  }
})
