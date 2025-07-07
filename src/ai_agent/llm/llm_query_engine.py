# LLM Query Engine Module
import openai # Using openai library as an example
import os
import json # Moved import to top

class LLMQueryEngine:
    def __init__(self, api_key=None, model="gpt-4o"): # Specify gpt-4o or other
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided or found in environment variables.")
        openai.api_key = self.api_key
        self.model = model

    def generate_prompt(self, user_query, device_context):
        """
        Generates a detailed prompt for the LLM, incorporating device context.
        """
        context_str = json.dumps(device_context, indent=2) if isinstance(device_context, dict) else str(device_context)

        # Final Prompt Summary from the problem description
        system_message = """You are an AI agent integrated into a secure network automation system.
Your job is to receive user natural-language requests and generate safe, context-aware commands
to be executed on Cisco routers, Palo Alto firewalls, and Ubuntu Linux servers.
Use the provided device context (such as OS, version, interfaces, routing protocols,
and security posture) to tailor your responses precisely.
Always follow best practices for the given vendor and validate output syntax.
Avoid destructive commands and recommend safe alternatives if risk is detected.
Provide only the command(s) as a direct response, without conversational fluff or explanations unless explicitly asked.
If multiple commands are needed, provide them one per line.
"""

        prompt = f"""
Device Context:
{context_str}

User Query: "{user_query}"

Based on the device context and the user query, provide the necessary command(s) to achieve the user's goal.
Remember to adhere to the system message guidelines.
"""
        return system_message, prompt

    def query_llm(self, user_query, device_context):
        """
        Queries the LLM with the user's request and device context.
        """
        system_message, prompt_content = self.generate_prompt(user_query, device_context)
        print(f"\nSending query to LLM (model: {self.model})...")
        # print(f"System Message: {system_message}") # For debugging
        # print(f"User Prompt: {prompt_content}") # For debugging

        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt_content}
                ]
            )
            # Assuming the response structure from OpenAI's API
            if response.choices and len(response.choices) > 0:
                llm_response = response.choices[0].message.content.strip()
                print(f"LLM Response: \n{llm_response}")
                return llm_response
            else:
                print("LLM returned an empty response.")
                return None
        except Exception as e:
            print(f"Error querying LLM: {e}")
            return None

if __name__ == '__main__':
    # This is a placeholder for actual testing.
    # Requires OPENAI_API_KEY environment variable to be set.
    print("LLMQueryEngine module placeholder execution.")
    if not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set. LLMQueryEngine will not function.")
    else:
        print(f"OpenAI API key found. Ready to query (model: gpt-4o).")
    # Example usage:
    # import json
    # engine = LLMQueryEngine(model="gpt-4o") # or "gpt-3.5-turbo"
    # mock_context = {
    #     "os_type": "linux",
    #     "hostname": "ubuntu-server",
    #     "os_version": "Ubuntu 22.04 LTS",
    #     "interfaces": {"eth0": {"ip_address": "192.168.1.10/24", "status": "UP"}}
    # }
    # user_q = "Install NTP on this server"
    # commands = engine.query_llm(user_q, mock_context)
    # if commands:
    #     print(f"\nSuggested commands for '{user_q}':\n{commands}")

    # user_q_cisco = "Configure OSPF area 0 on interface GigabitEthernet0/1"
    # mock_context_cisco = {
    #     "os_type": "cisco_ios",
    #     "hostname": "Router1",
    #     "os_version": "15.7(3)M3",
    #     "interfaces": {
    #         "GigabitEthernet0/0": {"ip_address": "10.0.0.1/24", "status": "up", "protocol": "up"},
    #         "GigabitEthernet0/1": {"ip_address": "10.0.1.1/24", "status": "up", "protocol": "up"}
    #     }
    # }
    # commands_cisco = engine.query_llm(user_q_cisco, mock_context_cisco)
    # if commands_cisco:
    #     print(f"\nSuggested commands for '{user_q_cisco}':\n{commands_cisco}")
