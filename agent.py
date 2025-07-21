from typing import List, Dict, Any, TypedDict, Annotated
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator
import json


from utils.tools import classify_image, extract_info_from_image, save_data_to_db, get_llm, get_vlm, google_search

# --- Agent State ---
class AgentState(TypedDict):
    """Represents the state of the agent, carrying messages through the graph.

    Attributes:
        messages: A list of messages, new messages are added to this list.
    """
    messages: Annotated[List[BaseMessage], operator.add]

# --- Agent Nodes ---
#节点以最近的state为输入，并返回新增的状态字典
def llm_agent(state: AgentState):
    """Primary agent node that invokes the LLM with tools.

    This node receives the current state, binds a set of tools to the LLM,
    and invokes the model with the current message history. The model's
    response, which may include tool calls, is then added to the state.

    Args:
        state: The current state of the graph, containing the message history.

    Returns:
        A dictionary with the new message from the LLM to be added to the state.
    """
    llm = get_llm()
    tools = [classify_image, extract_info_from_image, save_data_to_db,google_search]
    llm_with_tools = llm.bind_tools(tools)
    response = llm_with_tools.invoke(state['messages']) #会不会太多，全部对话历史？
    return {"messages": [response]}

def reflection_node(state: AgentState):
    """Reflects on the output of a tool call to ensure quality and correctness.

    This node examines the last tool message. If the tool was 'extract_info_from_image'
    and the abstract is missing, it suggests a web search. For other tools, it uses
    an LLM to check if the tool's output is satisfactory. If not, it injects a
    corrective message back into the graph.

    Args:
        state: The current state of the graph.

    Returns:
        An optional dictionary containing a new message to guide the next step,
        or None if the tool output is satisfactory.
    """
    tool_message = state['messages'][-1]
    tool_request_message = state['messages'][-2]

    if not isinstance(tool_message, ToolMessage) or not isinstance(tool_request_message, AIMessage):
        return
    print(tool_message)
    if tool_message.name == "extract_info_from_image":
        try:
            data = json.loads(tool_message.content)
            if data.get('paper_title') and (data.get('abstract') == '无明确描述' or not data.get('abstract')):
                print(f"--- Reflection: Abstract is missing for '{data['paper_title']}'. Suggesting search. ---")
                # 返回一条消息，明确建议LLM进行搜索
                suggestion = f"The information extraction for the paper '{data['paper_title']}' was successful, but the abstract is missing. Please use the google_search tool to find a summary for this paper."
                return {"messages": [AIMessage(content=suggestion)]}
        except (json.JSONDecodeError, AttributeError):
            pass # 解析失败则忽略，走默认路径


    reflection_prompt = f"""
    You are a quality assurance expert. Please review the result from a previous tool call.
    The original task was to call the tool: `{tool_request_message.tool_calls[0]['name']}` with arguments `{tool_request_message.tool_calls[0]['args']}`.
    The tool produced this output: {tool_message.content}
    
    Is this result satisfactory? Does it look complete and correct given the task?
    If the result is good, respond with just the word 'CONTINUE'.
    If there is an error or the result is unsatisfactory, briefly explain the issue and suggest a correction.
    """
    llm = get_llm()
    response = llm.invoke(reflection_prompt)
    
    print(f"--- Reflection ---\n{response.content}\n---------------------")

    if "CONTINUE" in response.content:
        return
    else:
        return {"messages": [AIMessage(content=f"Reflection on last action: {response.content}")]}

# --- Graph Definition (remains the same) ---

workflow = StateGraph(AgentState)
workflow.add_node("llm_agent", llm_agent)
#工具节点，可能需要定义不同类型的工具节点？
vlm_expert_node = ToolNode([classify_image, extract_info_from_image, save_data_to_db,google_search])
workflow.add_node("vlm_expert", vlm_expert_node)
workflow.add_node("reflection", reflection_node)
#定义为起点
workflow.set_entry_point("llm_agent")

def route_after_llm(state: AgentState):
    """Routes the workflow after the main LLM agent has run.

    If the last message from the LLM contains tool calls, it routes to the
    'vlm_expert' (tool execution) node. Otherwise, it ends the workflow.

    Args:
        state: The current state of the graph.

    Returns:
        A string indicating the next node to execute ('vlm_expert' or END).
    """
    if state['messages'][-1].tool_calls:
        return "vlm_expert"
    else:
        return END

def route_after_tool(state: AgentState):
    """Routes the workflow after a tool has been executed.

    If the tool execution resulted in an error or a specific condition (like a
    missing abstract), it routes to the 'reflection' node for quality control.
    Otherwise, it routes back to the 'llm_agent' to continue the process.

    Args:
        state: The current state of the graph.

    Returns:
        A string indicating the next node to execute ('reflection' or 'llm_agent').
    """
    last_message = state['messages'][-1]
    if isinstance(last_message, ToolMessage) and ("error" in last_message.content.lower() or "failed" in last_message.content.lower() or "abstract" in last_message.content.lower()):
        return "reflection"
    else:
        return "llm_agent"



workflow.add_conditional_edges(
    "llm_agent",
    route_after_llm,  # 这个是返回一个信号，下面的dict根据信号去执行下个节点的链接
    {"vlm_expert": "vlm_expert", END: END}
)
workflow.add_conditional_edges(
    "vlm_expert",
    route_after_tool,
    {"reflection": "reflection", "llm_agent": "llm_agent"}
)
workflow.add_edge('reflection', 'llm_agent')

#把定义好的图编译
app = workflow.compile()

# --- Graph Invocation (remains the same) ---
def run_agent(image_path: str):
    """Runs the agent workflow for a given image.

    This function initializes the agent with a prompt to analyze the specified
    image. It then streams the execution of the graph, printing each step's
    output to the console.

    Args:
        image_path: The local file path to the image to be analyzed.
    """
    initial_prompt = f"""
    Please analyze the image at the following path: {image_path}
    1. First, classify the image to determine its type.
    2. Second, based on the type, extract the relevant information. 
    Specifically, for "论文或学术研究" type image, if there is not enough content description extracted from the image, you should use search tool to get the content description.

    3. Finally, save the extracted information to the database 
    Let me know when you are done.
    """
    
    inputs = {"messages": [HumanMessage(content=initial_prompt)]}
    
    #以流的方式运行，就是每个节点完成就会有当前的state的结果，可以实时观察
    for event in app.stream(inputs, stream_mode="values"):
        event["messages"][-1].pretty_print()

