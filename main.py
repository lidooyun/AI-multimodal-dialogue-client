from gradio_app import demo

if __name__ == "__main__":
    # 启动Gradio界面，默认在7860端口
    demo.launch(debug=True, server_port=7861)