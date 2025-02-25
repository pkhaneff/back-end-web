import os
from openai import OpenAI
import traceback
import json
from ai.ai_bot import AiBot

class ChatGPT(AiBot):

    def __init__(self, token, model):
        self.__chat_gpt_model = model
        self.__client = OpenAI(api_key=token)

    def ai_request_diffs(self, code, diffs):
        try:
            response = self.__client.chat.completions.create(
                messages=[{
                    "role": "user", 
                    "content": AiBot.build_ask_text(code=code, diffs=diffs)
                }],
                model=self.__chat_gpt_model,
                stream=False,
                max_tokens=4096  
            )

            print("🔍 Raw response:", response)

            if response and hasattr(response, "choices") and len(response.choices) > 0:
                ai_message = response.choices[0].message
                print("🔍 AI message:", ai_message)

                if hasattr(ai_message, "content") and ai_message.content:
                    return ai_message.content.strip()
                else:
                    return "⚠️ AI không cung cấp phản hồi hợp lệ."
            return "⚠️ Không nhận được phản hồi từ AI."
        except Exception as e:
            import traceback
            print(f"🚨 API Error: {e}")
            print(traceback.format_exc())
            return f"❌ Error occurred: {str(e)}"
        
    import json

    def ai_request_summary(self, file_changes):
        try:
            print(f"🔍 Debug: type(file_changes) = {type(file_changes)}")  
            print(f"🔍 Debug: file_changes keys = {list(file_changes.keys())}")
            print(f"🔍 Debug: file_changes (type: {type(file_changes)}): {str(file_changes)[:200]}")

            if isinstance(file_changes, str):
                try:
                    file_changes = json.loads(file_changes)  
                except json.JSONDecodeError:
                    raise ValueError("⚠️ file_changes là string nhưng không phải JSON hợp lệ!")

            if not isinstance(file_changes, dict):
                raise ValueError(f"⚠️ file_changes phải là một dictionary! Nhận: {type(file_changes)}")

            summary_request = "Tóm tắt nội dung PR...\n"
            for file_name, file_content in file_changes.items():
                summary_request += f"\nFile: {file_name}\nNội dung thay đổi:\n{file_content}\n"

            response = self.__client.chat.completions.create(
                messages=[{"role": "user", "content": summary_request}],
                model=self.__chat_gpt_model,
                stream=False,
                max_tokens=2048  
            )

            if response and response.choices and len(response.choices) > 0:
                ai_message = response.choices[0].message
                if hasattr(ai_message, "content") and ai_message.content:
                    return ai_message.content.strip()
                else:
                    return "⚠️ AI không cung cấp phản hồi hợp lệ."
            return "⚠️ Không nhận được phản hồi từ AI."

        except Exception as e:
            print(f"🚨 API Error: {e}")
            print(traceback.format_exc())
            return f"❌ Error occurred: {str(e)}"
