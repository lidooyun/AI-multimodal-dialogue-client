import requests

# 火山方舟API配置 - 纯文本调用模块
# 注意事项:
# 1. API密钥已硬编码在代码中
# 2. 生产环境中建议使用环境变量存储密钥: ARK_API_KEY
# 3. 官方文档: https://ark.volces.com/docs/api-reference/chat
# 4. 当前使用模型: doubao-seed-1-6-250615
AI_MODEL_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
API_KEY = "47b0eb16-b869-498a-8604-6a0e1f27b0a0"

def call_text_model(text: str) -> str:
    """调用火山方舟AI模型进行纯文本对话

    Args:
        text: 用户输入的文本消息

    Returns:
        AI模型返回的响应文本
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    # 构建纯文本内容
    content = [{"type": "text", "text": text}]
    
    payload = {
        "model": "doubao-seed-1-6-250615",
        "messages": [{"role": "user", "content": content}]
    }

    try:
        response = requests.post(AI_MODEL_URL, json=payload, headers=headers)
        response.raise_for_status()
        response_data = response.json()
        choices = response_data.get("choices", [])
        if choices:
            return choices[0]["message"]["content"]
        return f"未获取到有效响应: {response_data}"
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response:
            try:
                error_details = e.response.json()
                return f"调用文本模型失败: {str(e)}, 错误详情: {error_details}"
            except ValueError:
                return f"调用文本模型失败: {str(e)}, 响应内容: {e.response.text}"
        return f"调用文本模型失败: {str(e)}"

# 示例用法
if __name__ == "__main__":
    text_message = "你好，请问有什么可以帮助的？"
    response = call_text_model(text_message)
    print(f"文本模型响应: {response}")