#!/usr/bin/env python3

def prompt_text(prompt_message, default=None, allow_empty=False):
    """在交互式环境中打印提示并读取用户输入"""
    while True:
        message = prompt_message
        if default is not None:
            message += f" (默认: {default})"
        message += ": "
        user_input = input(message).strip()

        if user_input:
            return user_input

        if default is not None:
            return default

        if allow_empty:
            return ""

        print("输入不能为空，请重新输入。")

def prompt_port(default=443):
    while True:
        value = prompt_text("请输入服务器监听端口", default=default)
        try:
            port = int(value)
            if 1 <= port <= 65535:
                return port
            print("端口号必须在 1-65535 之间。")
        except ValueError:
            print("请输入有效的数字端口号。")

if __name__ == "__main__":
    print("测试交互提示是否立即显示...")
    
    # 测试端口输入
    port = prompt_port(default=2170)
    print(f"你输入的端口是: {port}")
    
    # 测试SNI输入
    sni = prompt_text("请输入用于 SNI 的域名", default="bing.com")
    print(f"你输入的SNI是: {sni}")
    
    print("测试完成！")