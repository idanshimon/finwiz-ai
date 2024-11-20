from flask import Flask, render_template, request, jsonify
from io import StringIO
import sys
from langchain_openai import ChatOpenAI
from langchain.agents import tool, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
import yfinance as yf

app = Flask(__name__)


llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

@tool 
def PythonREPL_run(command: str) -> str:
        """A Python shell. Use this to execute Python commands. If you expect output, it should be printed out."""
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        try:
            print(f"Running command: {command}")
            # This is normal. No cause for Alarm
            exec(command, globals())
            # Completely harmless.
            sys.stdout = old_stdout
            output = mystdout.getvalue()
            print(f"Output: {output}")
        except Exception as e:
            sys.stdout = old_stdout
            output = str(e)
        return output

@tool
def get_stock_price(ticker, period='1d'):
    """
    Retrieves the stock price for a given ticker and period.

    Args:
    ticker (str): The stock symbol to retrieve price for.
    period (str): The period over which to retrieve stock data. Examples include '1d' (one day), '1mo' (one month), '1y' (one year), etc.

    Returns:
    float or str: The latest stock price or an error message if data is not available.
    """
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
    """
    Calculates the Relative Strength Index (RSI) for a given stock ticker.

    Args:
    ticker (str): The stock symbol.
    period (str): The period over which to fetch historical data (e.g., '1mo', '6mo', '1y').
    interval (str): The data interval (e.g., '1d' for daily).
    rsi_period (int): The period over which to calculate RSI (commonly 14 days).

    Returns:
    float: The RSI value.
    """
    # Fetch historical data
    data = yf.download(ticker, period=period, interval=interval)
    if data.empty:
        return "No data available"

    # Calculate price changes
    delta = data['Close'].diff()

    # Get gains (positive deltas) and losses (negative deltas)
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    # Calculate the exponential moving average of gains and losses
    avg_gain = gain.ewm(com=rsi_period-1, min_periods=rsi_period).mean()
    avg_loss = loss.ewm(com=rsi_period-1, min_periods=rsi_period).mean()

    # Calculate the RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1]


instructions = """You are an agent designed to analyze stocks by write and execute python code to answer questions.
You have access to a python REPL, which you can use to execute python code for all purpose.
You also have access Stock Price Retriver, which you can use to fetch stocks information.
You also have RSI calulcator you can use directly if the user input ask for it, without the need for the other tools
If you get an error, debug your code and try again.
Only use the output of your code to answer the question. 
You might know the answer without running any code, but you should still run the code to get the answer.
If it does not seem like you can write code to answer the question, explain why.
"""

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            instructions,
        ),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)
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

@app.route('/')
def home():
    print("Home page")
    return render_template('index.html')

# Additional endpoint that might use the agent for more complex tasks or inputs
@app.route('/chat', methods=['POST'])
def process_input():
    print(f"Received query: {request.json}")
    query = request.json['message']
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    # Example of using the agent for processing the input
    # # # response = agent.run(query)  # Ensure your agent's run method can handle such queries appropriately
    response = agent_executor.invoke({"input": query})  # Ensure your agent's run method can handle such queries appropriately
    print(f"Response: {response}")
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
