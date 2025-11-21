import socket
import json
import threading
import time
import os
import sys

# --- CẤU HÌNH VÀ GLOBAL STATE ---
# SỬA: Dùng IP LAN thực tế cho Tracker
TRACKER_IP = '127.0.0.1'
TRACKER_PORT = 9999 

PEER_MAP = {}
PEER_MESSAGES_BUFFER = [] # Buffer tin nhắn P2P nhận được, phục vụ Polling

# BIẾN ĐỊA CHỈ IP LAN: Địa chỉ thực của máy tính để peer khác kết nối tới
MY_IP_LAN = '127.0.0.1'

# BIẾN ĐỊA CHỈ BIND: Địa chỉ để server lắng nghe (0.0.0.0 nghe tất cả)
MY_IP_BIND = '127.0.0.1'
# MY_IP_BIND = '0.0.0.0' # <-- ĐÃ CMT LẠI: Địa chỉ chỉ dùng cho test nội bộ

MY_IP = MY_IP_BIND # Mặc định dùng IP lắng nghe cho các hàm bind
MY_PORT = 8000 # [Lưu ý] Port HTTP/WebApp. Port P2P là MY_PORT + 1.

# --- HÀM TRỢ GIÚP CHUNG ---

def _get_p2p_port(http_port):
    """Tính toán port P2P (Port HTTP + 1)"""
    return http_port + 1

def _receive_socket_response(s):
    """Đọc phản hồi thô từ socket và trả về header và body."""
    response_raw = b""
    s.settimeout(3.0) 
    
    while True:
        try:
            chunk = s.recv(1024)
            if not chunk:
                break
            response_raw += chunk
            if b'\r\n\r\n' in response_raw:
                break
        except socket.timeout:
            break
        except Exception:
            break

    response = response_raw.decode('utf-8', errors='ignore')
    header_part, separator, body_part = response.partition('\r\n\r\n')
    
    status_line = header_part.split('\r\n')[0]
    status_code = int(status_line.split()[1]) if len(status_line.split()) > 1 else 500
    
    return status_code, body_part

# --- HÀM MỚI: GỌI CHUNG ĐẾN TRACKER (Dùng cho Channel API) ---

def call_tracker_api(path, method='GET', data=None):
    """
    Hàm proxy gọi API đến Tracker bằng socket thô.
    Trả về dict: {'status_code': int, 'data': dict}
    """
    body = json.dumps(data) if data else ""
    
    request_lines = [
        f"{method} {path} HTTP/1.1",
        f"Host: {TRACKER_IP}:{TRACKER_PORT}",
        "Content-Type: application/json",
        f"Content-Length: {len(body)}",
        "Connection: close",
        "",
        body
    ]
    request = "\r\n".join(request_lines)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((TRACKER_IP, TRACKER_PORT))
            s.sendall(request.encode('utf-8'))
            
            # Đọc phản hồi
            status_code, response_body = _receive_socket_response(s)
            
            # Trích xuất JSON data
            try:
                data_dict = json.loads(response_body)
            except json.JSONDecodeError:
                data_dict = {"status": "error", "message": "Invalid JSON response or body too short."}
            
            return {'status_code': status_code, 'data': data_dict}
            
    except Exception as e:
        return {'status_code': 503, 'data': {"status": "error", "message": f"Tracker connection failed: {e}"}}

# --- LOGIC CLIENT (Giao tiếp với Tracker) ---

def register_with_tracker(username, ip, http_port):
    """
    Gửi thông tin đăng ký đến máy chủ Tracker, sử dụng port P2P.
    SỬA: Luôn gửi MY_IP_LAN (địa chỉ thực) lên Tracker.
    """
    global MY_IP_LAN
    
    p2p_listen_port = _get_p2p_port(http_port) 
    
    data = {
        "peer_id": username,
        "ip": MY_IP_LAN, # Gửi IP LAN thực tế để peer khác kết nối tới
        "port": p2p_listen_port
    }
    
    # Tái sử dụng call_tracker_api cho tính đồng nhất
    response = call_tracker_api("/submit-info", method="POST", data=data)
    return response['status_code'] == 200

def get_peer_list():
    """Yêu cầu danh sách các peer đang hoạt động từ Tracker và cập nhật PEER_MAP."""
    global PEER_MAP
    
    response = call_tracker_api("/get-list", method="GET")
    
    if response['status_code'] == 200:
        peers_list = response['data'].get('peers', [])
        new_map = {}
        for peer_info in peers_list:
            peer_id_full = f"{peer_info['username']}@{peer_info['ip']}:{peer_info['port']}"
            new_map[peer_id_full] = peer_info
            
        PEER_MAP = new_map
        return PEER_MAP
    else:
        # Nếu Tracker không phản hồi 200, trả về None
        return None

# --- LOGIC P2P CHATTING (Client/Server) ---

def _make_p2p_request(ip, port, message):
    """Hàm lõi gửi tin nhắn TCP P2P."""
    
    # Định dạng tin nhắn P2P: [MY_USERNAME] message content
    full_message = f"[{MY_IP_LAN}:{MY_PORT}] {message}" # Sử dụng IP LAN khi gửi

    p2p_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        p2p_socket.connect((ip, port))
        p2p_socket.sendall(full_message.encode('utf-8'))
        p2p_socket.close()
        return True
    except ConnectionRefusedError:
        print(f"[ERROR P2P] Connection refused to {ip}:{port}. Peer offline.")
        raise ConnectionError(f"Connection refused to {ip}:{port}")
    except Exception as e:
        print(f"[ERROR P2P] Error sending message to {ip}:{port}: {e}")
        raise ConnectionError(f"Error sending to {ip}:{port}: {e}")

def send_message_to_peer(peer_id_full, message, peer_list, sender_username=None):
    """Kết nối và gửi tin nhắn đến một peer cụ thể (P2P).

    If sender_username is provided, use it as the bracketed sender. Otherwise
    fall back to using the peer_id_full's username (not recommended).
    """

    target_peer_info = peer_list.get(peer_id_full)

    if not target_peer_info:
        raise ValueError(f"Peer ID '{peer_id_full}' not found or offline.")

    target_ip = target_peer_info['ip']
    target_port = int(target_peer_info['port'])

    # Use the actual sender username if provided; fallback to peer_id_full's username
    sender = sender_username if sender_username else peer_id_full.split('@')[0]
    full_message = f"[{sender}] {message}"

    try:
        _make_p2p_request(target_ip, target_port, full_message)
    except Exception as e:
        # Nếu không phân tích được ID hoặc lỗi gửi
        print(f"[ERROR] Failed to send direct message to {peer_id_full}: {e}")
        raise

def broadcast_message(message):
    """Gửi một tin nhắn đến tất cả các peer trong danh sách, trừ chính mình."""
    global PEER_MAP, MY_IP_LAN
    
    get_peer_list() # Cập nhật danh sách mới nhất
    latest_peer_list = PEER_MAP
    
    my_p2p_port = _get_p2p_port(MY_PORT)
    
    for peer_id_full, peer_data in latest_peer_list.items():
        if peer_data['port'] != my_p2p_port: # Tránh gửi cho chính mình
            try:
                # Gửi tin nhắn P2P
                _make_p2p_request(peer_data['ip'], peer_data['port'], f"[BROADCAST] {message}")
            except Exception:
                pass # Bỏ qua peer không kết nối được

# --- HÀM MỚI: GỬI TIN NHẮN ĐẾN THÀNH VIÊN KÊNH ---

def send_message_to_channel_members(member_list, message, sender_username):
    """
    Gửi tin nhắn P2P đến tất cả các thành viên trong danh sách.
    member_list là list các dict: [{'ip': ip, 'port': p2p_port, 'username': user}]
    """
    success_count = 0
    fail_count = 0
    
    my_p2p_port = _get_p2p_port(MY_PORT)
    
    for peer_data in member_list:
        # Tránh gửi đến chính mình
        if peer_data['port'] != my_p2p_port:
            try:
                # Định dạng tin nhắn P2P: [SENDER_USERNAME] message content
                # Use the sender's username (the one who originated the message),
                # not the recipient's username.
                full_message = f"[{sender_username}] {message}"
                _make_p2p_request(peer_data['ip'], peer_data['port'], full_message)
                success_count += 1
            except Exception:
                fail_count += 1
    
    return success_count, fail_count

# --- LOGIC P2P SERVER LẮNG NGHE ---

def handle_peer_connection(conn, addr):
    """Xử lý tin nhắn P2P đến và LƯU vào buffer."""
    global PEER_MESSAGES_BUFFER
    try:
        message_bytes = conn.recv(1024) 
        if message_bytes:
            message = message_bytes.decode('utf-8', errors='ignore')
            
            # Lấy ra IP:Port P2P của người gửi
            sender_p2p_addr = f"{addr[0]}:{addr[1]}" 
            
            PEER_MESSAGES_BUFFER.append({
                "sender_addr": sender_p2p_addr, # LƯU PORT P2P. JS cần suy luận ngược lại.
                "message": message,
                "timestamp": time.time()
            })
            
    except Exception:
        pass
    finally:
        conn.close()

def peer_server_thread(ip, port):
    """Luồng chạy server để lắng nghe kết nối P2P từ các peer khác."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # LƯU Ý: ip ở đây phải là 0.0.0.0 hoặc IP LAN để nghe từ mạng ngoài
        server.bind((ip, port)) 
    except OSError as e:
        print(f"[P2P Server ERROR] KHÔNG THỂ BIND VÀO PORT {port}: {e}")
        return 
    server.listen(5)

    while True:
        try:
            conn, addr = server.accept()
            client_handler = threading.Thread(target=handle_peer_connection, args=(conn, addr))
            client_handler.daemon = True
            client_handler.start()
        except Exception:
            break

def init_peer_server(ip, http_port):
    """Khởi động P2P Server trong luồng nền."""
    global MY_IP, MY_PORT
    
    p2p_listen_port = _get_p2p_port(http_port)
    
    # Đảm bảo server lắng nghe trên IP chính xác mà start_sampleapp.py cung cấp (0.0.0.0)
    MY_IP = ip
    MY_PORT = http_port
    
    server_thread = threading.Thread(target=peer_server_thread, args=(ip, p2p_listen_port))
    server_thread.daemon = True
    server_thread.start()
    time.sleep(1)

    print(f"[P2P Server] Lắng nghe P2P trên port riêng: {p2p_listen_port}")