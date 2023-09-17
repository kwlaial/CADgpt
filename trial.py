import openai

openai.api_type = "azure"
openai.api_base = "https://hkust.azure-api.net"
openai.api_version = "2023-05-15"
openai.api_key = "3e9b2e6825ca4cd1b9229d1284319932"

# check https://itsc.hkust.edu.hk/services/it-infrastructure/azure-openai-api-service

response = openai.ChatCompletion.create(
    engine="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is quantum computing?"}
    ]
)

print(response)
print(response['choices'][0]['message']['content'])

