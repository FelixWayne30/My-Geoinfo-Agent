# backend/app/services/amap_service.py
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

    def geocode(self, address: str) -> Optional[Dict[str, Any]]:
        """
        地理编码，将地址转换为经纬度坐标
        https://lbs.amap.com/api/webservice/guide/api/georegeo
        """
        try:
            # 构建参数
            params = {
                'key': self.api_key,
                'address': address,
                'output': 'JSON'
            }

            # 生成签名
            api_secret = os.getenv('AMAP_SECRET')
            if api_secret:
                params['sig'] = self._generate_signature(params)

            # 发送请求
            response = requests.get(f"{self.base_url}/geocode/geo", params=params)
            data = response.json()

            # 检查结果
            if data.get('status') == '1' and data.get('geocodes') and len(data['geocodes']) > 0:
                result = data['geocodes'][0]
                # 提取经纬度
                location = result.get('location', '')
                if location:
                    lng, lat = location.split(',')
                    return {
                        'latitude': float(lat),
                        'longitude': float(lng),
                        'formatted_address': result.get('formatted_address', ''),
                        'province': result.get('province', ''),
                        'city': result.get('city', ''),
                        'district': result.get('district', ''),
                        'adcode': result.get('adcode', ''),
                        'level': result.get('level', '')
                    }

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

    # backend/app/services/amap_service.py 中修改 get_static_map 方法

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