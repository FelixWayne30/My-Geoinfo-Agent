import logging
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class TextProcessor:
    """处理文本并提取地理信息"""

    def __init__(self, qwen_service, amap_service):
        self.qwen_service = qwen_service
        self.amap_service = amap_service

    # 保持原有方法不变
    def process_text(self, text: str) -> Dict[str, Any]:
        """
        处理文本，提取地址、构建行程链

        Args:
            text: 输入文本

        Returns:
            处理结果，包含地址和行程信息
        """
        try:
            # 提取地址
            addresses = self.qwen_service.extract_addresses(text)
            if not addresses:
                return {
                    "success": False,
                    "message": "未能从文本中提取到地址信息",
                    "addresses": []
                }

            logger.info(f"提取到{len(addresses)}个地址")

            # 地理编码
            locations = []
            for addr_info in addresses:
                address = addr_info.get("address", "")
                if not address:
                    continue

                # 地理编码
                location = self.amap_service.geocode(address)
                if location:
                    # 合并地址信息和地理编码结果
                    location.update(addr_info)
                    locations.append(location)
                else:
                    logger.warning(f"地址'{address}'地理编码失败")

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

    # 添加新方法，不修改现有功能
    def sort_locations_by_time(self, locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据时间信息对位置进行排序

        Args:
            locations: 位置列表

        Returns:
            按时间排序后的位置列表
        """
        try:
            # 检查是否有时间信息可排序
            locations_with_time = []

            for location in locations:
                timestamp = None

                # 尝试不同的时间字段
                if 'DateTime' in location:
                    timestamp = location['DateTime']
                elif 'DateTimeOriginal' in location:
                    timestamp = location['DateTimeOriginal']
                elif 'timestamp' in location:
                    timestamp = location['timestamp']

                if timestamp:
                    try:
                        # 尝试解析时间字符串
                        # 支持多种格式，如 "2023:05:20 14:35:42" 或 "2023-05-20 14:35:42"
                        timestamp_str = str(timestamp).replace(':', '-', 2)
                        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        location['parsed_time'] = dt
                        locations_with_time.append(location)
                    except ValueError as e:
                        logger.warning(f"无法解析时间戳 '{timestamp}': {str(e)}")
                        locations_with_time.append(location)
                else:
                    # 没有时间信息的位置
                    locations_with_time.append(location)

            # 按时间排序，没有时间的位置保持原来顺序
            def sort_key(loc):
                return loc.get('parsed_time', datetime.max)

            sorted_locations = sorted(locations_with_time, key=sort_key)

            # 清理临时字段
            for location in sorted_locations:
                if 'parsed_time' in location:
                    del location['parsed_time']

            return sorted_locations

        except Exception as e:
            logger.error(f"排序位置时出错: {str(e)}")
            # 出错时返回原始列表
            return locations