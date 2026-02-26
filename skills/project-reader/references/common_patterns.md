# 常见项目结构模式参考

本文档提供常见前端/全栈项目的标准目录结构供参考。

## React 项目标准结构

```
my-react-app/
├── public/                  # 静态资源（不经过打包）
│   ├── index.html
│   └── favicon.ico
├── src/                     # 源代码
│   ├── assets/              # 静态资源（经过打包处理）
│   │   ├── images/
│   │   └── styles/
│   ├── components/         # 通用组件
│   │   ├── Button/
│   │   ├── Modal/
│   │   └── index.js
│   ├── pages/              # 页面组件
│   │   ├── Home/
│   │   └── About/
│   ├── hooks/              # 自定义 Hooks
│   │   ├── useAuth.js
│   │   └── useFetch.js
│   ├── utils/               # 工具函数
│   │   ├── format.js
│   │   └── validate.js
│   ├── services/           # API 服务
│   │   └── api.js
│   ├── store/               # 状态管理
│   │   └── index.js
│   ├── constants/           # 常量定义
│   ├── App.js               # 根组件
│   ├── App.css
│   └── index.js             # 入口文件
├── package.json
└── webpack.config.js         # 或 vite.config.js
```

### React 目录用途说明

| 目录 | 用途 |
|------|------|
| `components/` | 可复用的 UI 组件 |
| `pages/` | 页面级组件（对应路由） |
| `hooks/` | 封装可复用的状态逻辑 |
| `utils/` | 纯函数工具 |
| `services/` | API 请求封装 |
| `store/` | 状态管理（Redux/Zustand/Context） |
| `constants/` | 常量配置 |
| `assets/` | 图片、字体等资源 |

---

## Next.js 项目结构

### App Router (推荐)

```
my-next-app/
├── src/
│   ├── app/                  # App Router
│   │   ├── layout.tsx       # 根布局
│   │   ├── page.tsx         # 首页
│   │   ├── globals.css      # 全局样式
│   │   ├── about/
│   │   │   └── page.tsx    # /about 页面
│   │   ├── api/              # API 路由
│   │   │   └── hello/
│   │   │       └── route.ts
│   │   └── (marketing)/     # 路由组
│   │       └── page.tsx
│   ├── components/           # 组件（Server/Client）
│   │   ├── Button.tsx
│   │   └── Counter.tsx
│   ├── lib/                 # 工具函数
│   │   ├── db.ts
│   │   └── utils.ts
│   └── types/               # TypeScript 类型
├── public/                   # 静态资源
├── package.json
├── next.config.js
└── tsconfig.json
```

### Pages Router (传统)

```
my-next-app/
├── pages/
│   ├── _app.tsx            # 根组件
│   ├── _document.tsx      # HTML 模板
│   ├── index.tsx          # 首页
│   ├── about.tsx          # /about
│   └── api/
│       └── hello.ts       # /api/hello
├── src/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   └── styles/
├── public/
└── package.json
```

---

## Vue 项目标准结构

```
my-vue-app/
├── public/                   # 静态资源
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── assets/              # 资源
│   │   ├── images/
│   │   └── styles/
│   ├── components/          # 组件
│   │   ├── Common/
│   │   │   └── Button.vue
│   │   └── Business/
│   ├── views/              # 页面
│   │   ├── Home.vue
│   │   └── About.vue
│   ├── router/             # 路由配置
│   │   └── index.js
│   ├── store/               # 状态管理
│   │   └── index.js
│   ├── api/                 # API 接口
│   │   └── user.js
│   ├── utils/               # 工具函数
│   ├── directives/           # 自定义指令
│   ├── filters/              # 自定义过滤器
│   ├── App.vue              # 根组件
│   └── main.js              # 入口文件
├── package.json
└── vue.config.js
```

---

## 常见目录模式对比

| 目录 | React | Vue | 说明 |
|------|-------|-----|------|
| 页面 | `pages/` | `views/` | 路由对应页面 |
| 组件 | `components/` | `components/` | 通用组件 |
| 状态 | `store/` | `store/` | 状态管理 |
| API | `services/` | `api/` | 接口封装 |
| 样式 | `styles/` | `assets/styles/` | 样式文件 |

---

## 关键配置文件

| 文件 | 用途 |
|------|------|
| `package.json` | 项目依赖配置 |
| `tsconfig.json` | TypeScript 配置 |
| `vite.config.js` | Vite 构建配置 |
| `webpack.config.js` | Webpack 构建配置 |
| `.eslintrc.js` | ESLint 代码规范 |
| `.prettierrc` | Prettier 格式化配置 |
| `.env` | 环境变量 |

---

## 附加说明

- 目录命名统一使用 `kebab-case`（短横线命名）
- 组件文件使用 `PascalCase`（首字母大写）
- hooks 使用 `use` 前缀（如 `useAuth`）
- 工具函数使用 `camelCase`
