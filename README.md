# AI-multimodal-dialogue-client
独立开发一套Web前端AI 对话系统，支持文本问答、图像识别与文生图三种模式。用户可在 Gradio 网页上传图片或输入文本，程序后台调用火山方舟大模型，阻塞响应返回答案，并自动缓存生成图片。全部逻辑均封装为可复用 Python 模块，一键启动即可在本地 7861 端口运行完整服务。 技术栈： Python、Gradio、Requests、Pillow、Threading、火山方舟大模型（文本 / 视觉 / 文生图）、Base64 编解码、JSON 配置
