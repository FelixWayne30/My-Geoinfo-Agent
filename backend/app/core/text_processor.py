import logging
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)


class TextProcessor:
    """处理文本并提取地理信息"""

    def __init__(self, qwen_service, amap_service):
        self.qwen_service = qwen_service
        self.amap_service = amap_service

    def process_text(self, text: str) -> Dict[str, Any]:
        """
        处理文本，提取地址、构建行程链

        Args:
            text: 输入文本

        Returns:
            处理结果，包含地址和行程信息
        """
        try:
            # 提取地址 - 现在返回的是更完整的地址信息
            addresses = self.qwen_service.extract_addresses(text)
            if not addresses:
                return {
                    "success": False,
                    "message": "未能从文本中提取到地址信息",
                    "addresses": []
                }

            logger.info(f"提取到{len(addresses)}个地址")

            # 地理编码 - 传入完整的地址信息
            locations = []
            for addr_info in addresses:
                # 地理编码现在接收完整的地址信息字典
                location = self.amap_service.geocode(addr_info)
                if location:
                    # 保留原始地址信息
                    location['original_address'] = addr_info.get('address', '')
                    location['time_mentioned'] = addr_info.get('time_mentioned', '')
                    locations.append(location)
                else:
                    logger.warning(f"地址'{addr_info.get('address', '')}'地理编码失败")

            if not locations:
                return {
                    "success": False,
                    "message": "提取的地址无法地理编码",
                    "addresses": addresses
                }

            # 构建行程链
            itinerary = self.qwen_service.build_itinerary(locations, text)

            # 如果有两个以上地点，生成路径
            route_data = None
            if len(itinerary) >= 2:
                origin = f"{itinerary[0]['longitude']},{itinerary[0]['latitude']}"
                destination = f"{itinerary[-1]['longitude']},{itinerary[-1]['latitude']}"

                # 处理途经点
                waypoints = None
                if len(itinerary) > 2:
                    waypoint_list = []
                    for loc in itinerary[1:-1]:
                        waypoint_list.append(f"{loc['longitude']},{loc['latitude']}")
                    waypoints = ";".join(waypoint_list)

                # 规划路径
                route_data = self.amap_service.plan_route(
                    origin=origin,
                    destination=destination,
                    waypoints=waypoints
                )

            # 生成静态地图URL
            static_map_url = self.amap_service.get_static_map(itinerary)

            return {
                "success": True,
                "message": f"成功提取{len(locations)}个地址信息并生成行程",
                "addresses": addresses,
                "locations": locations,
                "itinerary": itinerary,
                "route": route_data,
                "static_map_url": static_map_url
            }

        except Exception as e:
            logger.error(f"文本处理过程中出错: {str(e)}")
            return {
                "success": False,
                "message": f"处理出错: {str(e)}",
                "addresses": []
            }