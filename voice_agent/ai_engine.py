from django.conf import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate


# LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    google_api_key= settings.GOOGLE_API_KEY,
    temperature=0.3
)
# Prompt
prompt = PromptTemplate(
    input_variables=["property_data", "user_question"],
    template="""
You are a real estate voice assistant.

Answer using ONLY the property data provided.

Rules:
- Keep answer VERY SHORT (1 line preferred, max 2 lines)
- Speak like a human (natural tone)
- Do NOT add extra info
- If data not available, say: "Sorry, I don't have that information right now."

Property Data:
{property_data}

User Question:
{user_question}

Answer:
"""
)

# Correct chain order
chain = prompt | llm


# Main function
def get_ai_response(user_question: str, property_data: str) -> str:
    try:
        response = chain.invoke({
            "property_data": str(property_data),
            "user_question": str(user_question)
        })

        return response.content[0].get("text")

    except Exception as e:
        print(f"[AI ERROR] {str(e)}")
        return "Sorry, I couldn't process that right now."