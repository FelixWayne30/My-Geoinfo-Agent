import os
import json
import logging
from typing import Dict, Any, List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class QwenService:
    """阿里云百炼大模型服务封装 (OpenAI 兼容模式)"""

    def __init__(self):
        # 获取API密钥
        self.api_key = os.getenv('DASHSCOPE_API_KEY')
        if not self.api_key:
            logger.warning("未设置DASHSCOPE_API_KEY环境变量，百炼服务将无法正常工作")

        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        # 设置默认模型
        self.model = "qwen-plus"  # 可选: qwen-max, qwen-turbo, qwen-plus 等

    def _call_model(self, messages, temperature=0.7, max_tokens=1000):
        """调用百炼API (OpenAI兼容模式)"""
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # 返回生成的内容
            return completion.choices[0].message.content

        except Exception as e:
            logger.error(f"API调用出错: {str(e)}")
            return None

    def extract_addresses(self, text: str) -> List[Dict[str, Any]]:
        """
        从文本中提取地址信息

        Args:
            text: 输入文本

        Returns:
            提取的地址列表，每个地址包含地址文本和可能的其他信息
        """
        try:
            # 构建消息
            messages = [
                {"role": "system",
                 "content": "你是一个专业的地理信息提取助手，擅长从文本中识别出地址信息。请只返回JSON格式的结果，不要有其他解释。"},
                {"role": "user", "content": f"""
请从以下文本中提取所有地址信息，并按JSON格式返回。每个地址应包含地址文本和可能的提及时间。
不要有任何前导文字或后续解释，只返回JSON数组。

文本: {text}

返回格式应为:
[
  {{
    "address": "地址文本",
    "time_mentioned": "相关时间信息(如有)"
  }}
]

如果没有找到地址，返回空数组 []。
"""}
            ]

            # 调用模型
            content = self._call_model(
                messages=messages,
                temperature=0.2,
                max_tokens=1000
            )

            if not content:
                return []

            # 尝试解析返回的JSON
            try:
                # 提取JSON部分 (可能包含在```json和```之间)
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].strip()
                else:
                    json_str = content

                addresses = json.loads(json_str)
                return addresses
            except json.JSONDecodeError as e:
                logger.error(f"解析模型返回的JSON失败: {str(e)}, 内容: {content}")
                return []

        except Exception as e:
            logger.error(f"地址提取过程中出错: {str(e)}")
            return []

    def build_itinerary(self, locations: List[Dict[str, Any]], text: str = None) -> List[Dict[str, Any]]:
        """
        构建行程链，将地点按时间顺序排列

        Args:
            locations: 地点列表
            text: 原始文本上下文(可选)

        Returns:
            排序后的行程链
        """
        try:
            # 如果只有一个地点或没有地点，直接返回
            if len(locations) <= 1:
                return locations

            # 构建提示词
            locations_json = json.dumps(locations, ensure_ascii=False)

            # 构建消息
            messages = [
                {"role": "system",
                 "content": "你是一个专业的行程规划助手，擅长安排地点的访问顺序。请只返回JSON格式的结果，不要有其他解释。"},
                {"role": "user", "content": f"""
请分析以下地点列表，按照合理的时间顺序重新排列，构建一个行程链。
如果有明确的时间提及，按时间顺序排列；如果没有，根据地点之间的地理位置和合理的行程安排进行排序。

地点列表: {locations_json}

原始文本描述: {text if text else "无文本描述"}

返回完整的行程链JSON数组，包含所有原始信息，但顺序已调整。
不要添加任何额外的说明或解释，只返回JSON数组。
"""}
            ]

            # 调用模型
            content = self._call_model(
                messages=messages,
                temperature=0.2,
                max_tokens=2000
            )

            if not content:
                return locations

            # 尝试解析返回的JSON
            try:
                # 提取JSON部分
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].strip()
                else:
                    json_str = content

                itinerary = json.loads(json_str)
                return itinerary
            except json.JSONDecodeError as e:
                logger.error(f"解析行程排序JSON失败: {str(e)}, 内容: {content}")
                return locations  # 出错时返回原始列表

        except Exception as e:
            logger.error(f"构建行程链过程中出错: {str(e)}")
            return locations  # 出错时返回原始列表