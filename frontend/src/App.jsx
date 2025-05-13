import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import './App.css'
import MapViewer from './components/MapViewer'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedImages, setSelectedImages] = useState([])
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

  // 处理图片选择
  const handleImageSelect = (e) => {
    const files = Array.from(e.target.files)
    if (!files.length) return

    // 将选择的文件添加到状态中
    const newImages = files.map(file => ({
      file,
      preview: URL.createObjectURL(file)
    }))

    setSelectedImages(prev => [...prev, ...newImages])

    // 清空文件输入，允许重复选择
    e.target.value = null
  }

  // 处理批量图片上传和行程生成
  const handleImagesUpload = async () => {
    if (!selectedImages.length) return

    // 添加用户消息到聊天记录（显示图片预览）
    setMessages(prev => [...prev, {
      type: 'human',
      content: `上传了${selectedImages.length}张图片构建行程:`,
      images: selectedImages.map(img => img.preview)
    }])

    setLoading(true)

    try {
      // 创建FormData对象，包含所有图片
      const formData = new FormData()

      // 添加所有图片文件
      selectedImages.forEach(imageData => {
        formData.append('files', imageData.file)
      })

      console.log(`正在上传${selectedImages.length}张图片进行行程规划...`)

      // 调用后端批量处理API
      const response = await axios.post('http://localhost:8000/process-images',
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 60000 // 增加超时时间
        }
      )

      console.log("后端返回数据:", response.data)

      if (response.data.success) {
        // 生成详细的回复内容
        const locations = response.data.locations || []
        let content = response.data.message || '处理完成'

        // 添加位置信息到回复内容
        if (locations.length > 0) {
          content += '\n\n行程路线：'
          locations.forEach((loc, index) => {
            const time = loc.formatted_time || loc.DateTime || '未知时间'
            content += `\n${index + 1}. ${loc.filename || '位置'+index} (${time})`
          })
        }

        // 添加系统回复到聊天记录
        setMessages(prev => [...prev, {
          type: 'assistant',
          content,
          mapData: response.data.map_data
        }])
      } else {
        // 处理失败
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: response.data.message || '处理图片时出错'
        }])
      }

    } catch (error) {
      console.error('批量上传失败:', error)
      console.error('错误详情:', error.response ? error.response.data : '无详细信息')

      setMessages(prev => [...prev, {
        type: 'assistant',
        content: `抱歉，处理图片时出错了。错误信息: ${error.message || '未知错误'}`
      }])
    } finally {
      // 清空已选图片
      setSelectedImages([])
      setLoading(false)
    }
  }

  // 处理单张图片上传
  const handleSingleImageUpload = async (imageData) => {
    try {
      const formData = new FormData()
      formData.append('file', imageData.file)

      console.log("正在上传单张图片:", imageData.file.name)

      const response = await axios.post('http://localhost:8000/process-image',
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 30000
        }
      )

      console.log("后端返回数据:", response.data)

      // 构建回复消息
      let content = response.data.message || '处理完成'
      let mapData = null

      if (response.data.map_data && response.data.map_data.success) {
        mapData = response.data.map_data
      }

      // 添加系统回复到聊天记录
      setMessages(prev => [...prev, {
        type: 'assistant',
        content,
        mapData
      }])

      return true
    } catch (error) {
      console.error('上传失败:', error)

      setMessages(prev => [...prev, {
        type: 'assistant',
        content: `抱歉，处理图片时出错了。错误信息: ${error.message || '未知错误'}`
      }])

      return false
    }
  }

  // 键盘回车发送
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  // 移除已选图片
  const removeSelectedImage = (index) => {
    setSelectedImages(prev => {
      const newImages = [...prev];
      URL.revokeObjectURL(newImages[index].preview);
      newImages.splice(index, 1);
      return newImages;
    });
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
              {msg.images && (
                <div className="images-preview">
                  {msg.images.map((imgSrc, imgIndex) => (
                    <div key={imgIndex} className="image-preview">
                      <img src={imgSrc} alt={`上传的图片 ${imgIndex+1}`} />
                    </div>
                  ))}
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

      {/* 图片选择预览区域 */}
      {selectedImages.length > 0 && (
        <div className="selected-images-container">
          <div className="selected-images">
            {selectedImages.map((img, index) => (
              <div key={index} className="selected-image">
                <img src={img.preview} alt={`所选图片 ${index+1}`} />
                <button
                  className="remove-image"
                  onClick={() => removeSelectedImage(index)}
                >
                  &times;
                </button>
              </div>
            ))}
          </div>
          <button
            className="upload-selected-button"
            onClick={handleImagesUpload}
            disabled={loading}
          >
            上传并构建行程链 ({selectedImages.length}张照片)
          </button>
        </div>
      )}

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
            onChange={handleImageSelect}
            accept="image/*"
            multiple
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