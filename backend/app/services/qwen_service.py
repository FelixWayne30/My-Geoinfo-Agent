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
        从文本中提取并完善地址信息

        Args:
            text: 输入文本

        Returns:
            提取的地址列表，每个地址包含完整的结构化信息
        """
        try:
            # 构建更智能的提示词
            messages = [
                {"role": "system",
                 "content": """你是一个专业的地理信息提取助手，擅长从文本中识别和完善地址信息。
                 请遵循以下规则：
                 1. 默认假设所有地点都在同一城市内，除非文本明确提到不同城市
                 2. 尽可能完善地址信息，添加省份、城市等缺失信息
                 3. 推断地址所在城市，使用中国地名习惯
                 4. 如果文本未明确指出城市，从上下文和地点特征推断最可能的城市
                 5. 只返回JSON格式的结果，不要有其他解释"""},
                {"role": "user", "content": f"""
    请从以下文本中提取所有地址信息，并完善为尽可能完整的地址。每个地址应包含省份、城市、区县和详细地址。
    返回格式应为JSON数组:
    [
      {{
        "address": "完整地址文本",
        "province": "省份",
        "city": "城市",
        "district": "区县",
        "detail": "详细地址",
        "time_mentioned": "相关时间信息(如有)",
        "confidence": 0.9  // 地址识别置信度，0-1之间
      }}
    ]

    文本: {text}
    """}
            ]

            # 调用模型
            content = self._call_model(
                messages=messages,
                temperature=0.2,
                max_tokens=2000
            )

            if not content:
                return []

            # 尝试解析返回的JSON
            try:
                # 提取JSON部分
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
                 "content": """你是一个专业的行程规划助手，擅长安排地点的访问顺序。
                 请按照以下规则构建行程:
                 1. 如果有明确的时间提及，按时间顺序排列
                 2. 如果地点在不同城市，按照文本描述的顺序排列
                 3. 如果在同一城市内，根据地理位置和合理的访问路线进行排序
                 4. 考虑地址自然语言描述中的行程逻辑，比如"从A出发，经过B，最后到达C"
                 5. 只返回JSON格式的结果，不要有其他解释"""},
                {"role": "user", "content": f"""
    请分析以下地点列表和原始文本，构建一个最合理的行程链:

    地点列表: {locations_json}

    原始文本描述: {text if text else "无文本描述"}

    请返回完整的行程链JSON数组，排序后的地点序列应包含所有原始信息。
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