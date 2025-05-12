from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = FastAPI(title="智能地理信息提取与可视化系统")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "智能地理信息提取与可视化系统API"}

@app.post("/process-image")
async def process_image(file: UploadFile = File(...)):
    """处理上传的图片，提取地理位置信息"""
    return {"message": "图片处理功能正在开发中"}

@app.post("/process-text")
async def process_text(text: str = Form(...)):
    """处理文本，提取地址信息"""
    return {"message": "文本处理功能正在开发中"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)