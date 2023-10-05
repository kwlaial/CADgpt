import openai

openai.api_type = "azure"
openai.api_base = "https://hkust.azure-api.net"
openai.api_version = "2023-05-15"
openai.api_key = "5e5d81163812467f803dcc940340a3ee"

# check https://itsc.hkust.edu.hk/services/it-infrastructure/azure-openai-api-service

# 画五个半径为10的球体


response = openai.ChatCompletion.create(
    engine="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is quantum computing?"}
    ]
)

print(response)
print(response['choices'][0]['message']['content'])

