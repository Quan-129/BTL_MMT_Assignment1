# start_tracker.py

import json
import argparse
from daemon.weaprous import WeApRous

# Dùng một port khác cho tracker để tránh xung đột
TRACKER_PORT = 9999 

# 1. Khởi tạo một dictionary để lưu các peer đang hoạt động
# Định dạng: { 'peer_id': {'ip': 'x.x.x.x', 'port': yyyy, 'username': 'user'} }
# Chúng ta sẽ dùng username làm key tạm thời để lưu trữ
active_peers = {}

app = WeApRous()

# 2. API để các peer tự đăng ký (POST)
@app.route('/submit-info', methods=['POST'])
def submit_info(headers, body):
    """
    Xử lý việc đăng ký của peer.
    Mong đợi một body dạng JSON chứa 'peer_id' (là username), 'ip', và 'port'.
    """
    try:
        peer_data = json.loads(body)
        
        # Peer client gửi 'peer_id' là username (ví dụ: 'Alice')
        username = peer_data.get('peer_id') 
        
        if not username:
             raise KeyError("Missing peer_id (username)")
        
        # Lưu thông tin peer
        active_peers[username] = {
            'username': username,
            'ip': peer_data['ip'],
            'port': peer_data['port']
        }
        
        print(f"[Tracker] Đã đăng ký peer: {username} tại {peer_data['ip']}:{peer_data['port']}")
        
        # Giá trị trả về cho POST có thể là một xác nhận đơn giản
        return json.dumps({"status": "thành công", "message": f"Peer {username} đã được đăng ký."})
    
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[Tracker] Lỗi khi xử lý thông tin peer: {e}")
        # Trả về một response lỗi phù hợp
        return json.dumps({"status": "lỗi", "message": f"Định dạng dữ liệu không hợp lệ: {e}"})

# 3. API để các peer lấy danh sách các peer khác đang hoạt động (GET)
@app.route('/get-list', methods=['GET'])
def get_list(headers, body):
    """
    Trả về danh sách các peer đang hoạt động dưới dạng JSON ARRAY (Danh sách các đối tượng).
    Điều này giúp Peer Client dễ dàng lặp qua và cập nhật PEER_MAP.
    """
    print("[Tracker] Một peer đã yêu cầu danh sách hoạt động.")
    
    # CHỈNH SỬA QUAN TRỌNG:
    # Lấy TẤT CẢ các giá trị (dictionary của từng peer) từ active_peers
    # và chuyển nó thành một DANH SÁCH.
    peer_list_values = list(active_peers.values())
    
    # Trả về đối tượng JSON chứa danh sách peer
    return json.dumps({"peers": peer_list_values})

if __name__ == "__main__":
    import os
    import sys
    
    # Thêm dòng này để xử lý lỗi parser trong môi trường VSCode/terminal
    if 'idlelib' in sys.modules:
        sys.argv = [sys.argv[0]] 
    
    parser = argparse.ArgumentParser(prog='Tracker', description='Tracker server cho ứng dụng chat P2P')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=TRACKER_PORT)
 
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    app.prepare_address(ip, port)
    app.run()