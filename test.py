import os
from groq import Groq
import json

# Print all environment variables related to proxies
proxy_env_vars = {k: v for k, v in os.environ.items() if 'proxy' in k.lower()}
print("Proxy environment variables:", json.dumps(proxy_env_vars, indent=2))

# Try to initialize the client
try:
    client = Groq(api_key="your-test-key")
    print("✅ Client initialized successfully")
except Exception as e:
    print(f"❌ Error initializing client: {e}")
    
    # Inspect the Groq class
    print("\nGroq init signature:")
    import inspect
    print(inspect.signature(Groq.__init__))