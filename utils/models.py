from pydantic import BaseModel, Field
from typing import Optional, List
#这是做数据格式验证的，如果不符合就会报错
class Activity(BaseModel):
    """用于存储从活动海报或通知中提取的结构化信息。"""
    activity_name: str = Field(description="活动的官方或主要名称,用中文")
    activity_date: str = Field(description="活动举办的具体日期,转换为标准格式dd/mm/yy")
    activity_location: str = Field(description="活动举办的物理地点。如果图片中未明确指出，请根据海报内容（如组织单位）进行推断")
    activity_content: str = Field(description="用一段话简要概括活动的核心内容，包含哪些主要的活动环节或亮点。文字需精炼，在30字以内")
    #participants: Optional[List[str]] = Field(description="The participants of the activity")

class Experience(BaseModel):
    """用于存储从图片提取的生活经验，可能关于职场，人生，学习等方面的结构化信息"""
    experience_type: Optional[str] = Field(description="经验信息的类型，包括工作，人生，情感，学习等，你可以根据图片内容进行判断")
    experience_content: Optional[str] = Field(description="对核心内容的总结少于300字，要求尽可能体现经验最重要地价值")
    reason: Optional[str] = Field(description="如果无法提取有效的经验类型和内容，请在此字段中说明原因，其他字段留空。")
 #   lessons_learned: str = Field(description="The lessons learned from the experience")

class Paper(BaseModel):
    """用于从包含论文、文章或新闻的截图中提取结构化信息。"""
    paper_title: str = Field(description="图片中提到的主要论文、文章或研究的标题。如果找不到明确的标题，请根据内容生成一个最合适的标题。")
 #   authors: List[str] = Field(description="The authors of the paper")
    abstract: str = Field(description="**严格**根据图片中的文字进行摘要。只总结图片中明确存在的描述性文字150字内。如果图片中除了标题之外，没有任何关于内容的描述、介绍或摘要性文字，必须返回且仅返回字符串 '无明确内容'。禁止根据标题进行任何形式的推断或创造。")
#    keywords: Optional[List[str]] = Field(description="The keywords of the paper")

# class AcademicResearch(BaseModel):
#     """Represents information about academic research."""
#     research_field: str = Field(description="The field of the research")
#     research_title: str = Field(description="The title of the research")
#     research_content: str = Field(description="The summary of the research content")
#     research_methods: Optional[List[str]] = Field(description="The research methods used")