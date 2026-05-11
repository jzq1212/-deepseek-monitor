# DeepSeek Monitor

桌面端 DeepSeek API 余额 & 用量可视化监控工具。

## 截图

深色数据大屏风格，ECharts 图表实时展示余额趋势、模型定价、Token 估算。

## 功能

- 余额查询 & 历史趋势图
- 多 API Key 管理
- 历史余额补录（手动记录每日余额，推算消费）
- 模型定价参考
- Token 可用量估算
- 30 分钟自动刷新
- 打包为单个 exe，无需安装 Python

## 快速开始（用户）

下载 `DeepSeekMonitor_v1.0.zip` → 解压 → 双击 `DeepSeekMonitor.exe` → 浏览器自动打开。

## 快速开始（开发者）

```bash
# 后端
cd backend
pip install -r requirements.txt
python server.py

# 前端（可选，开发时用）
cd frontend
npm install
npm run dev        # 开发模式，热更新
npm run build      # 生产构建
```

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + ECharts + Vite |
| 后端 | FastAPI + uvicorn |
| 打包 | PyInstaller (单文件 exe) |
| 图表 | ECharts (折线图、柱状图) |

## 结构

```
backend/
  server.py       FastAPI 后端
  api.py          DeepSeek API 封装
  config.py       Key 加密存储
frontend/
  src/App.vue     主大屏界面
  src/style.css    深色主题
```

## API 说明

目前 DeepSeek 仅提供 [余额查询 API](https://api-docs.deepseek.com/api/get-user-balance) (`/user/balance`)，用量/消费接口尚未公开。本工具通过持续记录余额快照来推算每日消费。

## License

MIT
