import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from PIL import Image, ImageTk
import threading
import visual_client
import text_client
import io
import requests

class AIClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI多模态对话客户端")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # 设置中文字体
        self.font = ("SimHei", 10)
        self.title_font = ("SimHei", 12, "bold")

        # 存储对话历史(上下文记忆)
        self.conversation_history = []
        # 存储上传的图片路径
        self.uploaded_image_path = None
        self.image_preview = None
        # 流式输出开关状态
        self.streaming_enabled = tk.BooleanVar(value=False)

        self._create_widgets()

    def _create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 对话历史区域
        history_frame = ttk.LabelFrame(main_frame, text="对话历史", padding="10")
        history_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.history_text = scrolledtext.ScrolledText(history_frame, wrap=tk.WORD, font=self.font, state=tk.DISABLED)
        self.history_text.pack(fill=tk.BOTH, expand=True)

        # 图片预览区域
        image_frame = ttk.LabelFrame(main_frame, text="图片预览", padding="10")
        image_frame.pack(fill=tk.X, pady=(0, 10))
        image_frame.pack_propagate(False)  # 锁定框架大小
        image_frame.configure(height=200)  # 设置固定高度

        # 创建图片预览和控制区域的容器
        preview_container = ttk.Frame(image_frame)
        preview_container.pack(fill=tk.BOTH, expand=True)

        # 左侧图片预览区
        self.image_label = ttk.Label(preview_container, text="未上传图片", borderwidth=1, relief="solid")
        self.image_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # 右侧控制区
        control_frame = ttk.Frame(preview_container)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # 流式输出复选框
        self.streaming_checkbox = ttk.Checkbutton(
            control_frame, text="启用流式输出", variable=self.streaming_enabled
        )
        self.streaming_checkbox.pack(anchor=tk.NW, pady=(10, 0))

        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        self.upload_btn = ttk.Button(button_frame, text="上传图片", command=self.upload_image)
        self.upload_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.clear_image_btn = ttk.Button(button_frame, text="清除图片", command=self.clear_image)
        self.clear_image_btn.pack(side=tk.LEFT)

        # 输入区域
        input_frame = ttk.LabelFrame(main_frame, text="输入消息", padding="10")
        input_frame.pack(fill=tk.BOTH, expand=True)

        self.input_text = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, font=self.font, height=4)
        self.input_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        # 绑定回车键发送消息，Shift+回车换行
        self.input_text.bind("<Return>", lambda event: self.send_message())
        self.input_text.bind("<Shift-Return>", lambda event: self.input_text.insert(tk.INSERT, "\n"))

        self.send_btn = ttk.Button(input_frame, text="发送", command=self.send_message)
        self.send_btn.pack(fill=tk.X)

    def upload_image(self):
        """上传图片并显示预览"""
        file_path = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")]
        )
        if file_path:
            self.uploaded_image_path = file_path
            self._display_image_preview()
            self.add_message("系统", f"已上传图片: {file_path.split('/')[-1]}")

    def _display_image_preview(self):
        """显示图片预览(固定大小缩略图)"""
        if self.uploaded_image_path:
            try:
                image = Image.open(self.uploaded_image_path)
                # 获取预览区域大小
                preview_width = self.image_label.winfo_width() if self.image_label.winfo_width() > 1 else 400
                preview_height = self.image_label.winfo_height() if self.image_label.winfo_height() > 1 else 200

                # 计算缩略图大小，保持纵横比
                image.thumbnail((preview_width, preview_height))
                photo = ImageTk.PhotoImage(image)
                self.image_preview = photo  # 保持引用，防止被垃圾回收
                self.image_label.config(image=photo, text="")
            except Exception as e:
                self.add_message("系统错误", f"无法显示图片: {str(e)}")
                self.uploaded_image_path = None
                self.image_label.config(text="图片加载失败")

    def clear_image(self):
        """清除已上传的图片"""
        self.uploaded_image_path = None
        self.image_preview = None
        self.image_label.config(image="")
        self.image_label.config(text="未上传图片")
        self.add_message("系统", "已清除图片")

    def add_message(self, sender, message):
        """添加消息到对话历史"""
        self.conversation_history.append((sender, message))
        self.history_text.config(state=tk.NORMAL)
        self.history_text.insert(tk.END, f"{sender}: {message}\n\n")
        self.history_text.config(state=tk.DISABLED)
        self.history_text.see(tk.END)  # 滚动到最新消息

    def send_message(self):
        """发送消息到AI模型"""
        user_text = self.input_text.get(1.0, tk.END).strip()
        if not user_text and not self.uploaded_image_path:
            return  # 没有输入内容和图片，不发送

        # 清空输入框
        self.input_text.delete(1.0, tk.END)

        # 添加用户消息到对话历史
        self.add_message("你", user_text)

        # 禁用发送按钮，防止重复发送
        self.send_btn.config(state=tk.DISABLED)
        self.current_streaming_sender = None
        self.current_streaming_content = ''
        self.add_message("系统", "正在处理...")

        # 在新线程中处理AI调用，避免界面冻结
        threading.Thread(target=self._process_ai_request, args=(user_text,)).start()

    def _process_ai_request(self, user_text):
        """处理AI请求"""
        try:
            if self.uploaded_image_path:
                # 有图片，调用视觉识别模块
                # 先获取图片的URL（这里简化处理，实际应用中可能需要先上传图片到服务器）
                # 为了演示，我们假设图片已经可以通过URL访问
                # 实际应用中，这里需要添加图片上传逻辑
                image_url = self._get_image_url(self.uploaded_image_path)
                self.root.after(0, lambda: self.add_message("系统", f"正在分析图片..."))
                # 准备上下文历史，只包含用户和AI的消息
                context_history = [(sender, msg) for sender, msg in self.conversation_history if sender in ['你', 'AI']]
                # 调用视觉模型，传入上下文和流式输出状态
                visual_result = visual_client.call_visual_model(
                    user_text, 
                    image_url, 
                    conversation_history=context_history, 
                    streaming_enabled=self.streaming_enabled.get(),
                    update_callback=lambda content: self.root.after(0, lambda: self.update_streaming_response('AI(视觉识别)', content))
                )
                self.root.after(0, lambda: self.add_message("AI(视觉识别)", visual_result))
                # 清除图片，准备下一次对话
                self.root.after(0, self.clear_image)
                # 使用视觉识别结果作为输入调用文本模型
                # 调用文本模型，传入上下文和流式输出状态
                final_result = text_client.call_text_model(
                    f"基于以下图片分析结果回答问题: {visual_result}\n问题: {user_text}",
                    conversation_history=context_history,
                    streaming_enabled=self.streaming_enabled.get(),
                    update_callback=lambda content: self.root.after(0, lambda: self.update_streaming_response('AI', content))
                )
            else:
                  # 纯文本，调用文本模块
                  # 准备上下文历史，只包含用户和AI的消息
                  context_history = [(sender, msg) for sender, msg in self.conversation_history if sender in ['你', 'AI']]
                  # 调用文本模型，传入上下文和流式输出状态
                  final_result = text_client.call_text_model(
                      user_text,
                      conversation_history=context_history,
                      streaming_enabled=self.streaming_enabled.get(),
                      update_callback=lambda content: self.root.after(0, lambda: self.update_streaming_response('AI', content))
                  )

            # 在主线程中更新UI
            self.root.after(0, lambda: self.add_message("AI", final_result))
        except Exception as e:
            self.root.after(0, lambda: self.add_message("错误", f"处理请求时出错: {str(e)}"))
        finally:
            # 恢复发送按钮状态
            self.root.after(0, lambda: self.send_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.add_message("系统", "处理完成"))

    def update_streaming_response(self, sender, content):
        """更新流式输出响应"""
        if self.current_streaming_sender != sender:
            # 新的流式响应开始
            self.current_streaming_sender = sender
            self.current_streaming_content = content
            self.add_message(sender, content)
        else:
            # 更新现有流式响应
            self.current_streaming_content = content
            # 移除最后一条消息
            self.history_text.config(state=tk.NORMAL)
            # 删除最后两个换行符和消息内容
            last_line_start = self.history_text.index(f"end-2l linestart")
            self.history_text.delete(last_line_start, tk.END)
            # 添加更新后的内容
            self.history_text.insert(tk.END, f"{sender}: {content}\n\n")
            self.history_text.config(state=tk.DISABLED)
            self.history_text.see(tk.END)

    def _get_image_url(self, image_path):
        """将本地图片转换为Base64编码的data URL"""
        import base64
        try:
            with open(image_path, "rb") as image_file:
                # 读取图片并转换为Base64
                base64_data = base64.b64encode(image_file.read()).decode('utf-8')
                # 获取图片格式
                import os
                ext = os.path.splitext(image_path)[1].lower().replace('.', '')
                if ext == 'jpg':
                    ext = 'jpeg'
                # 返回data URL
                return f"data:image/{ext};base64,{base64_data}"
        except Exception as e:
            self.add_message("错误", f"图片编码失败: {str(e)}")
            return None

if __name__ == "__main__":
    root = tk.Tk()
    app = AIClientGUI(root)
    root.mainloop()