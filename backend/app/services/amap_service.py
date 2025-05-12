import os
import json
import logging
import hashlib
import urllib.parse
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger(__name__)


class AMapService:
    """高德地图服务封装"""

    def __init__(self):
        self.api_key = os.getenv('AMAP_API_KEY')
        if not self.api_key:
            logger.warning("未设置AMAP_API_KEY环境变量，高德地图服务将无法正常工作")

        self.base_url = "https://restapi.amap.com/v3"

    def _generate_signature(self, params: Dict[str, str]) -> str:
        """
        生成数字签名（高德地图Web服务API数字签名）
        https://lbs.amap.com/api/webservice/guide/create-project/signature
        """
        api_secret = os.getenv('AMAP_SECRET')
        if not api_secret:
            return ""

        # 将参数排序
        sorted_params = sorted(params.items())

        # 将所有参数按key=value的格式拼接
        param_str = ''
        for key, value in sorted_params:
            param_str += f"{key}={value}&"
        param_str = param_str[:-1]  # 去除最后的&符号

        # 拼接密钥
        str_to_sign = param_str + api_secret

        # 使用MD5算法计算签名
        signature = hashlib.md5(str_to_sign.encode()).hexdigest()

        return signature

    # backend/app/services/amap_service.py 优化地理编码函数

    def geocode(self, address: str) -> Optional[Dict[str, Any]]:
        """
        地理编码，将地址转换为经纬度坐标
        https://lbs.amap.com/api/webservice/guide/api/georegeo
        """
        try:
            # 清理地址文本
            address = address.strip()
            if not address:
                logger.warning("地址为空")
                return None

            logger.info(f"正在地理编码地址: {address}")

            # 构建参数
            params = {
                'key': self.api_key,
                'address': address,
                'output': 'JSON',
                # 添加city参数可提高准确度
                'city': '',  # 可以根据上下文设置默认城市
            }

            # 生成签名
            api_secret = os.getenv('AMAP_SECRET')
            if api_secret:
                params['sig'] = self._generate_signature(params)

            # 发送请求
            response = requests.get(f"{self.base_url}/geocode/geo", params=params, timeout=5)
            data = response.json()

            # 记录原始响应
            logger.info(f"地理编码响应: {data}")

            # 检查结果
            if data.get('status') == '1' and data.get('geocodes') and len(data['geocodes']) > 0:
                result = data['geocodes'][0]
                # 提取经纬度
                location = result.get('location', '')
                if location:
                    lng, lat = location.split(',')
                    geo_result = {
                        'latitude': float(lat),
                        'longitude': float(lng),
                        'formatted_address': result.get('formatted_address', ''),
                        'province': result.get('province', ''),
                        'city': result.get('city', ''),
                        'district': result.get('district', ''),
                        'adcode': result.get('adcode', ''),
                        'level': result.get('level', '')
                    }
                    logger.info(f"地理编码成功: {address} -> [{lng},{lat}]")
                    return geo_result

            logger.warning(f"地理编码失败，地址: {address}, 响应: {data}")
            return None

        except Exception as e:
            logger.error(f"地理编码过程中出错: {str(e)}")
            return None

    def plan_route(self,
                   origin: str,
                   destination: str,
                   waypoints: str = None,
                   mode: str = 'driving') -> Optional[Dict[str, Any]]:
        """
        路径规划
        https://lbs.amap.com/api/webservice/guide/api/direction

        Args:
            origin: 起点坐标(lng,lat)
            destination: 终点坐标(lng,lat)
            waypoints: 途经点坐标(lng,lat)，多个用";"分隔
            mode: 出行方式，driving-驾车, walking-步行, transit-公交, bicycling-骑行
        """
        try:
            # 选择正确的端点
            endpoint_map = {
                'driving': 'direction/driving',
                'walking': 'direction/walking',
                'transit': 'direction/transit/integrated',
                'bicycling': 'direction/bicycling'
            }
            endpoint = endpoint_map.get(mode, 'direction/driving')

            # 构建基本参数
            params = {
                'key': self.api_key,
                'origin': origin,
                'destination': destination,
                'output': 'JSON',
                'extensions': 'all'  # 返回详细路径信息
            }

            # 添加可选参数
            if waypoints:
                params['waypoints'] = waypoints

            # 驾车路径规划的特有参数
            if mode == 'driving':
                params['strategy'] = '10'  # 速度优先

            # 生成签名
            api_secret = os.getenv('AMAP_SECRET')
            if api_secret:
                params['sig'] = self._generate_signature(params)

            # 发送请求
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, params=params)
            data = response.json()

            # 检查结果
            if data.get('status') == '1':
                return data

            logger.warning(f"路径规划失败，参数: {params}, 响应: {data}")
            return None

        except Exception as e:
            logger.error(f"路径规划过程中出错: {str(e)}")
            return None

    def get_static_map(self, locations: List[Dict[str, Any]], zoom: int = 13) -> str:
        """
        生成静态地图URL
        https://lbs.amap.com/api/webservice/guide/api/staticmaps
        """
        try:
            if not locations:
                return ""

            # 提取位置坐标
            markers = []
            for loc in locations:
                if 'longitude' in loc and 'latitude' in loc:
                    coord = f"{loc['longitude']},{loc['latitude']}"
                    markers.append(coord)

            if not markers:
                return ""

            # 构建参数
            params = {
                'key': self.api_key,
                'size': '750*500'  # 图片大小
            }

            # 单点和多点处理
            if len(markers) == 1:
                # 单点地图
                params['location'] = markers[0]
                params['zoom'] = str(zoom)
                params['markers'] = f"mid,0xFF0000,A:{markers[0]}"
            else:
                # 多点地图 - 需要特别处理

                # 1. 构建标记参数
                marker_parts = []
                for i, marker in enumerate(markers):
                    # 根据位置设置不同颜色
                    if i == 0:  # 起点
                        color = '0xFF0000'  # 红色
                    elif i == len(markers) - 1:  # 终点
                        color = '0x00FF00'  # 绿色
                    else:  # 途经点
                        color = '0x0000FF'  # 蓝色

                    # 使用字母作为标记
                    label = chr(65 + i) if i < 26 else str(i + 1)
                    marker_parts.append(f"mid,{color},{label}:{marker}")

                # 将标记参数用"|"连接
                params['markers'] = "|".join(marker_parts)

                # 2. 添加路径连线
                # 注意：路径线必须符合特定格式，宽度,颜色,透明度,线形
                if len(markers) >= 2:
                    path_str = ';'.join(markers)
                    # 宽度为5像素，蓝色，透明度1.0，实线
                    params['path'] = f"5,0x0000FF,1,0:{path_str}"

            # 生成签名
            api_secret = os.getenv('AMAP_SECRET')
            if api_secret:
                # 确保所有参数值都是字符串
                string_params = {k: str(v) for k, v in params.items()}
                params['sig'] = self._generate_signature(string_params)

            # 构建URL - 确保正确编码
            base_url = "https://restapi.amap.com/v3/staticmap"
            query_parts = []

            for k, v in params.items():
                # 对值进行URL编码，但保留某些特殊字符
                if k in ['markers', 'path']:
                    # 这些参数需要特殊处理，因为它们包含特殊符号如冒号、竖线等
                    encoded_v = v.replace('|', '%7C')
                    query_parts.append(f"{k}={encoded_v}")
                else:
                    query_parts.append(f"{k}={urllib.parse.quote(str(v))}")

            query_string = "&".join(query_parts)
            full_url = f"{base_url}?{query_string}"

            logger.info(f"生成的静态地图URL: {full_url}")
            return full_url

        except Exception as e:
            logger.error(f"生成静态地图过程中出错: {str(e)}")
            return ""

    # backend/app/services/amap_service.py 中的prepare_map_data方法

    def prepare_map_data(self, locations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        准备前端地图渲染所需的数据

        Args:
            locations: 位置点列表

        Returns:
            包含地图渲染所需数据的字典
        """
        if not locations:
            return {"success": False, "message": "无位置数据"}

        # 记录日志以便调试
        logger.info(f"准备地图数据，共{len(locations)}个位置点")

        # 提取位置点信息
        map_points = []
        for i, loc in enumerate(locations):
            if 'longitude' in loc and 'latitude' in loc:
                # 确保经纬度是浮点数
                lng = float(loc['longitude'])
                lat = float(loc['latitude'])

                # 确定点类型
                point_type = "起点" if i == 0 else "终点" if i == len(locations) - 1 else "途经点"

                # 获取地址信息
                address = loc.get('formatted_address', '') or loc.get('address', '')
                logger.info(f"点{i + 1}: 类型={point_type}, 坐标=[{lng},{lat}], 地址={address}")

                map_points.append({
                    "lnglat": [lng, lat],
                    "name": address,
                    "type": point_type,
                    "index": i
                })

        # 如果有多个点，获取路径规划数据
        route_data = None
        if len(map_points) >= 2:
            try:
                # 构建起点终点坐标
                start = f"{map_points[0]['lnglat'][0]},{map_points[0]['lnglat'][1]}"
                end = f"{map_points[-1]['lnglat'][0]},{map_points[-1]['lnglat'][1]}"

                # 处理途经点
                waypoints = None
                if len(map_points) > 2:
                    waypoint_coords = []
                    for point in map_points[1:-1]:
                        waypoint_coords.append(f"{point['lnglat'][0]},{point['lnglat'][1]}")
                    waypoints = ";".join(waypoint_coords)
                    logger.info(f"途经点: {waypoints}")

                # 获取路径规划数据
                route_result = self.plan_route(start, end, waypoints)

                if route_result and route_result.get('status') == '1':
                    route_data = route_result
                    logger.info("路径规划数据获取成功")
                else:
                    logger.warning(f"路径规划失败: {route_result}")
            except Exception as e:
                logger.error(f"获取路径数据出错: {str(e)}")

        result = {
            "success": True,
            "mapKey": self.api_key,
            "points": map_points,
            "routeData": route_data
        }

        # 记录完整的结果（仅用于调试）
        logger.info(
            f"地图数据准备完成: 成功={result['success']}, 点数={len(result['points'])}, 是否有路线={result['routeData'] is not None}")

        return result