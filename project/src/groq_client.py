from groq import Groq
from dotenv import load_dotenv

import json
import os

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

MODEL_NAME = "llama-3.3-70b-versatile"


# ============================================================
# SYSTEM PROMPTS
# ============================================================

GRAPH_QA_SYSTEM_PROMPT = """
Bạn là AI chuyên suy luận trên Knowledge Graph di sản văn hóa.

Nhiệm vụ:
- Chỉ trả lời dựa trên GRAPH EVIDENCE được cung cấp.
- Được phép suy luận multi-hop.
- Nếu dữ liệu không đủ thì nói rõ không tìm thấy.
- Không được bịa thông tin ngoài graph.

Ví dụ suy luận multi-hop:

A -> located_in -> B
B -> located_in -> C

=> A nằm trong C.

Hãy trả lời ngắn gọn, chính xác và tự nhiên.
"""


ENTITY_EXTRACTION_PROMPT = """
Bạn là bộ phân tích câu hỏi cho hệ thống Knowledge Graph.

Hãy trích xuất:
- entities
- question_type

Trả về STRICT JSON.

question_type có thể là:
- location
- person
- time
- material
- relation
- description
- unknown

Ví dụ:

Input:
"Tháp Eiffel nằm ở quận nào của Paris?"

Output:
{
  "entities": ["Tháp Eiffel", "Paris"],
  "question_type": "location"
}
"""


# ============================================================
# BASE CHAT
# ============================================================

def _chat(messages, temperature=0.2):

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=temperature
    )

    return response.choices[0].message.content


# ============================================================
# MAIN QA
# ============================================================

def ask_groq(question, evidence):

    prompt = f"""
[USER QUESTION]
{question}

[GRAPH EVIDENCE]
{evidence}

Hãy trả lời câu hỏi dựa trên graph evidence phía trên.
"""

    return _chat(
        [
            {
                "role": "system",
                "content": GRAPH_QA_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1
    )


# ============================================================
# ENTITY EXTRACTION
# ============================================================

def extract_entities_and_intent(question):

    prompt = f"""
{ENTITY_EXTRACTION_PROMPT}

Input:
{question}
"""

    response = _chat(
        [
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    try:
        return json.loads(response)

    except Exception:

        return {
            "entities": [],
            "question_type": "unknown"
        }
    
def extract_question_entities(question):

    prompt = f"""
    Extract:

    1. Main entity
    2. Target location
    3. Reasoning type

    QUESTION:
    {question}

    Output JSON only.
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content