# start_sampleapp.py (Phiên bản Bổ sung Channel Management API)

import json
import socket
import argparse
import threading
import os
import sys
# Thêm requests hoặc tương đương để gọi API từ Tracker
import requests # Sử dụng thư viện requests tiêu chuẩn (giả định có thể dùng)
from urllib.parse import parse_qs

from daemon.weaprous import WeApRous
import peer

PORT = 8000

app = WeApRous()

# --- HELPER FUNCTIONS (CHO TASK 1 VÀ JSON API) ---
# ... (Giữ nguyên các hàm build_json_response, build_401_response, build_file_response, v.v.)
# (Phần này được giữ nguyên như trong input của bạn)
def build_json_response(status_code, data_dict):
    """Xây dựng phản hồi JSON thô cho các API Chat."""
    
    body = json.dumps(data_dict)
    encoded_body = body.encode('utf-8')
    status_line = {
        200: "200 OK",
        400: "400 Bad Request",
        500: "500 Internal Server Error",
        503: "503 Service Unavailable"
    }.get(status_code, "200 OK")

    response_lines = [
        f"HTTP/1.1 {status_line}",
        "Content-Type: application/json; charset=utf-8",
        f"Content-Length: {len(encoded_body)}",
        "Connection: close",
        "",
        body
    ]
    return "\r\n".join(response_lines), status_code

# ... (Các hàm khác như build_401_response, build_file_response, build_welcome_response được giữ nguyên)
def build_401_response():
    """Tạo phản hồi 401 Unauthorized đơn giản."""
    body = "<h1>401 Unauthorized</h1><p>Access denied. Please log in.</p>"
    response_lines = [
        "HTTP/1.1 401 Unauthorized",
        "Content-Type: text/html",
        f"Content-Length: {len(body)}",
        "Connection: close",
        "",
        body
    ]
    return "\r\n".join(response_lines), 401

def build_file_response(filename, set_cookie=None):
    """Tạo phản hồi 200 OK với file HTML từ www/."""
    try:
        filepath = os.path.join("www", filename)
        with open(filepath, "r", encoding="utf-8") as f:
            body = f.read()
            response_lines = [
                "HTTP/1.1 200 OK",
                "Content-Type: text/html; charset=utf-8",
                f"Content-Length: {len(body)}",
                "Connection: close",
            ]
            if set_cookie:
                response_lines.append(f"Set-Cookie: {set_cookie}")
            response_lines.append("")
            response_lines.append(body)

            return "\r\n".join(response_lines), 200
    except FileNotFoundError:
        # Giả định 404 cho tiện, bạn có thể thay đổi bằng hàm 404 chuẩn hơn
        return build_401_response() 

def build_welcome_response(set_cookie=None):
    """Tạo phản hồi 200 OK với trang chào mừng (ảnh + nút)."""

    body = """
<!doctype html>
<html>
<head>
    <title>bksysnet@hcmut welcome</title>
    <meta charset="utf-8" />
    <meta http-equiv="Content-type" content="text/html; charset=utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
        body {
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            align-items: center;
            height: 100vh;
            width: 100vw;
            margin: 0; 
            background: #fff;
            text-align: center;
        }
        .welcome-content {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 50px 20px 20px;
        }
        .logo-img {
            width: 700px;        /* Kích thước mong muốn (thay 700px bằng giá trị bạn muốn) */
            max-width: 90vw;     /* Đảm bảo ảnh co lại trên màn hình nhỏ */
            height: auto;
            margin-bottom: 30px;
        }
        .chat-btn {
            background-color: #cc0000;
            color: white;
            padding: 15px 30px;
            margin-top: 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1.2em;
            text-transform: uppercase;
        }
    </style>
</head>
<body>
    
    <div class="welcome-content">
        <img src="/static/images/welcome1.png" alt="bksysnet at HCMUT" class="logo-img">
        
        <button class="chat-btn" onclick="window.location.href='/register.html'">Enter Chat room</button>
    </div>
</body>
</html>
    """

    response_lines = [
        "HTTP/1.1 200 OK",
        "Content-Type: text/html; charset=utf-8",
        f"Content-Length: {len(body)}",
        "Connection: close",
    ]
    if set_cookie:
        response_lines.append(f"Set-Cookie: {set_cookie}")
    response_lines.append("")
    response_lines.append(body)

    return "\r\n".join(response_lines), 200
# --- TASK 1: COOKIE SESSION VÀ PHỤC VỤ TRANG ---
# ... (Các route / , /login.html, /login, /welcome, /register.html, /index.html được giữ nguyên)
@app.route('/', methods=['GET'])
def index_access(headers="guest", body="anonymous"):
    redirect_lines = [
        "HTTP/1.1 302 Found",
        "Location: /login.html",
        "Content-Length: 0",
        "Connection: close",
        "",
        ""
    ]
    return "\r\n".join(redirect_lines), 302


@app.route('/login.html', methods=['GET'])
def serve_login_page(headers="guest", body="anonymous"):
    return build_file_response("login.html")


@app.route('/login', methods=['POST'])
def login(headers="guest", body="anonymous"):
    print(f"[LOGIN] Received POST /login with body: {body}")
    if "username=admin" in body and "password=password" in body:
        print(f"[LOGIN] Credentials valid. Returning response with Set-Cookie: auth=true")
        response, status = build_welcome_response(set_cookie="auth=true; Path=/")
        print(f"[LOGIN] First 500 chars of response: {response[:500]}")
        return response, status
    else:
        print(f"[LOGIN] Invalid credentials. Returning 401.")
        return build_401_response()


@app.route('/welcome', methods=['GET'])
def serve_welcome_page(headers="guest", body="anonymous"):
    return build_welcome_response()


@app.route('/register.html', methods=['GET'])
def serve_register_page(headers="guest", body="anonymous"):
    return build_file_response("register.html")


@app.route('/index.html', methods=['GET'])
def serve_chat_ui(headers="guest", body="anonymous"):
    return build_file_response("index.html")


# --- TASK 2: HYBRID CHAT API (Cũ và Mới) ---

@app.route('/register-peer', methods=['POST'])
def register_route(headers="guest", body="anonymous"):
    try:
        data = json.loads(body)
        username = data.get('username')
        
        if not username:
            return build_json_response(400, {"status": "error", "message": "Username required"})

        # Giả định peer.register_with_tracker đã được cập nhật để gửi cả username lên Tracker
        if peer.register_with_tracker(username, peer.MY_IP, peer.MY_PORT):
            p2p_port = peer._get_p2p_port(peer.MY_PORT)
            
            # CHỈ TRẢ VỀ JSON RESPONSE CHUẨN (KHÔNG SET-COOKIE LẠI)
            # Cookie 'auth=true' đã được đặt khi POST /login thành công.
            return build_json_response(200, {"status": "success", "peer_id": f"{username}@{peer.MY_IP}:{p2p_port}"})
            
        else:
            return build_json_response(503, {"status": "error", "message": "Failed to register with Tracker"})
        
    except Exception as e:
        return build_json_response(500, {"status": "error", "message": str(e)})

@app.route('/get-list', methods=['GET'])
def get_list_route(headers="guest", body="anonymous"):
    # Lấy danh sách Peer từ Tracker
    current_list = peer.get_peer_list()
    if current_list is None:
        return build_json_response(503, {"peers": [], "message": "Tracker unreachable"})
        
    return build_json_response(200, {"peers": list(current_list.values())})


# --------------------------------------------------------------------------
# --- API QUẢN LÝ KÊNH (Proxy tới Tracker) ---
# --------------------------------------------------------------------------

@app.route('/create-channel', methods=['POST'])
def create_channel_route(headers="guest", body="anonymous"):
    """Proxy API: Tạo kênh trên Tracker Server."""
    try:
        data = json.loads(body)
        channel_name = data.get('channel_name')
        owner = data.get('owner') # Tên người dùng hiện tại

        # Giả định peer.call_tracker_api() là hàm xử lý gọi đến Tracker
        tracker_response = peer.call_tracker_api(
            '/create-channel', 
            method='POST', 
            data={'channel_name': channel_name, 'owner': owner}
        )
        
        # Trả về phản hồi nguyên vẹn từ Tracker
        return build_json_response(tracker_response['status_code'], tracker_response['data'])

    except Exception as e:
        print(f"[WebApp] Lỗi khi gọi create-channel: {e}")
        return build_json_response(500, {"status": "error", "message": f"WebApp error: {str(e)}"})


@app.route('/join-channel', methods=['POST'])
def join_channel_route(headers="guest", body="anonymous"):
    """Proxy API: Tham gia kênh trên Tracker Server."""
    try:
        data = json.loads(body)
        channel_name = data.get('channel_name')
        username = data.get('username')

        tracker_response = peer.call_tracker_api(
            '/join-channel', 
            method='POST', 
            data={'channel_name': channel_name, 'username': username}
        )
        
        return build_json_response(tracker_response['status_code'], tracker_response['data'])

    except Exception as e:
        print(f"[WebApp] Lỗi khi gọi join-channel: {e}")
        return build_json_response(500, {"status": "error", "message": f"WebApp error: {str(e)}"})


@app.route('/get-channels', methods=['GET'])
def get_channels_route(headers="guest", body="anonymous"):
    """Proxy API: Lấy danh sách kênh từ Tracker Server."""
    try:
        tracker_response = peer.call_tracker_api('/get-channels', method='GET')
        
        return build_json_response(tracker_response['status_code'], tracker_response['data'])

    except Exception as e:
        print(f"[WebApp] Lỗi khi gọi get-channels: {e}")
        return build_json_response(500, {"status": "error", "message": f"WebApp error: {str(e)}"})

# --------------------------------------------------------------------------
# --- CẬP NHẬT API GỬI TIN NHẮN ĐỂ HỖ TRỢ KÊNH ---
# --------------------------------------------------------------------------

@app.route('/send-peer', methods=['POST'])
def send_peer_route(headers="guest", body="anonymous"):
    """
    Gửi tin nhắn. Hỗ trợ 2 chế độ:
    1. Gửi trực tiếp (target_type='peer', target_id=username@ip:port)
    2. Gửi vào kênh (target_type='channel', target_id=channel_name)
    """
    try:
        data = json.loads(body)
        target_id = data.get('target_id') # Có thể là username@ip:port hoặc channel_name
        target_type = data.get('target_type') # 'peer' hoặc 'channel'
        message = data.get('message')
        
        if target_type == 'peer':
            # 1. Gửi trực tiếp P2P; pass through sender_username so receiver sees correct sender
            sender_username = data.get('sender_username') or 'unknown'
            peer.send_message_to_peer(target_id, message, peer.PEER_MAP, sender_username)
            return build_json_response(200, {"status": "success", "mode": "direct_peer"})

        elif target_type == 'channel':
            # 2. Gửi vào kênh: Lấy danh sách thành viên từ Tracker rồi gửi P2P
            channel_name = target_id
            
            # Gọi Tracker để lấy IP/Port của TẤT CẢ thành viên trong kênh
            tracker_response = peer.call_tracker_api(
                '/get-members', 
                method='GET', 
                data={'channel_name': channel_name}
            )
            
            if tracker_response['status_code'] != 200:
                return build_json_response(tracker_response['status_code'], {"status": "error", "message": f"Failed to get channel members from Tracker: {tracker_response['data'].get('message', '')}"})

            member_list = tracker_response['data'].get('members', [])
            
            # Gửi tin P2P đến từng thành viên (hàm này đã chờ sender_username)
            sender_username = data.get('sender_username') or 'unknown'
            success_count, fail_count = peer.send_message_to_channel_members(member_list, message, sender_username)
            
            return build_json_response(200, {
                "status": "success", 
                "mode": "channel_broadcast", 
                "channel": channel_name, 
                "sent_to": success_count,
                "failed": fail_count
            })

        else:
            return build_json_response(400, {"status": "error", "message": "Invalid target_type"})
            
    except ConnectionError as e:
        return build_json_response(503, {"status": "error", "message": f"Connection failed. Target may be offline. Error: {e}"})
    except Exception as e:
        return build_json_response(500, {"status": "error", "message": str(e)})


@app.route('/broadcast-peer', methods=['POST'])
def broadcast_route(headers="guest", body="anonymous"):
    try:
        data = json.loads(body)
        message = data.get('message')
        
        peer.broadcast_message(message)
        
        return build_json_response(200, {"status": "success"})
        
    except Exception as e:
        return build_json_response(500, {"status": "error", "message": str(e)})


@app.route('/check-new-messages', methods=['GET'])
def check_new_messages_route(headers="guest", body="anonymous"):
    messages = peer.PEER_MESSAGES_BUFFER.copy()
    peer.PEER_MESSAGES_BUFFER.clear()
    return build_json_response(200, {"messages": messages})


@app.route('/hello', methods=['PUT'])
def hello(headers, body):
    print("[SampleApp] ['PUT'] Hello in {} to {}".format(headers, body))
    return f"Hello handled successfully: {body}", 200


# --- MAIN RUN LOGIC ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='Backend', description='', epilog='Beckend daemon')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)
    
    args = parser.parse_args()
    ip = args.server_ip
    http_port = args.server_port
    
    # 1. Khởi động P2P Server (trên Port HTTP + 1)
    peer.init_peer_server(ip, http_port)

    # 2. Khởi động WebApp Server (WeApRous)
    print(f"[WeApRous] Preparing to launch HTTP Server on {ip}:{http_port}")
    app.prepare_address(ip, http_port)
    
    try:
        app.run()
    except OSError as e:
        p2p_port = peer._get_p2p_port(http_port)
        if e.winerror == 10048:
            print("-" * 50)
            print(f"[FATAL ERROR] Cổng {http_port} đã bị chiếm, hoặc {p2p_port} bị trùng.")
            print(f"Kiểm tra và giải phóng cổng {http_port} và {p2p_port}.")
            print("-" * 50)
        else:
            raise e