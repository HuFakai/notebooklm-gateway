import { defineConfig } from 'vitepress'

export default defineConfig({
  title: "NotebookLM Gateway",
  description: "自包含、支持多账户动态路由的 Google NotebookLM 外部 API 网关服务",
  base: "/notebooklm-gateway/", // 如果是部署到 github.io/notebooklm-gateway
  themeConfig: {
    logo: '/logo.png',
    nav: [
      { text: '首页', link: '/' },
      { text: 'API 接口文档', link: '/api' },
      { text: 'GitHub 仓库', link: 'https://github.com/HuFakai/notebooklm-gateway' }
    ],
    sidebar: [
      {
        text: '使用指引',
        items: [
          { text: '快速开始与部署', link: '/' },
          { text: 'API 接口规范', link: '/api' }
        ]
      }
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/HuFakai/notebooklm-gateway' }
    ],
    footer: {
      message: '基于 MIT 协议开源',
      copyright: 'Copyright © 2026-present'
    }
  }
})
