import exifread
from PIL import Image
from io import BytesIO
import logging
from typing import Dict, Tuple, Optional, Any

logger = logging.getLogger(__name__)


class ImageProcessor:
    """处理图像并提取地理位置信息"""

    @staticmethod
    def _convert_to_decimal(dms_str: str, ref: str) -> float:
        """
        将DMS(度分秒)格式转换为十进制度数格式

        Args:
            dms_str: EXIF中的度分秒字符串 如 "[41, 53, 23]"
            ref: 方向参考 "N", "S", "E", "W"

        Returns:
            转换后的十进制度数
        """
        # 移除'[', ']'并分割
        parts = dms_str.strip('[]').split(',')
        if len(parts) != 3:
            raise ValueError(f"无效的DMS值: {dms_str}")

        # 解析度、分、秒
        degrees = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])

        # 计算十进制度数
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)

        # 根据参考确定正负符号
        if ref in ['S', 'W']:
            decimal = -decimal

        return decimal

    def extract_gps_from_image(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """
        从图像中提取GPS坐标信息

        Args:
            image_data: 图像二进制数据

        Returns:
            包含经纬度信息的字典或None
        """
        try:
            # 使用exifread提取元数据
            tags = exifread.process_file(BytesIO(image_data))

            # 检查是否有GPS信息
            if not ('GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags and
                    'GPS GPSLatitudeRef' in tags and 'GPS GPSLongitudeRef' in tags):
                logger.warning("图像中未找到GPS信息")
                return None

            # 提取GPS信息
            lat = str(tags['GPS GPSLatitude'])
            lat_ref = str(tags['GPS GPSLatitudeRef'])
            lon = str(tags['GPS GPSLongitude'])
            lon_ref = str(tags['GPS GPSLongitudeRef'])

            # 转换为十进制
            latitude = self._convert_to_decimal(lat, lat_ref)
            longitude = self._convert_to_decimal(lon, lon_ref)

            # 可选：提取GPS时间戳
            timestamp = tags.get('GPS GPSTimeStamp')
            datestamp = tags.get('GPS GPSDateStamp')

            # 构建结果
            result = {
                'latitude': latitude,
                'longitude': longitude,
                'coordinate_system': 'WGS84',  # GPS坐标默认是WGS84系统
            }

            if timestamp and datestamp:
                result['timestamp'] = f"{datestamp} {timestamp}"

            return result

        except Exception as e:
            logger.error(f"提取GPS信息时出错: {str(e)}")
            return None

    def get_image_info(self, image_data: bytes) -> Dict[str, Any]:
        """
        获取图像基本信息

        Args:
            image_data: 图像二进制数据

        Returns:
            图像信息字典
        """
        try:
            img = Image.open(BytesIO(image_data))
            return {
                'format': img.format,
                'size': img.size,
                'mode': img.mode
            }
        except Exception as e:
            logger.error(f"获取图像信息时出错: {str(e)}")
            return {}