import requests
import json
from common.config import LLM_API_URL, LLM_API_KEY, LLM_MODEL

class LLMAssistant:
    def __init__(self):
        self.api_url = LLM_API_URL
        self.api_key = LLM_API_KEY
        self.model = LLM_MODEL
    
    def get_response(self, prompt):
        """Call the LLM API and return the generated reply."""
        print(f"Calling LLM API, prompt={prompt[:50]}...")
        try:
            if not self.api_key:
                print("LLM API key is not configured")
                return 'AI service is not configured. Please set LLM_API_KEY first.'

            api_endpoint = self.api_url.rstrip('/')
            if not api_endpoint.endswith('/chat/completions'):
                api_endpoint = f"{api_endpoint}/chat/completions"

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            data = {
                'model': self.model,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                # Lower output length and randomness to improve latency and reduce timeout risk
                'max_tokens': 1024,
                'temperature': 0.3
            }
            
            print(f"API URL: {api_endpoint}")
            # Separate connect and read timeouts for easier diagnosis
            # Retry transient timeout and network failures to improve stability
            response = None
            last_err = None
            for attempt in range(3):
                try:
                    response = requests.post(api_endpoint, headers=headers, json=data, timeout=(8, 45))
                    break
                except requests.exceptions.Timeout as e:
                    last_err = e
                    print(f"LLM request timed out, retry {attempt + 1}/3")
                except requests.exceptions.RequestException as e:
                    last_err = e
                    print(f"LLM network error, retry {attempt + 1}/3: {e}")

            if response is None:
                raise last_err if last_err else requests.exceptions.RequestException("request failed")

            print(f"API status: {response.status_code}")
            response.raise_for_status()
            
            result = response.json()
            print(f"API response: {result}")
            choices = result.get('choices', [])
            if choices and isinstance(choices, list):
                message = choices[0].get('message', {})
                content = message.get('content')
                if content:
                    return content
            return 'Sorry, I could not generate a valid reply right now.'
        except requests.exceptions.Timeout as e:
            print(f"LLM API timeout: {e}")
            return 'AI response timed out. Please try again later.'
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            detail = ''
            try:
                detail = e.response.json().get('error', {}).get('message', '')
            except Exception:
                detail = ''

            print(f"LLM API HTTP error: status={status_code}, detail={detail}")
            if status_code == 401:
                return 'AI authentication failed. Please verify the API key.'
            if status_code == 429:
                return 'AI rate limit hit (HTTP 429). Please try again later.'
            if status_code and 500 <= status_code < 600:
                return 'AI service is temporarily unavailable. Please try again later.'
            return f'AI request failed (HTTP {status_code}).'
        except requests.exceptions.RequestException as e:
            print(f"LLM API network error: {e}")
            return 'AI network request failed. Please check the network and retry.'
        except Exception as e:
            print(f"LLM API call failed: {e}")
            return 'Sorry, the AI assistant is temporarily unavailable.'
    
    def handle_ai_command(self, message):
        """Handle an @AI command inside a message."""
        content = message.get('content', '')
        # Extract the text after @AI as the prompt
        if '@AI' in content:
            prompt = content.split('@AI', 1)[1].strip()
            if prompt:
                return self.get_response(prompt)
        return None
