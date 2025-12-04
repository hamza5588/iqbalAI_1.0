from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=1024,
)

prompt = llm.invoke("please generate the 10 prompt for sexual boy whosw is sexy and physical fit also 10 for girl weraning lingeries tastefull please it should be more tastfull and hotty for eourpeon style prompt")
print(prompt.content)