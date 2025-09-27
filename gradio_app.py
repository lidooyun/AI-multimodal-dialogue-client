import gradio as gr
import visual_client
import text_client
import base64
from PIL import Image
import numpy as np
import os
from threading import Thread
import time

streaming_enabled = False
current_streaming_response = None
current_user_message = None

def process_message(text_input, conversation_history, generate_image_checkbox, image_size_dropdown, seed_input, guidance_scale_input, watermark_checkbox):
    user_message = text_input
    # 移除全局变量依赖，使用传入的对话历史
    # global conversation_history, streaming_enabled, current_streaming_response
    streaming_enabled = False  # 暂时禁用流式处理
    response = ""
    
    # 确保对话历史是列表类型
    if not isinstance(conversation_history, list):
        conversation_history = []
    # 添加用户消息到历史
    conversation_history.append({"role": "user", "content": user_message})
    
    if generate_image_checkbox:
        # 文字生成图片逻辑
        # 解析图片尺寸
        size_str = image_size_dropdown.split()[0]  # 获取"1024x1024"部分
        width, height = map(int, size_str.split('x'))
        
        # 解析seed参数
        try:
            seed = int(seed_input)
            if seed < -1 or seed > 2147483647:
                seed = -1  # 超出范围使用默认值
        except ValueError:
            seed = -1  # 无效输入使用默认值
        
        # 解析guidance_scale参数
        try:
            guidance_scale = float(guidance_scale_input)
            if guidance_scale < 1 or guidance_scale > 10:
                guidance_scale = 2.5  # 超出范围使用默认值
        except ValueError:
            guidance_scale = 2.5  # 无效输入使用默认值
        
        # 水印参数
        watermark = watermark_checkbox
        
        # 调用图像生成模型
        image_path = visual_client.call_text_to_image_model(
            user_message, 
            width=width, 
            height=height, 
            seed=seed, 
            guidance_scale=guidance_scale, 
            watermark=watermark
        )
        image_url = get_image_url(image_path)
        conversation_history.append({"role": "assistant", "content": f"![生成图片]({image_url})"})
        return "", conversation_history, conversation_history

    else:
        # 处理纯文本
        context_history = [(msg["role"], msg["content"]) for msg in conversation_history[:-1]]
        if streaming_enabled:

            current_streaming_response = ""
            response = text_client.call_text_model(
                user_message
            )
            conversation_history.append({"role": "assistant", "content": response})
        else:
            response = text_client.call_text_model(
                  user_message
              )
            conversation_history.append({"role": "assistant", "content": response})
    
    return "", conversation_history, conversation_history

def get_image_url(image):
    """将Gradio图片对象转换为Base64编码的data URL"""
    # 验证输入image参数有效性
    if image is None:
        return None
    if not isinstance(image, (str, bytes, Image.Image, np.ndarray)):
        print(f"无效的图片类型: {type(image)}")
        return None  # 返回None表示图片处理失败
    
    # 获取图片格式
    ext = os.path.splitext(image)[1].lower().replace('.', '') if isinstance(image, str) else 'png'
    if ext == 'jpg':
        ext = 'jpeg'
    
    # 读取图片并转换为Base64
    if isinstance(image, str):
        with open(image, "rb") as image_file:
            base64_data = base64.b64encode(image_file.read()).decode('utf-8')
    else:
        # 对于Gradio上传的图片对象（转换为bytes）
        if hasattr(image, 'save'):
            # PIL Image对象
            buffer = BytesIO()
            image.save(buffer, format=ext.upper())
            base64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        elif isinstance(image, np.ndarray):
            # NumPy数组 (RGB格式)
            img = Image.fromarray(image)
            buffer = BytesIO()
            img.save(buffer, format=ext.upper())
            base64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        else:
            # 回退处理
            base64_data = base64.b64encode(image).decode('utf-8')
    
    return f"data:image/{ext};base64,{base64_data}"

def update_streaming_response(content):
    """更新流式响应内容"""
    global current_streaming_response
    current_streaming_response = content

def stream_response():
    """流式响应生成器"""
    global current_streaming_response
    while True:
        if current_streaming_response is not None:
            yield conversation_history + [{"role": "assistant", "content": current_streaming_response}]
            if not streaming_enabled:
                current_streaming_response = None
        time.sleep(0.1)

# 创建Gradio界面
with gr.Blocks(title="AI文图互生对话客户端", css=".image-generation-panel { border: 1px solid #ddd; padding: 10px; border-radius: 5px; }") as demo:
    gr.Markdown("# AI文图互生对话客户端")
    
    with gr.Row():
        chatbot = gr.Chatbot(height=500, type='messages', render_markdown=True)
        
        with gr.Column():
            # 所有功能整合到单个垂直列布局
            image_input = gr.Image(type="filepath", label="上传图片", height=150)
            #streaming_checkbox = gr.Checkbox(label="启用流式输出", value=False)

            with gr.Column():
                generate_image_checkbox = gr.Checkbox(label="文字生成图片", value=False)                
                image_size_dropdown = gr.Dropdown(
                        choices=[
                            "1024x1024 (1:1)",
                            "896x1152 (3:4)",
                            "1152x896 (4:3)",
                            "832x1216 (2:3)",
                            "1216x832 (3:2)",
                            "768x1344 (9:16)",
                            "1344x768 (16:9)",
                            "576x1024 (9:16)",
                        ],
                        value="1024x1024 (1:1)",
                        interactive=False,
                        label="图片尺寸"
                )
                
                seed_input = gr.Textbox(value="-1", placeholder="取值范围为 [-1, 2147483647]，默认-1", label="随机种子 (seed)", interactive=False)
                guidance_scale_input = gr.Textbox(value="2.5", placeholder="取值范围：[1, 10] 之间的浮点数，默认2.5", label="自由度 (guidance_scale)", interactive=False)
                watermark_checkbox = gr.Checkbox(label="添加水印", value=True, interactive=False)

                generate_image_checkbox.change(
                    fn=lambda checked: [gr.update(interactive=checked)] * 4,
                    inputs=[generate_image_checkbox],
                    outputs=[image_size_dropdown, seed_input, guidance_scale_input, watermark_checkbox]
                )
            
    # 在Blocks上下文中定义状态组件
    conversation_history = gr.State([])
    with gr.Row():
        text_input = gr.Textbox(label="输入消息", placeholder="请输入文本消息（支持Markdown格式，如代码块```python...```和公式$$E=mc^2$$）")
        send_button = gr.Button("发送")
    
    # 设置按钮点击事件
    send_button.click(
        process_message,
        inputs=[text_input, conversation_history, generate_image_checkbox, image_size_dropdown, seed_input, guidance_scale_input, watermark_checkbox],
        outputs=[text_input, chatbot, conversation_history]
    )
    text_input.submit(
        process_message,
        inputs=[text_input, conversation_history, generate_image_checkbox, image_size_dropdown, seed_input, guidance_scale_input, watermark_checkbox],
        outputs=[text_input, chatbot, conversation_history]
    )

if __name__ == "__main__":
    demo.launch(debug=True)
