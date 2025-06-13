from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

import requests
import json
import os

# Global variables
api_hostname = os.environ.get("HOME_API_BASE", "http://192.168.4.1") # Takes the default AP mode IP of ESP8266
ollama_base = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
ollama_model = api_hostname = os.environ.get("OLLAMA_MODEL", "llama3.2") # Uses llama3.2 as default if not provided

# Tool definitions
@tool
def get_led_status() -> str:
    """
    Returns the current status of LEDs
    No argument is required for this function
    """

    url = f"{api_hostname}/led/stat"
    respMsg = "inital"
    try:
        response = requests.get(url)
        response.raise_for_status()
        response_data = response.json()
        if "message" in response_data:
            respMsg = response_data['message']
        else:
            respMsg = f"Raw response content: {response.text}"
    except requests.exceptions.HTTPError as http_err:
        respMsg = f"HTTP error occurred: {http_err} - Response: {response.text}"
    except requests.exceptions.ConnectionError as conn_err:
        respMsg = f"Connection error occurred: {conn_err}"
    except requests.exceptions.Timeout as timeout_err:
        respMsg = f"Timeout error occurred: {timeout_err}"
    except requests.exceptions.RequestException as req_err:
        respMsg = f"An unexpected error occurred: {req_err}"
    except json.JSONDecodeError:
        print("Error: Could not decode JSON from response.")
        respMsg = f"Raw response content: {response.text}"
    return respMsg

@tool
def change_led_status(led_number: int, led_on: bool) -> str:
    """
    Turns a LED on or off depending on request and return the status reponse after execution

    Args:
        led_number (int): The selected LED number
        led_on (bool): A boolean value to set the status, true to turn ON and false to turn OFF
    """

    url = f"{api_hostname}/led/control"
    jsonBody = '''
    {
      "ledNum": 1,
      "ledOn": false
    }
    '''
    respMsg = "inital"
    apiHeader = {'content-type': 'application/json'}
    reqBodyObj = json.loads(jsonBody)
    reqBodyObj["ledNum"] = led_number
    reqBodyObj["ledOn"] = led_on
    reqBodyMain = json.dumps(reqBodyObj)

    try:
        response = requests.post(url, data = reqBodyMain, headers = apiHeader) # , verify=False  >>Remove verify in prod
        response.raise_for_status()
        response_data = response.json()
        if "message" in response_data:
            respMsg = response_data['message']
        else:
            respMsg = f"Raw response content: {response.text}"
    except requests.exceptions.HTTPError as http_err:
        respMsg = f"HTTP error occurred: {http_err} - Response: {response.text}"
    except requests.exceptions.ConnectionError as conn_err:
        respMsg = f"Connection error occurred: {conn_err}"
    except requests.exceptions.Timeout as timeout_err:
        respMsg = f"Timeout error occurred: {timeout_err}"
    except requests.exceptions.RequestException as req_err:
        respMsg = f"An unexpected error occurred: {req_err}"
    except json.JSONDecodeError:
        print("Error: Could not decode JSON from response.")
        respMsg = f"Raw response content: {response.text}"
    return respMsg

# Define model & tools
model = ChatOllama(model=ollama_model, base_url=ollama_base)
tools = [get_led_status, change_led_status]

# Prompt guidence
promt = """
You are Micky, an expert AI Agent. You can control the LEDs (Home Automation) using the given tools.

**Guidelines for Home Automation**

1. **Getting LED status**
   * You have a tool `get_led_status` to get status of all LEDs that are available.
   * You can provide answer based on user's query for any specific LED number.
   * If the user do not specify a LED number, you can tell them the entire result.

2. **Changing LED status**
   * You have another important tool `change_led_status` to change the status of selected LED i.e. you can send turn `on` or `off` request.
   * User might say `turn off the led two`, you need to make a call to the tool & specify the number as integer.
   * When a user do not specify a LED number when requesting to change the status, ask them to specify before you can use the tool.
   * Whenever you are in doubt, please ask the user to clarify it.
   * You will receive a response message from the tool and you should show the same response to user.
   * Please do not make any status assumption if you do not get proper response from tools, follow the responses properly.

"""

## Define a ChatPromptTemplate with a system message
prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", promt),
        MessagesPlaceholder("messages"), # This is crucial for handling chat history
    ]
)

# Create the agent with the ChatPromptTemplate
agent = create_react_agent(
    model=model,
    tools=tools,
    prompt=prompt_template
)

# Convert gradio history to langchain message history
def gradio_to_langchain_messages(gradio_history: list[list[str, str | None]]):
    """
    Converts Gradio chat history (list of dicts) into a list of LangChain BaseMessage objects.
    """
    langchain_messages = []
    for user_msg, bot_msg in gradio_history:
        if user_msg is not None:
            langchain_messages.append(HumanMessage(content=user_msg))
        if bot_msg is not None:
            langchain_messages.append(AIMessage(content=bot_msg))
    return langchain_messages


# This function is the entrypoint to the AI
def chat_with_langchain_agent(message: str, history: list[list[str, str | None]]):
    """
    This function acts as the bridge between Gradio UI and LangChain agent.
    It takes the current user message and the full Gradio history,
    converts them, invokes the LangChain agent, and returns the updated Gradio history.
    """
    # Add the user message to history
    history.append([message, None])
    # Convert gradio history to langchain history
    langchain_full_history = gradio_to_langchain_messages(history)
    #print(f"Messages sent to LangChain: {langchain_full_history}") # For debugging

    try:
        # Invoke the LangGraph agent with the complete LangChain message history
        # The agent.invoke method expects a dictionary with a "messages" key
        agent_response_dict = agent.invoke({"messages": langchain_full_history})

        # LangGraph agent's response typically contains the full message history
        # We extract the latest AI message from the response.
        ai_response_lc = agent_response_dict["messages"][-1]

        # Convert the LangChain AI message back to Gradio format
        ai_response_content = ai_response_lc.content if hasattr(ai_response_lc, 'content') else str(ai_response_lc)

        # Append the AI's response to the Gradio history
        # Gradio's ChatInterface expects `history` to be updated and returned
        history[-1][1] = ai_response_content
    except Exception as e:
        error_message = f"An error occurred: {e}. Please try again."
        history[-1][1] = error_message
        print(f"Error in chat_with_langchain_agent: {e}")

    return history

#response = agent.invoke({"messages": [("user", "Please turn on first led")]})
#print(response["messages"][-1].content)
