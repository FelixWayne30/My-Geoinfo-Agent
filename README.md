# 智能地理信息提取与可视化系统

一个能够从图片和文本中提取地理位置信息，并在地图上进行可视化展示的智能系统。该系统利用大语言模型（LLM）进行文本分析，能够处理照片中的地理坐标元数据，从自然语言描述中提取地址信息，构建行程路线，并通过高德地图进行可视化展示。


## 🌟 主要功能

- 📷 **图像地理信息提取**：自动从上传图片的EXIF数据中提取GPS坐标
- 🔍 **文本地址识别**：使用大语言模型分析文本，识别并提取其中的地址信息
- 🗺️ **地理编码处理**：将提取的地址信息转换为标准地理坐标
- 🧭 **行程链构建**：根据多个地点信息，构建合理的时间顺序行程链
- 🛣️ **路径可视化**：在高德地图上可视化显示多点路径规划
- 💬 **直观交互界面**：用户友好的聊天式交互界面

## 🔧 技术栈

### 后端

- **框架**：FastAPI
- **对话引擎**：阿里云百炼大模型 (Qwen) 通过 OpenAI 兼容接口
- **地图服务**：高德地图 API
- **图像处理**：ExifRead, Pillow
- **其他库**：Python-dotenv, Requests, Uvicorn

### 前端

- **框架**：React 19
- **构建工具**：Vite
- **地图组件**：高德地图 JavaScript SDK
- **HTTP客户端**：Axios
- **样式**：纯CSS

## 📐 系统架构

系统采用模块化设计，主要包含以下核心组件：

```
┌───────────────────┐     ┌─────────────────────┐     ┌───────────────────┐
│                   │     │                     │     │                   │
│  输入处理模块      │────▶│  智能分析引擎        │────▶│  地图可视化模块   │
│                   │     │                     │     │                   │
└───────────────────┘     └─────────────────────┘     └───────────────────┘
        │                           │                          │
        ▼                           ▼                          ▼
┌───────────────────┐     ┌─────────────────────┐     ┌───────────────────┐
│                   │     │                     │     │                   │
│  图像处理子模块    │     │  地址识别与解析      │     │  高德地图服务接口  │
│                   │     │                     │     │                   │
└───────────────────┘     └─────────────────────┘     └───────────────────┘
```

## 🚀 安装与设置

### 前提条件

- Python 3.8+
- Node.js 14+
- 阿里云百炼（Qwen）API 密钥
- 高德地图开发者密钥

### 后端设置

1. 克隆仓库：

```bash
git clone https://github.com/FelixWayne30/My-Geoinfo-Agent.git
cd geoinfoagent
```

2. 创建并激活虚拟环境：

```bash
python -m venv venv
source venv/bin/activate  # 在Windows上使用: venv\Scripts\activate
```

3. 安装依赖：

```bash
cd backend
pip install -r requirements.txt
```

4. 创建`.env`文件并添加以下内容：

```
DASHSCOPE_API_KEY=your_dashscope_api_key
AMAP_API_KEY=your_amap_api_key
AMAP_SECRET=your_amap_secret  # 可选，用于数字签名
```

5. 启动后端服务：

```bash
python main.py
```

### 前端设置

1. 安装依赖：

```bash
cd frontend
npm install
```

2. 启动开发服务器：

```bash
npm run dev
```

## 💻 使用方法

1. 打开浏览器访问前端应用（默认为 http://localhost:5173）
2. 通过以下方式与系统交互：
   - 输入包含地址信息的文本（例如："我打算从北京出发，经过上海，最后到达广州"）
   - 上传包含GPS元数据的照片
3. 系统会分析输入，提取地理信息，并在地图上显示位置和路线

## 📡 API端点

后端提供以下API端点：

- `GET /` - 系统状态检查
- `POST /process-image` - 处理图片并提取GPS信息
- `POST /process-text` - 处理文本并提取地址信息

## 📋 配置参数

### 环境变量

- `DASHSCOPE_API_KEY` - 阿里云百炼（Qwen）API密钥
- `AMAP_API_KEY` - 高德地图开发者密钥
- `AMAP_SECRET` - 高德地图API密钥（用于请求签名，可选）

## 🧠 模型使用

系统使用阿里云百炼大模型（Qwen）进行以下任务：

1. **地址提取**：从文本中识别出地址信息
2. **行程规划**：根据提取的地点，按合理的顺序排列

## 📝 许可证

[MIT](LICENSE)

## 🙏 致谢

- [阿里云百炼](https://dashscope.aliyun.com) - 提供大模型API
- [高德地图](https://lbs.amap.com) - 提供地图服务API
- [FastAPI](https://fastapi.tiangolo.com) - 后端框架
- [React](https://react.dev) - 前端框架

## 👨‍💻 贡献者

欢迎提交问题和拉取请求！
