from flask import Flask, render_template, request, jsonify
from io import StringIO
import sys
from langchain_openai import ChatOpenAI
from langchain.agents import tool, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents.format_scratchpad.openai_tools import format_to_openai_tool_messages
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from pymongo import MongoClient
import yfinance as yf
import datetime
import os

app = Flask(__name__)

# MongoDB setup
conn_str = os.getenv('MONGO_CONN_STR')
mongo_uri = conn_str
client = MongoClient(mongo_uri)
db = client.wizdemoapp
prompts_collection = db.prompts

# LangChain setup
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

@tool 
def PythonREPL_run(command: str) -> str:
    """A Python shell. Use this to execute Python commands. If you expect output, it should be printed out."""
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    try:
        print(f"Running command: {command}")
        exec(command, globals())
        sys.stdout = old_stdout
        output = mystdout.getvalue()
        print(f"Output: {output}")
    except Exception as e:
        sys.stdout = old_stdout
        output = str(e)
    return output

@tool
def get_stock_price(ticker, period='1d'):
    """Retrieves the stock price for a given ticker and period."""
    stock = yf.Ticker(ticker)
    try:
        todays_data = stock.history(period=period)
        if not todays_data.empty:
            return todays_data['Close'][-1]
        else:
            return "No data available"
    except Exception as e:
        return f"An error occurred: {str(e)}"

@tool
def calculate_rsi(ticker, period='6mo', interval='1d', rsi_period=14):
    """Calculates the Relative Strength Index (RSI) for a given stock ticker."""
    try:
        data = yf.download(ticker, period=period, interval=interval)
        if data.empty:
            return "No data available"

        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)
        avg_gain = gain.ewm(com=rsi_period-1, min_periods=rsi_period).mean()
        avg_loss = loss.ewm(com=rsi_period-1, min_periods=rsi_period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    except Exception as e:
        return f"Error calculating RSI: {str(e)}"

instructions = """You are an agent designed to analyze stocks by write and execute python code to answer questions.
You have access to a python REPL, which you can use to execute python code for all purpose.
You also have access Stock Price Retriver, which you can use to fetch stocks information.
You also have RSI calulcator you can use directly if the user input ask for it, without the need for the other tools
If you get an error, debug your code and try again.
Only use the output of your code to answer the question. 
You might know the answer without running any code, but you should still run the code to get the answer.
If it does not seem like you can write code to answer the question, explain why.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", instructions),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

tools = [PythonREPL_run, get_stock_price, calculate_rsi]
llm_with_tools = llm.bind_tools(tools)

agent = (
    {
        "input": lambda x: x["input"],
        "agent_scratchpad": lambda x: format_to_openai_tool_messages(
            x["intermediate_steps"]
        ),
    }
    | prompt
    | llm_with_tools
    | OpenAIToolsAgentOutputParser()
)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

def save_prompt(input_text, response, save_enabled=True):
    """Save the prompt and response to MongoDB if save_enabled is True."""
    if not save_enabled:
        return

    prompt_doc = {
        "input": input_text,
        "response": response["response"]["output"],  # Flatten the response structure
        "timestamp": datetime.datetime.utcnow(),
        "model": "gpt-3.5-turbo",
        "temperature": 0
    }
    prompts_collection.insert_one(prompt_doc)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    query = data['message']
    save_history = data.get('save_history', True)

    if not query:
        return jsonify({"error": "No query provided"}), 400

    try:
        # Get response from agent
        response = agent_executor.invoke({"input": query})

        # Format response for frontend
        formatted_response = {
            "response": {
                "output": response["output"]
            }
        }

        # Save to MongoDB if enabled
        try:
            save_prompt(query, formatted_response, save_history)
        except Exception as e:
            print(f"Error saving to MongoDB: {e}")

        return jsonify(formatted_response)
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({
            "response": {
                "output": f"Sorry, I encountered an error: {str(e)}"
            }
        }), 500

@app.route('/history', methods=['GET'])
def get_history():
    """Retrieve chat history from MongoDB."""
    try:
        prompts = list(prompts_collection.find({}, {'_id': 0}).sort('timestamp', -1))
        return jsonify(prompts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/clear-history', methods=['POST'])
def clear_history():
    """Clear all chat history from MongoDB."""
    try:
        prompts_collection.delete_many({})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
        
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)