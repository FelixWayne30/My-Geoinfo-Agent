import logging
from io import BytesIO
from typing import Dict, Optional, Any
from PIL import Image, ExifTags
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)


class ImageProcessor:
    """处理图像并提取地理位置信息"""

    def extract_gps_from_image(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """从图像中提取GPS坐标信息"""
        try:
            # 使用PIL打开图像
            img = Image.open(BytesIO(image_data))

            # 检查是否有EXIF数据
            if not hasattr(img, '_getexif') or img._getexif() is None:
                logger.warning("图片没有EXIF数据")
                return None

            # 获取所有EXIF数据
            exif_data = img._getexif()
            logger.info(f"EXIF标签: {[ExifTags.TAGS.get(tag, tag) for tag in exif_data.keys()]}")

            # 找到GPS信息对应的标签
            gps_info = None
            for tag, value in exif_data.items():
                tag_name = ExifTags.TAGS.get(tag, tag)
                if tag_name == 'GPSInfo':
                    gps_info = value
                    break

            if not gps_info:
                logger.warning("图片中没有GPS信息")
                return None

            # 打印GPS信息标签
            gps_tags = {key: ExifTags.GPSTAGS.get(key, key) for key in gps_info.keys()}
            logger.info(f"GPS标签: {gps_tags}")

            # 解析GPS数据
            lat_ref = lon_ref = None
            lat_deg = lon_deg = None

            for key, val in gps_info.items():
                tag_name = ExifTags.GPSTAGS.get(key, key)
                if tag_name == 'GPSLatitudeRef':
                    lat_ref = val
                elif tag_name == 'GPSLatitude':
                    lat_deg = val
                elif tag_name == 'GPSLongitudeRef':
                    lon_ref = val
                elif tag_name == 'GPSLongitude':
                    lon_deg = val

            logger.info(f"GPS原始数据: lat_ref={lat_ref}, lat_deg={lat_deg}, lon_ref={lon_ref}, lon_deg={lon_deg}")

            if not (lat_ref and lon_ref and lat_deg and lon_deg):
                logger.warning("GPS信息不完整")
                return None

            # 转换为十进制坐标
            def to_decimal(degree_data, ref):
                d, m, s = degree_data
                # 处理不同类型的数据
                if isinstance(d, tuple):
                    d = float(d[0]) / float(d[1])
                else:
                    d = float(d)

                if isinstance(m, tuple):
                    m = float(m[0]) / float(m[1])
                else:
                    m = float(m)

                if isinstance(s, tuple):
                    s = float(s[0]) / float(s[1])
                else:
                    s = float(s)

                decimal = d + (m / 60.0) + (s / 3600.0)
                if ref in ['S', 'W']:
                    decimal = -decimal
                return decimal

            latitude = to_decimal(lat_deg, lat_ref)
            longitude = to_decimal(lon_deg, lon_ref)

            logger.info(f"成功提取GPS坐标: 纬度={latitude}, 经度={longitude}")

            return {
                'latitude': latitude,
                'longitude': longitude,
                'coordinate_system': 'WGS84'
            }

        except Exception as e:
            logger.error(f"提取GPS信息时出错: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def get_image_info(self, image_data: bytes) -> Dict[str, Any]:
        """获取图像基本信息，包括时间等EXIF数据"""
        try:
            img = Image.open(BytesIO(image_data))
            info = {
                'format': img.format,
                'size': img.size,
                'mode': img.mode
            }

            # 获取EXIF信息
            if hasattr(img, '_getexif') and img._getexif():
                exif = img._getexif()
                if exif:
                    # 添加所有有用的EXIF信息
                    for tag, tag_value in exif.items():
                        tag_name = ExifTags.TAGS.get(tag, str(tag))
                        # 保留时间相关信息，用于排序
                        if tag_name in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized', 'Make', 'Model']:
                            info[tag_name] = tag_value

                    # 尝试格式化时间信息以便前端展示
                    if 'DateTimeOriginal' in info or 'DateTime' in info:
                        timestamp = info.get('DateTimeOriginal', info.get('DateTime', ''))
                        try:
                            dt = datetime.strptime(timestamp, '%Y:%m:%d %H:%M:%S')
                            info['formatted_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            logger.warning(f"无法解析时间格式: {timestamp}")

            return info

        except Exception as e:
            logger.error(f"获取图像信息时出错: {str(e)}")
            return {}