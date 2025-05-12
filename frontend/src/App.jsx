import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import './App.css'
import MapViewer from './components/MapViewer'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const fileInputRef = useRef(null)
  const messagesEndRef = useRef(null)

  // 自动滚动到最新消息
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 添加初始欢迎消息
  useEffect(() => {
    setMessages([
      {
        type: 'assistant',
        content: '您好！我是智能地理助手。您可以：\n- 发送包含地址信息的文本\n- 上传含有地理坐标的照片\n我将帮您提取地理信息并进行可视化。'
      }
    ])
  }, [])

  // 自动调整文本框高度
  useEffect(() => {
    const textarea = document.querySelector('textarea');
    if (!textarea) return;

    const adjustHeight = () => {
      textarea.style.height = 'auto';
      textarea.style.height = textarea.scrollHeight + 'px';
    };

    textarea.addEventListener('input', adjustHeight);

    // 初始调整
    adjustHeight();

    return () => {
      textarea.removeEventListener('input', adjustHeight);
    };
  }, [input]);

  // 处理文本输入提交
  const handleSubmit = async () => {
    if (!input.trim()) return

    // 添加用户消息到聊天记录
    setMessages(prev => [...prev, { type: 'human', content: input }])

    const userInput = input
    setInput('')
    setLoading(true)

    try {
      // 调用后端API处理文本
      const formData = new FormData()
      formData.append('text', userInput)

      const response = await axios.post('http://localhost:8000/process-text',
  formData,
  { headers: { 'Content-Type': 'multipart/form-data' } }
);

// 详细记录地图数据
console.log("API返回完整数据:", response.data);

// 构建回复消息
let content = response.data.message || '处理完成';
let mapData = null;

// 检查并使用map_data字段
if (response.data.map_data && response.data.map_data.success) {
  mapData = response.data.map_data;
  console.log("使用地图数据:", mapData);
}

// 添加系统回复到聊天记录
setMessages(prev => [...prev, {
  type: 'assistant',
  content,
  mapData
}]);
    } catch (error) {
      console.error('请求失败:', error)
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: '抱歉，处理您的请求时出错了。'
      }])
    } finally {
      setLoading(false)
    }
  }

  // 处理图片上传
  const handleImageUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    // 添加用户消息到聊天记录（显示图片预览）
    const reader = new FileReader()
    reader.onload = async (event) => {
      setMessages(prev => [...prev, {
        type: 'human',
        content: '上传了图片:',
        image: event.target.result
      }])

      // 创建FormData对象上传图片
      const formData = new FormData()
      formData.append('file', file)

      setLoading(true)
      try {
        // 调用后端API处理图片
        const response = await axios.post('http://localhost:8000/process-image',
          formData,
          { headers: { 'Content-Type': 'multipart/form-data' } }
        )

        // 构建回复消息
        let content = response.data.message || '处理完成'
        let mapData = null

        // 如果有地图数据
        if (response.data.map_data && response.data.map_data.success) {
          mapData = response.data.map_data
        }

        // 添加系统回复到聊天记录
        setMessages(prev => [...prev, {
          type: 'assistant',
          content,
          mapData
        }])
      } catch (error) {
        console.error('上传失败:', error)
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: '抱歉，处理图片时出错了。'
        }])
      } finally {
        setLoading(false)
        // 清空文件输入，允许重复上传同一文件
        e.target.value = null
      }
    }
    reader.readAsDataURL(file)
  }

  // 键盘回车发送
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="chat-app">
      <div className="messages-container">
        {messages.map((msg, index) => (
          <div key={index} className={`message-row ${msg.type}`}>
            <div className="message">
              {msg.image && (
                <div className="image-preview">
                  <img src={msg.image} alt="上传的图片" />
                </div>
              )}
              <p>{msg.content}</p>

              {/* 使用地图组件显示地图 */}
              {msg.mapData && (
                <div className="map-container">
                  <MapViewer mapData={msg.mapData} />
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="message-row assistant">
            <div className="message loading">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-container">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入您的问题或地址信息..."
          disabled={loading}
          rows={1}
          autoFocus
        />
        <div className="buttons">
          <button
            className="upload-button"
            onClick={() => fileInputRef.current.click()}
            disabled={loading}
            title="上传图片"
          >
            <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
          </button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleImageUpload}
            accept="image/*"
            style={{ display: 'none' }}
          />
          <button
            className="send-button"
            onClick={handleSubmit}
            disabled={loading || !input.trim()}
            title="发送消息"
          >
            <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}

export default App