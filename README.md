# Hysteria2 一键部署脚本

## 功能特点
- 🚀 **一键部署**：自动下载、配置、启动 Hysteria2
- ⚡ **性能优化**：内置 BBR 拥塞控制和 QUIC 窗口优化
- 🔄 **智能检测**：避免重复下载和配置生成
- 🛠️ **硬编码支持**：支持预设端口和 SNI，实现完全自动化

## 快速开始

### 1. 设置硬编码配置（可选）
编辑脚本开头的配置：
```python
PRESET_PORT = 2170              # 设置端口
PRESET_SNI = "node1.lunes.host" # 设置 SNI 域名
```

### 2. 运行脚本
```bash
python3 hy2.py
```

## 性能优化说明
脚本已内置以下优化配置：
- **BBR 拥塞控制**：提供更好的网络适应性
- **QUIC 窗口优化**：
  - `initStreamReceiveWindow`: 26MB（提升单流速度）
  - `maxStreamReceiveWindow`: 26MB
  - `initConnReceiveWindow`: 64MB（提升总连接速度）  
  - `maxConnReceiveWindow`: 64MB
  - `maxIncomingStreams`: 1024（支持更多并发）
- **带宽设置**：默认 1Gbps 上下行（防止客户端带宽限制）

## 文件结构
```
/home/container/
├── hysteria                    # Hy2 二进制文件
└── hy2/
    ├── config.json            # 配置文件
    ├── hysteria.crt           # 自签证书
    └── hysteria.key           # 私钥文件
```

## 环境要求
- Python 3.6+
- openssl
- 网络连接（首次下载）

## 重新运行优势
- 已存在的组件会被跳过
- 保持 UUID 等配置一致
- 秒级启动