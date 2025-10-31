# peer.py

import socket
import json
import uuid # Dùng để tạo ID ngẫu nhiên cho peer
import threading

# Địa chỉ của máy chủ Tracker
TRACKER_IP = '172.27.213.32'
TRACKER_PORT = 9999

def register_with_tracker(peer_id, ip, port):
    """Gửi thông tin đăng ký đến máy chủ Tracker."""
    
    # 1. Chuẩn bị dữ liệu để gửi đi
    data = {
        "peer_id": peer_id,
        "ip": ip,
        "port": port
    }
    body = json.dumps(data)

    # 2. Xây dựng một request HTTP POST thô (raw)
    request_lines = [
        f"POST /submit-info HTTP/1.1",
        f"Host: {TRACKER_IP}:{TRACKER_PORT}",
        "Content-Type: application/json",
        f"Content-Length: {len(body)}",
        "Connection: close",
        "",
        body
    ]
    request = "\r\n".join(request_lines)

    # 3. Gửi request đến Tracker
    # --- BẮT ĐẦU PHẦN SỬA ---
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((TRACKER_IP, TRACKER_PORT))
            s.sendall(request.encode('utf-8'))
            response = s.recv(1024).decode('utf-8')
            print("[Client] Phản hồi từ Tracker (Đăng ký):")
            print(response)
    except ConnectionRefusedError:
        print(f"[Client] Lỗi: Không thể kết nối đến Tracker tại {TRACKER_IP}:{TRACKER_PORT}. Hãy đảm bảo Tracker đang chạy.")
    except Exception as e:
        print(f"[Client] Lỗi không xác định khi đăng ký với Tracker: {e}")
    # --- KẾT THÚC PHẦN SỬA ---

def get_peer_list():
    """Yêu cầu danh sách các peer đang hoạt động từ Tracker."""

    # 1. Xây dựng một request HTTP GET thô (raw)
    request_lines = [
        f"GET /get-list HTTP/1.1",
        f"Host: {TRACKER_IP}:{TRACKER_PORT}",
        "Connection: close",
        "",
        ""
    ]
    request = "\r\n".join(request_lines)
    
    # 2. Gửi request và nhận phản hồi
    # --- BẮT ĐẦU PHẦN SỬA ---
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((TRACKER_IP, TRACKER_PORT))
            s.sendall(request.encode('utf-8'))
            response_raw = s.recv(1024).decode('utf-8')
            
            header_part, _, body_part = response_raw.partition('\r\n\r\n')
            peer_list = json.loads(body_part)
            
            print("[Client] Danh sách peer nhận được:")
            print(peer_list)
            return peer_list
    except ConnectionRefusedError:
        print(f"[Client] Lỗi: Không thể kết nối đến Tracker tại {TRACKER_IP}:{TRACKER_PORT}. Hãy đảm bảo Tracker đang chạy.")
        return None
    except Exception as e:
        print(f"[Client] Lỗi không xác định khi lấy danh sách peer: {e}")
        return None
    # --- KẾT THÚC PHẦN SỬA ---
    
def handle_peer_connection(conn, addr):
    """Xử lý kết nối từ một peer khác."""
    try:
        print(f"\n[Server Peer] Có kết nối từ {addr}")
        while True:
            message = conn.recv(1024).decode('utf-8')
            if not message:
                break
            # --- BẮT ĐẦU PHẦN SỬA ---
            # In tin nhắn đến một cách rõ ràng
            print(f"\n<<< Tin nhắn từ {addr[0]}:{addr[1]}]: {message}")
            # In lại dấu nhắc lệnh để người dùng biết họ có thể gõ tiếp
            print("Nhập lệnh > ", end="", flush=True)
            # --- KẾT THÚC PHẦN SỬA ---
    except Exception as e:
        print(f"[Server Peer] Lỗi kết nối: {e}")
    finally:
        print(f"[Server Peer] Đã đóng kết nối từ {addr}")
        conn.close()

def peer_server_thread(ip, port):
    """Luồng chạy server để lắng nghe kết nối từ các peer khác."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((ip, port))
    server.listen(5) # Cho phép tối đa 5 kết nối chờ
    print(f"[Server Peer] Đang lắng nghe trên port {port}...")

    while True:
        conn, addr = server.accept()
        # Khi có kết nối mới, tạo một luồng riêng để xử lý
        client_handler = threading.Thread(
            target=handle_peer_connection,
            args=(conn, addr)
        )
        client_handler.start()

def send_message_to_peer(peer_id, message, peer_list):
    """Kết nối và gửi tin nhắn đến một peer cụ thể."""
    
    # 1. Tra cứu thông tin của peer đích
    target_peer_info = peer_list.get(peer_id)
    
    if not target_peer_info:
        print(f"[Client] Lỗi: Không tìm thấy peer với ID '{peer_id}'. Hãy dùng lệnh 'list' để cập nhật.")
        return

    target_ip = target_peer_info['ip']
    target_port = int(target_peer_info['port'])

    # 2. Tạo kết nối socket mới đến peer đó
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((target_ip, target_port))
            s.sendall(message.encode('utf-8'))
            print(f"[Client] Đã gửi tin nhắn đến {peer_id}.")
    except ConnectionRefusedError:
        print(f"[Client] Lỗi: Không thể kết nối đến {peer_id}. Peer có thể đã offline.")
    except Exception as e:
        print(f"[Client] Lỗi không xác định khi gửi tin nhắn: {e}")

def broadcast_message(message, current_peer_list):
    """Gửi một tin nhắn đến tất cả các peer trong danh sách, trừ chính mình."""
    
    print("\n--- Đang gửi broadcast đến tất cả các peer... ---")
    
    # Lấy danh sách mới nhất trước khi gửi để đảm bảo cập nhật
    latest_peer_list = get_peer_list()
    if not latest_peer_list:
        print("[Client] Không thể lấy danh sách peer. Đã hủy broadcast.")
        return

    if len(latest_peer_list) <= 1:
        print("[Client] Không có peer nào khác để gửi broadcast.")
        return

    # Lặp qua tất cả các peer trong danh sách mới nhất
    for peer_id, info in latest_peer_list.items():
        # Không gửi tin nhắn cho chính mình
        if peer_id != MY_ID:
            send_message_to_peer(peer_id, message, latest_peer_list)


if __name__ == "__main__":
    # Thông tin của peer này
    MY_ID = f"peer_{uuid.uuid4().hex[:6]}"
    MY_IP = '172.27.213.32'
    MY_PORT = int(input("Nhập port bạn muốn peer này lắng nghe (ví dụ: 9001, 9002,...): "))

    print(f"--- Bắt đầu Peer: {MY_ID} tại {MY_IP}:{MY_PORT} ---")

    # 1. Khởi chạy server lắng nghe trong một luồng nền
    server_thread = threading.Thread(target=peer_server_thread, args=(MY_IP, MY_PORT))
    server_thread.daemon = True
    server_thread.start()

    # 2. Đăng ký với Tracker
    print("\n--- Đang đăng ký với Tracker... ---")
    register_with_tracker(MY_ID, MY_IP, MY_PORT)

    print("\n--- Peer đã sẵn sàng. Gõ 'list', 'send <id> <msg>', 'broadcast <msg>', hoặc 'exit'. ---")
    active_peers = {} 

    while True:
        command = input("Nhập lệnh > ")
        # Tách lệnh và nội dung tin nhắn
        parts = command.split(" ", 1)
        cmd = parts[0].lower()
        
        if cmd == 'list':
            print("\n--- Đang lấy danh sách peer cập nhật... ---")
            active_peers = get_peer_list()
        
        elif cmd == 'send':
            # ... (logic gửi tin nhắn trực tiếp của Ngày 5 giữ nguyên)
            send_parts = command.split(" ", 2)
            if len(send_parts) < 3:
                print("Lỗi: Cú pháp lệnh là 'send <peer_id> <message>'")
            else:
                peer_id = send_parts[1]
                message = send_parts[2]
                send_message_to_peer(peer_id, message, active_peers)

        # --- BẮT ĐẦU PHẦN SỬA ---
        elif cmd == 'broadcast':
            if len(parts) < 2:
                print("Lỗi: Cú pháp lệnh là 'broadcast <message>'")
            else:
                message = parts[1]
                # Gọi hàm broadcast (sẽ được tạo ở bước tiếp theo)
                broadcast_message(message, active_peers)
        # --- KẾT THÚC PHẦN SỬA ---

        elif cmd == 'exit':
            print("--- Tạm biệt! ---")
            break
        else:
            print(f"Lệnh '{cmd}' không hợp lệ.")