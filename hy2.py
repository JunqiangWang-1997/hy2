#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import uuid
import json
import urllib.request
import urllib.error
from urllib.parse import quote

# --- 配置项 ---
HYSTERIA_VERSION = "v2.6.3"  # 您可以修改为希望安装的特定版本
BASE_DIR = "/home/container"
INSTALL_PATH = os.path.join(BASE_DIR, "hysteria")
CONFIG_DIR = os.path.join(BASE_DIR, "hy2")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

# --- 硬编码配置（设置后将跳过交互输入） ---
PRESET_PORT = 2170  # 例如: 2170
PRESET_SNI = "node1.lunes.host"  # 例如: "node1.lunes.host"

REQUIRED_COMMANDS = {
    "openssl": "请先安装 openssl（例如：apt install openssl）"
}

OPTIONAL_COMMAND_HINTS = {
    "qrencode": "如需二维码输出，可通过 'apt install qrencode' 安装"
}

# --- 颜色代码 ---
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
ENDC = '\033[0m'

def get_input(prompt, default=None):
    """简化的输入函数"""
    message = f"{prompt} (默认: {default}): " if default else f"{prompt}: "
    print(message, end="", flush=True)
    value = input().strip()
    return value or default

def check_environment_status():
    """检查环境状态，返回各组件是否已存在"""
    status = {
        "hysteria_binary": os.path.exists(INSTALL_PATH) and os.access(INSTALL_PATH, os.X_OK),
        "config_file": os.path.exists(CONFIG_PATH),
        "certificates": False,
        "config_data": None
    }
    
    # 检查证书文件
    cert_path = os.path.join(CONFIG_DIR, "hysteria.crt")
    key_path = os.path.join(CONFIG_DIR, "hysteria.key")
    status["certificates"] = os.path.exists(cert_path) and os.path.exists(key_path)
    
    # 如果配置文件存在，尝试读取配置
    if status["config_file"]:
        try:
            with open(CONFIG_PATH, "r") as f:
                status["config_data"] = json.load(f)
        except Exception:
            status["config_file"] = False
    
    return status

def ensure_environment():
    """确保环境准备就绪"""
    os.makedirs(BASE_DIR, exist_ok=True)
    if not shutil.which("openssl"):
        print(f"{RED}错误：未检测到 openssl，请先安装{ENDC}")
        sys.exit(1)

def get_server_arch():
    """获取服务器 CPU 架构"""
    try:
        arch = subprocess.check_output(["uname", "-m"]).strip().decode('utf-8')
        if "x86_64" in arch:
            return "amd64"
        elif "aarch64" in arch or "arm64" in arch:
            return "arm64"
        else:
            print(f"{RED}错误：不支持的服务器架构: {arch}{ENDC}")
            sys.exit(1)
    except Exception as e:
        print(f"{RED}错误：无法检测服务器架构: {e}{ENDC}")
        sys.exit(1)

def download_hysteria(arch):
    """从 GitHub 下载 Hysteria2"""
    tag_name = f"app/{HYSTERIA_VERSION}"
    file_name = f"hysteria-linux-{arch}"
    download_url = f"https://github.com/apernet/hysteria/releases/download/{tag_name}/{file_name}"
    download_path = os.path.join(BASE_DIR, file_name)
    
    print(f"{YELLOW}正在从 {download_url} 下载 Hysteria2...{ENDC}")
    
    try:
        with urllib.request.urlopen(download_url, timeout=30) as response, open(download_path, "wb") as f:
            shutil.copyfileobj(response, f)
        print(f"{GREEN}下载成功: {download_path}{ENDC}")
        return download_path
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"{RED}下载失败: {e}{ENDC}")
        sys.exit(1)

def install_hysteria(downloaded_file):
    """安装 Hysteria2 到系统路径"""
    print(f"{YELLOW}正在安装 Hysteria2 到 {INSTALL_PATH}...{ENDC}")
    try:
        os.makedirs(os.path.dirname(INSTALL_PATH), exist_ok=True)

        if os.path.exists(INSTALL_PATH):
            os.remove(INSTALL_PATH)

        shutil.move(downloaded_file, INSTALL_PATH)
        os.chmod(INSTALL_PATH, 0o755)

        version_output = subprocess.check_output([INSTALL_PATH, "version"], text=True)
        print(f"{GREEN}Hysteria2 安装成功！{ENDC}")
        print(f"{GREEN}{version_output.strip()}{ENDC}")
    except (OSError, shutil.Error, subprocess.CalledProcessError) as e:
        print(f"{RED}安装失败: {e}{ENDC}")
        sys.exit(1)

def get_public_ip():
    """获取公网 IPv4 地址"""
    try:
        with urllib.request.urlopen('https://api.ipify.org?format=json', timeout=5) as resp:
            data = resp.read().decode('utf-8')
            return json.loads(data).get('ip')
    except Exception:
        return None

def generate_self_signed_certificate(cert_path, key_path, common_name):
    """生成自签名证书"""
    print(f"{YELLOW}正在生成自签名证书...{ENDC}")
    try:
        subprocess.run([
            "openssl",
            "ecparam",
            "-genkey",
            "-name",
            "prime256v1",
            "-out",
            key_path
        ], check=True)

        subprocess.run([
            "openssl",
            "req",
            "-new",
            "-x509",
            "-key",
            key_path,
            "-out",
            cert_path,
            "-subj",
            f"/CN={common_name}",
            "-days",
            "36500"
        ], check=True)

        os.chmod(key_path, 0o600)
        os.chmod(cert_path, 0o644)
        print(f"{GREEN}自签名证书生成成功!{ENDC}")
    except FileNotFoundError:
        print(f"{RED}未找到 openssl，请确认已安装。{ENDC}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"{RED}生成自签名证书失败: {e}{ENDC}")
        sys.exit(1)


def configure_hysteria(existing_config=None):
    """引导用户完成配置（仅自签证书模式）"""
    print(f"{YELLOW}--- 开始配置 Hysteria2 ---{ENDC}")
    
    # 获取端口配置
    if PRESET_PORT:
        listen_port = PRESET_PORT
        print(f"{GREEN}使用预设端口: {listen_port}{ENDC}")
    elif existing_config and existing_config.get("listen"):
        listen_port = int(existing_config["listen"].lstrip(":"))
        print(f"{GREEN}使用现有配置端口: {listen_port}{ENDC}")
    else:
        port_input = get_input("请输入服务器监听端口", "443")
        listen_port = int(port_input)

    # 生成或使用现有UUID
    if existing_config and existing_config.get("auth", {}).get("password"):
        password = existing_config["auth"]["password"]
        print(f"{GREEN}使用现有 UUID 凭证: {password}{ENDC}")
    else:
        generated_uuid = uuid.uuid4()
        password = str(generated_uuid)
        print(f"{GREEN}已自动生成 UUID 作为连接凭证: {password}{ENDC}")

    os.makedirs(CONFIG_DIR, exist_ok=True)
    cert_path = os.path.join(CONFIG_DIR, "hysteria.crt")
    key_path = os.path.join(CONFIG_DIR, "hysteria.key")

    public_ip = get_public_ip() or get_input("无法自动获取公网IP，请手动输入服务器IP地址")

    # 获取SNI配置
    if PRESET_SNI:
        client_sni = PRESET_SNI
        print(f"{GREEN}使用预设 SNI: {client_sni}{ENDC}")
    else:
        client_sni = get_input("请输入用于 SNI 的域名", "bing.com")

    generate_self_signed_certificate(cert_path, key_path, client_sni)

    config_dict = {
        "listen": f":{listen_port}",
        "auth": {
            "type": "password",
            "password": password
        },
        "ignoreClientBandwidth": True,
        "masquerade": {
            "type": "proxy",
            "proxy": {
                "url": "https://bing.com",
                "rewriteHost": True
            }
        },
        "resolver": {
            "type": "udp",
            "udp": {
                "addr": "1.1.1.1:53"
            },
            "preferIPv6": False
        },
        "tls": {
            "cert": cert_path,
            "key": key_path,
            "alpn": ["h3"]
        },
        "transport": {
    
                "congestion": "bbr"
            }
        }


    with open(CONFIG_PATH, "w") as f:
        json.dump(config_dict, f, indent=2)

    print(f"{GREEN}配置文件已成功写入到 {CONFIG_PATH}{ENDC}")

    print(f"\n{YELLOW}配置概要:{ENDC}")
    print(f"  监听地址 : 0.0.0.0:{listen_port}")
    print(f"  外网地址 : {public_ip}")
    print(f"  SNI 域名 : {client_sni}")
    print(f"  凭证 UUID: {password}")
    print(f"  证书路径 : {cert_path}")
    print(f"  配置文件 : {CONFIG_PATH}\n")

    return {
        "host": public_ip,
        "port": listen_port,
        "password": password,
        "sni": client_sni,
        "insecure": "1"
    }

def generate_client_info(client_config):
    """生成客户端连接信息"""
    password_encoded = quote(client_config["password"])
    url_scheme = (
        f"hysteria2://{password_encoded}@{client_config['host']}:{client_config['port']}/"
        f"?sni={client_config['sni']}&insecure={client_config['insecure']}"
    )
    
    print("\n" + "="*50)
    print(f"{GREEN}🎉 部署完成! 🎉{ENDC}")
    print("\n" + f"{YELLOW}您的客户端连接链接:{ENDC}")
    print(f"{GREEN}{url_scheme}{ENDC}")
    
    if shutil.which("qrencode"):
        try:
            subprocess.run(["qrencode", "-t", "ANSIUTF8", url_scheme], check=True)
        except subprocess.CalledProcessError:
            print(f"\n{YELLOW}提示: 二维码生成失败，请稍后手动执行 'qrencode -t ANSIUTF8 \"{url_scheme}\"'{ENDC}")
    else:
        print(f"\n{YELLOW}提示: {OPTIONAL_COMMAND_HINTS['qrencode']}{ENDC}")


def start_hysteria_service():
    """以当前配置启动 Hysteria2 服务（前台运行）"""
    print(f"{YELLOW}即将使用配置文件启动 Hysteria2: {CONFIG_PATH}{ENDC}")
    print(f"{YELLOW}如果需要停止服务，请使用 Ctrl+C 终止当前进程。{ENDC}")
    sys.stdout.flush()

    args = [INSTALL_PATH, "server", "-c", CONFIG_PATH]
    try:
        os.execv(INSTALL_PATH, args)
    except FileNotFoundError:
        print(f"{RED}未找到可执行文件 {INSTALL_PATH}，请确认安装是否成功。{ENDC}")
    except OSError as e:
        print(f"{RED}启动 Hysteria2 失败: {e}{ENDC}")
    sys.exit(1)


if __name__ == "__main__":
    ensure_environment()
    
    # 检查环境状态
    env_status = check_environment_status()
    print(f"{YELLOW}环境检查结果:{ENDC}")
    print(f"  Hy2 二进制: {'✓' if env_status['hysteria_binary'] else '✗'}")
    print(f"  配置文件: {'✓' if env_status['config_file'] else '✗'}")
    print(f"  证书文件: {'✓' if env_status['certificates'] else '✗'}")
    
    # 根据检查结果决定执行步骤
    if not env_status['hysteria_binary']:
        print(f"{YELLOW}正在下载 Hysteria2...{ENDC}")
        arch = get_server_arch()
        downloaded_file = download_hysteria(arch)
        install_hysteria(downloaded_file)
    else:
        print(f"{GREEN}Hysteria2 二进制已存在，跳过下载步骤{ENDC}")
    
    if not env_status['config_file'] or not env_status['certificates']:
        print(f"{YELLOW}正在生成配置和证书...{ENDC}")
        client_config = configure_hysteria(env_status.get('config_data'))
    else:
        print(f"{GREEN}配置和证书已存在，读取现有配置...{ENDC}")
        config_data = env_status['config_data']
        listen_port = int(config_data["listen"].lstrip(":"))
        password = config_data["auth"]["password"]
        
        # 获取公网IP
        public_ip = get_public_ip() or get_input("无法自动获取公网IP，请手动输入服务器IP地址")
        
        # 从证书中提取SNI（简化处理，使用默认值）
        client_sni = PRESET_SNI or "bing.com"
        
        client_config = {
            "host": public_ip,
            "port": listen_port,
            "password": password,
            "sni": client_sni,
            "insecure": "1"
        }
    
    generate_client_info(client_config)
    start_hysteria_service()