# groq_client.py

import json
import time
from groq import Groq


class GroqClient:

    def __init__(
        self,
        api_key,
        model="llama-3.3-70b-versatile"
    ):

        self.client = Groq(
            api_key=api_key
        )

        self.model = model

    # =========================================================
    # GENERIC CHAT
    # =========================================================

    def chat(
        self,
        system_prompt,
        user_prompt,
        temperature=0.1,
        max_tokens=1024,
        retries=3
    ):

        for attempt in range(retries):

            try:

                response = (
                    self.client.chat.completions.create(

                        model=self.model,

                        temperature=temperature,

                        max_tokens=max_tokens,

                        messages=[

                            {
                                "role": "system",
                                "content": system_prompt
                            },

                            {
                                "role": "user",
                                "content": user_prompt
                            }
                        ]
                    )
                )

                content = (
                    response
                    .choices[0]
                    .message.content
                )

                return content

            except Exception as e:

                print(
                    f"[Groq ERROR] Attempt {attempt+1}: {e}"
                )

                time.sleep(1)

        return ""

    # =========================================================
    # JSON CHAT
    # =========================================================

    def chat_json(
        self,
        system_prompt,
        user_prompt,
        temperature=0.1,
        max_tokens=1024
    ):

        response = self.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )

        try:

            return json.loads(response)

        except Exception:

            try:

                cleaned = (
                    response
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
                )

                return json.loads(cleaned)

            except Exception:

                return {
                    "error": "Failed to parse JSON",
                    "raw_response": response
                }