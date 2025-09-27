import os
import requests
import json
import random
import base64
import os
from PIL import Image
from io import BytesIO

# API密钥配置
API_KEY = "47b0eb16-b869-498a-8604-6a0e1f27b0a0"

# 辅助函数：生成备用随机图像
def _generate_fallback_image():
    # 确保输出目录存在
    os.makedirs('generated_images', exist_ok=True)
    # 生成备用随机图像
    width, height = 1024, 1024
    image = Image.new('RGB', (width, height), color=(random.randint(0,255), random.randint(0,255), random.randint(0,255)))
    image_path = os.path.join('generated_images', f'fallback_image_{random.randint(100000, 999999)}.png')
    image.save(image_path)
    return image_path

# 图像识别模型API配置
VISUAL_RECOGNITION_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
IMAGE_GENERATION_API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"

def call_text_to_image_model(prompt, width=1024, height=1024, seed=-1, guidance_scale=2.5, watermark=True):
    # 火山方舟API配置
    API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    payload = {
        "model": "doubao-seedream-3-0-t2i-250415",
        "prompt": prompt,
        "response_format": "url",
        "size": f"{width}x{height}",
        "seed": random.randint(1, 10000) if seed == -1 else seed,
        "guidance_scale": guidance_scale,
        "watermark": watermark
    }
    
    try:
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        
        # 获取图片URL
        image_url = result['data'][0]['url']
        
        # 下载图片
        img_response = requests.get(image_url)
        img_response.raise_for_status()
    
        
        # 确保输出目录存在
        output_dir = 'generated_images'
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成唯一的文件名
        image_path = os.path.join(output_dir, f'image_{random.randint(100000, 999999)}.png')
        
        # 保存图片
        with open(image_path, 'wb') as f:
            f.write(img_response.content)
        
        return image_path
    except Exception as e:
        print(f"API请求失败: {str(e)}")
        return _generate_fallback_image()


def call_visual_model(prompt, image_path, conversation_history=None, streaming_enabled=False, update_callback=None):
    # 图像识别API调用实现
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    # 获取图片MIME类型
    mime_type = 'image/png'
    if image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg'):
        mime_type = 'image/jpeg'
    elif image_path.lower().endswith('.gif'):
        mime_type = 'image/gif'
    elif image_path.lower().endswith('.webp'):
        mime_type = 'image/webp'
    
    # 将本地图片转换为base64
    try:
        # 检查文件大小（限制10MB）
        if os.path.getsize(image_path) > 10 * 1024 * 1024:
            print(f"图片过大: {image_path}")
            return "错误：图片大小不能超过10MB"
        
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        # 提取图片格式并构建符合官方规范的data URL
        image_format = mime_type.split('/')[1] if mime_type and '/' in mime_type else 'png'
        image_url = f"data:image/{image_format};base64,{base64_image}"
        # 调试image_url
        print(f"生成的图片URL: {image_url[:50]}...")  # 打印前50个字符避免过长
        # 验证image_url是否有效
        if not image_url or not isinstance(image_url, str):
            return "错误：图片URL为空或无效"
        # 验证image_url格式
        if not image_url.startswith('data:') or 'base64,' not in image_url:
            return "错误：生成的图片URL格式无效"
    except FileNotFoundError:
        print(f"图片文件不存在: {image_path}")
        return "错误：图片文件不存在"
    except PermissionError:
        print(f"没有权限读取图片: {image_path}")
        return "错误：没有权限读取图片文件"
    except Exception as e:
        print(f"图片读取失败: {str(e)}")
        return f"图片处理错误: {str(e)}"
    
    # 构建符合API要求的请求体
    payload = {
        "model": "doubao-1-5-vision-pro-32k-250115",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ]
    }
    
    # 如果有对话历史，添加到请求中
    if conversation_history:
        payload["messages"] = conversation_history + payload["messages"]
    
    try:
        # 设置超时时间为60秒
        # 调试API URL
        print(f"API请求URL: {VISUAL_RECOGNITION_API_URL}")
        # 验证API URL格式
        if not VISUAL_RECOGNITION_API_URL.startswith(('http://', 'https://')):
            print(f"无效的API URL: {VISUAL_RECOGNITION_API_URL}")
            return "错误：API URL配置无效，缺少协议前缀"
        response = requests.post(VISUAL_RECOGNITION_API_URL, headers=headers, data=json.dumps(payload), timeout=60)
        response.raise_for_status()
        # 检查HTTP状态码
        if response.status_code != 200:
            print(f"API请求失败，状态码: {response.status_code}")
            return f"图像识别请求失败，状态码: {response.status_code}"
        
        try:
            result = response.json()
            # 添加API响应调试日志
            print(f"API响应: {json.dumps(result, indent=2)}")
        except json.JSONDecodeError:
            print(f"API响应不是有效的JSON格式: {response.text}")
            return "图像识别API返回无效响应"
        
        # 检查API响应是否包含错误
        if 'error' in result:
            error_msg = result['error'].get('message', '未知错误')
            error_type = result['error'].get('type', 'unknown')
            print(f"API错误 ({error_type}): {error_msg}")
            return f"图像识别失败: {error_msg}"
        
        # 提取识别结果
        if 'choices' in result and len(result['choices']) > 0:
            message = result['choices'][0].get('message', {})
            content = message.get('content', '')
            if content:
                if streaming_enabled and update_callback:
                    # 模拟流式输出
                    for chunk in [content[i:i+50] for i in range(0, len(content), 50)]:
                        update_callback(chunk)
                return content
            else:
                print("API响应中没有内容")
                return "图像识别成功，但未返回内容"
        else:
            print(f"API响应格式不正确: {json.dumps(result, indent=2)}")
            return "无法获取图像识别结果"
    except Exception as e:
        error_msg = f"图像识别API调用失败: {str(e)}"
        print(error_msg)
        return _generate_fallback_image()