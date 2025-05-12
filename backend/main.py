import os
import logging
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv
from app.services.qwen_service import QwenService
from app.services.amap_service import AMapService
from app.core.image_processor import ImageProcessor
from app.core.text_processor import TextProcessor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 创建FastAPI应用
app = FastAPI(title="智能地理信息提取与可视化系统")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 依赖项
def get_qwen_service():
    return QwenService()


def get_amap_service():
    return AMapService()


def get_image_processor():
    return ImageProcessor()


def get_text_processor(
        qwen_service: QwenService = Depends(get_qwen_service),
        amap_service: AMapService = Depends(get_amap_service)
):
    return TextProcessor(qwen_service, amap_service)


@app.get("/")
async def root():
    return {"message": "智能地理信息提取与可视化系统API"}


@app.post("/process-image")
async def process_image(
        file: UploadFile = File(...),
        image_processor: ImageProcessor = Depends(get_image_processor),
        amap_service: AMapService = Depends(get_amap_service)
):
    """处理上传的图片，提取地理位置信息"""
    try:
        # 读取图片数据
        image_data = await file.read()

        # 提取GPS信息
        gps_info = image_processor.extract_gps_from_image(image_data)

        if not gps_info:
            return JSONResponse(
                status_code=200,
                content={"success": False, "message": "未能从图片中提取到GPS信息"}
            )

        # 获取图片基本信息
        image_info = image_processor.get_image_info(image_data)

        # 生成静态地图
        static_map_url = amap_service.get_static_map([gps_info])

        return {
            "success": True,
            "message": "成功从图片中提取GPS信息",
            "gps_info": gps_info,
            "image_info": image_info,
            "static_map_url": static_map_url
        }
    except Exception as e:
        logger.error(f"处理图片时出错: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"处理图片时出错: {str(e)}"}
        )


@app.post("/process-text")
async def process_text(
    text: str = Form(...),
    text_processor: TextProcessor = Depends(get_text_processor)
):
    """处理文本，提取地址信息"""
    try:
        # 处理文本
        result = text_processor.process_text(text)
        return result
    except Exception as e:
        logger.error(f"处理文本时出错: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"处理文本时出错: {str(e)}"}
        )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)