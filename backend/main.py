import os
import logging
from typing import List
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

# 打印环境变量（调试用）
print(f"DASHSCOPE_API_KEY设置状态: {'已设置' if os.getenv('DASHSCOPE_API_KEY') else '未设置'}")
print(f"AMAP_API_KEY设置状态: {'已设置' if os.getenv('AMAP_API_KEY') else '未设置'}")

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

        # 记录图片信息
        logger.info(f"接收到图片：{file.filename}，大小：{len(image_data)} 字节")

        # 提取GPS信息
        gps_info = image_processor.extract_gps_from_image(image_data)

        if not gps_info:
            logger.warning(f"图片 {file.filename} 未能提取到GPS信息")
            return JSONResponse(
                status_code=200,
                content={"success": False, "message": "未能从图片中提取到GPS信息"}
            )

        # 获取图片基本信息
        image_info = image_processor.get_image_info(image_data)

        # 记录成功提取的信息
        logger.info(f"成功从图片 {file.filename} 提取到GPS信息：{gps_info}")

        # 生成静态地图
        static_map_url = amap_service.get_static_map([gps_info])

        # 准备地图数据
        map_data = amap_service.prepare_map_data([gps_info])

        return {
            "success": True,
            "message": "成功从图片中提取GPS信息",
            "gps_info": gps_info,
            "image_info": image_info,
            "static_map_url": static_map_url,
            "map_data": map_data
        }
    except Exception as e:
        # 详细记录异常
        logger.error(f"处理图片 {file.filename if file else 'unknown'} 时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"处理图片时出错: {str(e)}"}
        )


@app.post("/process-text")
async def process_text(
        text: str = Form(...),
        text_processor: TextProcessor = Depends(get_text_processor),
        amap_service: AMapService = Depends(get_amap_service)
):
    """处理文本，提取地址信息"""
    try:
        # 处理文本
        result = text_processor.process_text(text)

        # 如果处理成功，添加地图数据
        if result.get("success") and result.get("itinerary"):
            map_data = amap_service.prepare_map_data(result["itinerary"])
            result["map_data"] = map_data

        return result
    except Exception as e:
        logger.error(f"处理文本时出错: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"处理文本时出错: {str(e)}"}
        )


@app.post("/process-images")
async def process_images(
        files: List[UploadFile] = File(...),
        image_processor: ImageProcessor = Depends(get_image_processor),
        amap_service: AMapService = Depends(get_amap_service),
        text_processor: TextProcessor = Depends(get_text_processor)
):
    """处理多张图片，提取地理位置信息并构建行程链"""
    try:
        # 记录请求信息
        logger.info(f"收到批量处理请求，共{len(files)}张图片")

        # 存储所有图片的位置信息
        locations = []

        # 处理每张图片
        for file in files:
            image_data = await file.read()
            logger.info(f"处理图片: {file.filename}, 大小: {len(image_data)}字节")

            # 提取GPS信息
            gps_info = image_processor.extract_gps_from_image(image_data)
            if not gps_info:
                logger.warning(f"图片 {file.filename} 未能提取到GPS信息")
                continue

            # 获取图片基本信息(包含时间信息)
            image_info = image_processor.get_image_info(image_data)

            # 构建位置信息
            location = {
                **gps_info,
                **image_info,
                "filename": file.filename,
                "name": file.filename,  # 添加名称用于地图标记
                "address": gps_info.get("formatted_address", "未知地点")
            }

            locations.append(location)

        if not locations:
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "message": "未能从任何图片中提取到GPS信息"
                }
            )

        # 按照时间排序(如果存在时间信息)
        sorted_locations = text_processor.sort_locations_by_time(locations)

        # 生成行程路线
        route_data = None
        if len(sorted_locations) >= 2:
            # 准备起点、终点和途经点
            origin = f"{sorted_locations[0]['longitude']},{sorted_locations[0]['latitude']}"
            destination = f"{sorted_locations[-1]['longitude']},{sorted_locations[-1]['latitude']}"

            waypoints = None
            if len(sorted_locations) > 2:
                waypoint_list = []
                for loc in sorted_locations[1:-1]:
                    waypoint_list.append(f"{loc['longitude']},{loc['latitude']}")
                waypoints = ";".join(waypoint_list)

            # 规划路径
            route_data = amap_service.plan_route(
                origin=origin,
                destination=destination,
                waypoints=waypoints
            )

        # 准备地图数据
        map_data = amap_service.prepare_map_data(sorted_locations)

        # 如果有路径数据，添加到地图数据中
        if route_data:
            map_data["routeData"] = route_data

        return {
            "success": True,
            "message": f"成功从{len(locations)}张图片中提取位置信息并构建行程",
            "locations": sorted_locations,
            "map_data": map_data
        }

    except Exception as e:
        logger.error(f"批量处理图片出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"处理图片时出错: {str(e)}"}
        )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)