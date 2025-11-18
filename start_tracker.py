# start_tracker.py (Phiên bản Bổ sung Channel Management)

import json
import argparse
from daemon.weaprous import WeApRous
import sys

# Dùng một port khác cho tracker để tránh xung đột
TRACKER_PORT = 9999 

# 1. Khởi tạo một dictionary để lưu các peer đang hoạt động
active_peers = {}

# 2. KHỞI TẠO DICTIONARY LƯU TRỮ CÁC KÊNH (ACTIVE CHANNELS)
# Format: {'group1': {'owner': 'alice', 'members': ['alice', 'bob']}}
active_channels = {}

app = WeApRous()

# --- HÀM TRỢ GIÚP: XÂY DỰNG PHẢN HỒI JSON HOÀN CHỈNH ---
def build_tracker_response(status_code, data_dict):
    """
    Hàm trợ giúp xây dựng phản hồi HTTP thô (raw HTTP response) 
    với Content-Length chính xác cho phản hồi JSON.
    """
    response_body = json.dumps(data_dict)
    
    status_line = {
        200: "200 OK", 
        400: "400 Bad Request", 
        404: "404 Not Found",
        409: "409 Conflict", # Mã này hữu ích khi tạo kênh đã tồn tại
        500: "500 Internal Server Error", 
        503: "503 Service Unavailable"
    }.get(status_code, "200 OK")
    
    response_lines = [
        f"HTTP/1.1 {status_line}",
        "Content-Type: application/json; charset=utf-8",
        f"Content-Length: {len(response_body)}", 
        "Connection: close",
        "",
        response_body
    ]
    # NOTE: WeApRous cần tuple (string, int). String này là Raw HTTP Response.
    return "\r\n".join(response_lines), status_code


# 3. API ĐỂ CÁC PEER TỰ ĐĂNG KÝ (POST)
@app.route('/submit-info', methods=['POST'])
def submit_info(headers, body):
    """
    Xử lý việc đăng ký của peer. (Không đổi)
    """
    try:
        peer_data = json.loads(body)
        username = peer_data.get('peer_id') 
        
        if not username:
             return build_tracker_response(400, {"status": "lỗi", "message": "Missing peer_id (username)"})
        
        # Lưu thông tin peer
        active_peers[username] = {
            'username': username,
            'ip': peer_data['ip'],
            'port': peer_data['port']
        }
        
        print(f"[Tracker] Đã đăng ký peer: {username} tại {peer_data['ip']}:{peer_data['port']}")
        
        return build_tracker_response(200, {"status": "thành công", "message": f"Peer {username} đã được đăng ký."})
    
    except Exception as e:
        print(f"[Tracker] Lỗi khi xử lý thông tin peer: {e}")
        return build_tracker_response(500, {"status": "lỗi", "message": f"Lỗi nội bộ Tracker: {e}"})


# 4. API ĐỂ CÁC PEER LẤY DANH SÁCH CÁC PEER KHÁC ĐANG HOẠT ĐỘNG (GET)
@app.route('/get-list', methods=['GET'])
def get_list(headers, body):
    """
    Trả về danh sách các peer đang hoạt động dưới dạng JSON. (Không đổi)
    """
    print("[Tracker] Một peer đã yêu cầu danh sách hoạt động.")
    
    peer_list_values = list(active_peers.values())
    
    return build_tracker_response(200, {"peers": peer_list_values})

# --------------------------------------------------------------------------
# --- CÁC API MỚI CHO CHANNEL MANAGEMENT ---
# --------------------------------------------------------------------------

# 5. API TẠO KÊNH (POST)
@app.route('/create-channel', methods=['POST'])
def create_channel(headers, body):
    """
    Tạo một kênh chat mới.
    Body: {'channel_name': 'group1', 'owner': 'alice'}
    """
    try:
        data = json.loads(body)
        channel_name = data.get('channel_name')
        owner = data.get('owner')

        if not channel_name or not owner:
            return build_tracker_response(400, {"status": "lỗi", "message": "Missing channel_name or owner"})

        # Kiểm tra tên kênh đã tồn tại chưa
        if channel_name in active_channels:
            return build_tracker_response(409, {"status": "lỗi", "message": f"Kênh '{channel_name}' đã tồn tại."})

        # Kiểm tra owner có phải là peer đang hoạt động không
        if owner not in active_peers:
             return build_tracker_response(400, {"status": "lỗi", "message": f"Owner '{owner}' không phải là peer đang hoạt động."})

        # Tạo kênh mới, owner tự động là thành viên đầu tiên
        active_channels[channel_name] = {
            'owner': owner,
            'members': [owner]
        }
        
        print(f"[Tracker] Đã tạo kênh mới: {channel_name}, Owner: {owner}")
        return build_tracker_response(200, {"status": "thành công", "message": f"Kênh '{channel_name}' đã được tạo."})

    except Exception as e:
        print(f"[Tracker] Lỗi khi tạo kênh: {e}")
        return build_tracker_response(500, {"status": "lỗi", "message": f"Lỗi nội bộ Tracker: {e}"})


# 6. API THAM GIA KÊNH (POST)
@app.route('/join-channel', methods=['POST'])
def join_channel(headers, body):
    """
    Thêm một thành viên vào kênh.
    Body: {'channel_name': 'group1', 'username': 'bob'}
    """
    try:
        data = json.loads(body)
        channel_name = data.get('channel_name')
        username = data.get('username')

        if not channel_name or not username:
            return build_tracker_response(400, {"status": "lỗi", "message": "Missing channel_name or username"})

        # Kiểm tra kênh có tồn tại không
        if channel_name not in active_channels:
            return build_tracker_response(404, {"status": "lỗi", "message": f"Kênh '{channel_name}' không tồn tại."})
        
        # Kiểm tra username có đang hoạt động không
        if username not in active_peers:
             return build_tracker_response(400, {"status": "lỗi", "message": f"Peer '{username}' không hoạt động."})

        # Thêm thành viên nếu chưa có
        if username not in active_channels[channel_name]['members']:
            active_channels[channel_name]['members'].append(username)
            print(f"[Tracker] Peer '{username}' đã tham gia kênh: {channel_name}")
            return build_tracker_response(200, {"status": "thành công", "message": f"Peer '{username}' đã tham gia kênh '{channel_name}'."})
        else:
            return build_tracker_response(200, {"status": "thành công", "message": f"Peer '{username}' đã ở trong kênh '{channel_name}'."})

    except Exception as e:
        print(f"[Tracker] Lỗi khi tham gia kênh: {e}")
        return build_tracker_response(500, {"status": "lỗi", "message": f"Lỗi nội bộ Tracker: {e}"})


# 7. API LẤY DANH SÁCH KÊNH (GET)
@app.route('/get-channels', methods=['GET'])
def get_channels(headers, body):
    """
    Trả về toàn bộ danh sách các kênh đang hoạt động và thông tin thành viên.
    """
    print("[Tracker] Một peer đã yêu cầu danh sách kênh.")
    
    # Trả về bản sao của active_channels để tránh sửa đổi bên ngoài
    return build_tracker_response(200, {"channels": active_channels.copy()})


# 8. API LẤY DANH SÁCH THÀNH VIÊN TRONG KÊNH (GET)
@app.route('/get-members', methods=['GET'])
def get_members(headers, body):
    """
    Body: {'channel_name': 'group1'} (Thực tế GET thường dùng query params)
    Trả về danh sách các peer object (ip/port) của các thành viên trong kênh.
    """
    try:
        # NOTE: Trong RESTful GET, body thường rỗng. Ta sẽ giả định body chứa JSON data 
        # hoặc bạn sẽ cần parse query parameters từ headers/url. 
        # Tạm thời ta giả định body chứa JSON data cho tiện việc test POST client.
        
        # Nếu dùng query params, bạn cần parse thủ công:
        # Ví dụ: channel_name = self.request.url_params.get('channel_name') 
        
        # Tạm thời dùng body cho dễ test:
        data = json.loads(body)
        channel_name = data.get('channel_name')
        
        if not channel_name:
            return build_tracker_response(400, {"status": "lỗi", "message": "Missing channel_name in request body."})

        # Kiểm tra kênh có tồn tại không
        if channel_name not in active_channels:
            return build_tracker_response(404, {"status": "lỗi", "message": f"Kênh '{channel_name}' không tồn tại."})
        
        member_usernames = active_channels[channel_name]['members']
        
        # Lấy thông tin IP/Port từ active_peers cho mỗi thành viên
        member_peer_data = [active_peers[user] for user in member_usernames if user in active_peers]
        
        print(f"[Tracker] Trả về danh sách {len(member_peer_data)} thành viên cho kênh: {channel_name}")
        return build_tracker_response(200, {"channel_name": channel_name, "members": member_peer_data})

    except Exception as e:
        print(f"[Tracker] Lỗi khi lấy danh sách thành viên: {e}")
        return build_tracker_response(500, {"status": "lỗi", "message": f"Lỗi nội bộ Tracker: {e}"})

# --------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    
    # Thêm dòng này để xử lý lỗi parser trong môi trường VSCode/terminal
    if 'idlelib' in sys.modules:
        sys.argv = [sys.argv[0]] 
    
    parser = argparse.ArgumentParser(prog='Tracker', description='Tracker server cho ứng dụng chat P2P')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=TRACKER_PORT)

    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    print(f"Bắt đầu Tracker Server tại http://{ip}:{port}")
    app.prepare_address(ip, port)
    app.run()