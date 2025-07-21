import os
import json
import yaml
import sqlite3
from datetime import datetime
from typing import Type, Dict, Any

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from .config_loader import get_active_model_config, config
from langchain_community.tools import GoogleSearchRun
from langchain_community.utilities import GoogleSearchAPIWrapper






from utils.models import Activity, Experience, Paper

# --- Helper Functions ---

def get_vlm():
    """Initializes and returns the active Vision Language Model (VLM).

    This function reads the configuration to determine which VLM is active,
    retrieves the necessary API key from environment variables, and instantiates
    the corresponding VLM client.

    Returns:
        An instance of the configured VLM client (e.g., ChatTongyi).

    Raises:
        ValueError: If the required API key is not found in the environment variables.
        NotImplementedError: If the configured VLM is not supported.
    """
    vlm_config = get_active_model_config('vlm')
    api_key_name = vlm_config['api_key_name']
    api_key = os.getenv(api_key_name)

    if not api_key:
        raise ValueError(f"API key '{api_key_name}' not found in environment variables.")

    # This part can be extended if you support other VLMs
    if 'qwen' in vlm_config['model_name']:
        return ChatTongyi(model_name=vlm_config['model_name'], dashscope_api_key=api_key)
    else:
        raise NotImplementedError(f"VLM for '{vlm_config['model_name']}' is not implemented.")

def get_llm():
    """Initializes and returns the active Large Language Model (LLM).

    This function reads the configuration to determine which LLM is active,
    retrieves the necessary API key from environment variables, and instantiates
    the corresponding LLM client.

    Returns:
        An instance of the configured LLM client (e.g., ChatOpenAI).

    Raises:
        ValueError: If the required API key is not found in the environment variables.
        NotImplementedError: If the configured LLM is not supported.
    """
    llm_config = get_active_model_config('llm')
    api_key_name = llm_config['api_key_name']
    api_key = os.getenv(api_key_name)

    if not api_key:
        raise ValueError(f"API key '{api_key_name}' not found in environment variables.")

    # This part can be extended to support other LLMs like those from OpenAI, Anthropic, etc.
    if 'deepseek' in llm_config['model_name']:
        return ChatOpenAI(
            model=llm_config['model_name'],
            openai_api_key=api_key,
            openai_api_base=llm_config['api_base_url']
        )
    else:
        raise NotImplementedError(f"LLM for '{llm_config['model_name']}' is not implemented.")

def parse_json_from_response(response_content: str) -> Dict[str, Any]:
    """Extracts a JSON object from a model's string response.

    It handles responses where the JSON is embedded within a markdown code block
    (e.g., ```json\n{...}\n```) or as a plain string.

    Args:
        response_content: The raw string response from the language model.

    Returns:
        A dictionary parsed from the JSON string.

    Raises:
        json.JSONDecodeError: If parsing the JSON fails.
    """
    try:
        # A common pattern is for the model to return JSON in a markdown block
        start = response_content.find('```json\n{') + len('```json\n')
        end = response_content.rfind('}\n```') + 1
        if start == -1 + len('```json\n'): # Fallback if markdown block is not found
            start = response_content.find('{')
            end = response_content.rfind('}') + 1
        
        json_str = response_content[start:end]
        return json.loads(json_str)
    except (json.JSONDecodeError, IndexError) as e:
        print(f"Error parsing JSON: {e}\nResponse: {response_content}")
        raise

# --- Agent Tools ---

@tool
def classify_image(image_path: str) -> str:
    """Analyzes an image to classify its content into a predefined category.

    This tool uses a VLM to determine if the image content relates to an 'activity',
    'experience', or 'paper' based on descriptions in a configuration file.

    Args:
        image_path: The local file path to the image to be classified.

    Returns:
        A string representing the classified category (e.g., '活动', '经验', '论文').
    """
    base_dir = r'd:\projects\image detector'
    conf_path = os.path.join(base_dir, 'config', 'categories_config.yaml')
    with open(conf_path, encoding='utf-8') as f:
        categories = yaml.safe_load(f)['categories']

    categories_prompt = """请判断图像内容最符合下面哪种description的需求，选择最符合的类型
    """
    for cat in categories:
        categories_prompt += f"\n- {cat['name']}: {', '.join(cat['description'])}"
    
    categories_prompt += """\n严格按照下面json格式输出
    {"分析":"分析属于哪个类型的过程","类型":"类型名称"}
    """
    
    message = HumanMessage(content=[
        {"text": categories_prompt},
        {"image": image_path}
    ])
    
    vlm = get_vlm()
    result = vlm.invoke([message])
    print(result)
    print(type(result.content[0]))
    parsed_result = parse_json_from_response(result.content[0]['text'])
    return parsed_result.get('类型', '未知')

@tool
def extract_info_from_image(image_path: str, image_type: str) -> Dict[str, Any]:
    """Extracts structured information from an image based on its classified type.

    This tool uses a VLM and a corresponding Pydantic model to extract and
    validate information from an image. The specific information to extract is
    determined by the `image_type`.

    Args:
        image_path: The local file path to the image.
        image_type: The category of the image ('活动', '经验', '论文'), which
            determines the data schema to use for extraction.

    Returns:
        A dictionary containing the extracted and validated information.
        Returns a dictionary with an error message if parsing or validation fails.

    Raises:
        ValueError: If the `image_type` is not supported.
    """
    type_map: Dict[str, Type[BaseModel]] = {
        '活动': Activity,
        '经验': Experience,
        '论文': Paper # Assuming Paper and AcademicResearch can use the same prompt for now
    }

    if image_type not in type_map:
        raise ValueError(f"Unsupported image type: {image_type}")

    model_class = type_map[image_type]
    #这个函数挺不错的功能，限制输出的数据格式,自动修改prompt,会很消耗token吗
    vlm = get_vlm()#.with_structured_output(model_class)
    print(vlm)

    # Load prompts from the new prompt_config.yaml
    base_dir = r'd:\projects\image detector'
    conf_path = os.path.join(base_dir, 'config', 'prompt_config.yaml')
    with open(conf_path, encoding='utf-8') as f:
        prompt_config = yaml.safe_load(f)
    
    base_prompt = prompt_config.get('base_prompt', '')
    instruction = ""
    for p in prompt_config.get('prompts', []):
        if p['name'] == image_type:
            instruction = p['instruction']
            break

 #   prompt = f"你是一个从图片中提取结构化信息的专家。请仔细分析提供的图片，并从中提取出关键信息。严格按照要求的 JSON 格式输出，不要包含任何 markdown 标记、额外的解释、注释或任何非 JSON 文本."
    print(base_prompt+instruction)
    message = HumanMessage(content=[
        {"type": "text", "text": base_prompt+instruction},  # Explicitly specify type
        {"type": "image", "image": image_path}  # Proper format for image
    ])

    result = vlm.invoke([message])
    raw_content = result.content[0]['text']
    try:
        # Attempt to parse the JSON from the raw string response
        parsed_json = parse_json_from_response(raw_content)
        # Validate with Pydantic model
        validated_data = model_class(**parsed_json)
        return validated_data.dict()
    except Exception as e:
        print(f"Failed to parse or validate JSON: {e}")
        # Return a dictionary with an error message, or handle as needed
        return {"error": "Failed to extract structured information", "details": str(e), "raw_output": raw_content}

    #print(result)
    return result.dict()



@tool
def google_search(query: str) -> str:
    """Performs a Google search and returns the results.

    This tool is a wrapper around the Google Search API and is useful for
    finding information on current events or supplementing knowledge.

    Args:
        query: The search query string.

    Returns:
        A string containing the search results.
    """
   
#
    search_wrapper = GoogleSearchAPIWrapper()
    search = GoogleSearchRun(api_wrapper=search_wrapper)
    search_query = f"{query} site:arxiv.org OR site:springer.com"
    return search.run(search_query)

@tool
def save_data_to_db(data: Dict[str, Any], image_type: str) -> str:
    """Saves extracted data to a SQLite database.

    This tool connects to a SQLite database using the path from environment
    variables. It dynamically determines the table name based on the `image_type`
    and creates the table if it doesn't exist before inserting the data.

    Args:
        data: A dictionary containing the data to be saved.
        image_type: The category of the data, used to determine the table name.

    Returns:
        A string indicating the success or failure of the operation.
    """
    table_name = config['database_tables'].get(image_type, config['database_tables']['default'])
    db_path = os.getenv("DB_PATH", "database.db")
    conn = None  # Initialize conn to None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        columns_defs = []
        for key, value in data.items():
            if isinstance(value, bool): col_type = "INTEGER"  # SQLite uses INTEGER for booleans
            elif isinstance(value, int): col_type = "INTEGER"
            elif isinstance(value, float): col_type = "REAL"
            elif isinstance(value, str):
                try:
                    datetime.strptime(value, '%Y-%m-%d')
                    col_type = "DATE"
                except ValueError:
                    col_type = "TEXT"
            else:
                col_type = "TEXT" # Default for lists, etc.
            columns_defs.append(f'"{key}" {col_type}')
        
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS "{table_name}" (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                {', '.join(columns_defs)}
            )
        """
        cursor.execute(create_sql)
        
        columns = '", "'.join(data.keys())
        values_placeholder = ', '.join(['?'] * len(data))
        insert_sql = f'INSERT INTO "{table_name}" ("{columns}") VALUES ({values_placeholder})'
        
        # Convert lists to JSON strings for storage
        values = [json.dumps(v) if isinstance(v, list) else v for v in data.values()]

        cursor.execute(insert_sql, tuple(values))
        conn.commit()
        return f"Data successfully saved to table '{table_name}'."
    except Exception as e:
        if conn:
            conn.rollback()
        return f"Database operation failed: {e}"
    finally:
        if conn:
            conn.close()


def check_upcoming_events(query: str = "") -> str:
    """
    Checks the 'activity' table in the database for events scheduled within the next 10 days and returns a reminder.
    """
    db_path = os.getenv("DB_PATH", "database.db")
    conn = None # Initialize conn to None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query for events between today and 10 days from now
        query = """
            SELECT activity_name, activity_date 
            FROM activity_log 
            WHERE date(activity_date) 
            BETWEEN date('now') AND date('now', '+10 days')
        """
        cursor.execute(query)
        events = cursor.fetchall()

        if not events:
            return "未来10天内没有即将开始的活动。"

        reminders = []
        for event in events:
            reminders.append(f"- {event[0]} (日期: {event[1]})")
        
        return "提醒：以下活动即将在10天内开始：\n" + "\n".join(reminders)

    except sqlite3.OperationalError as err:
        # Handle cases where the table might not exist yet
        if "no such table" in str(err):
            return "'activity' 表不存在，无法查询即将开始的活动。"
        return f"数据库查询失败: {err}"
    except Exception as e:
        return f"检查活动时发生未知错误: {e}"
    finally:
        if conn:
            conn.close()