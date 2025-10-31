# start_tracker.py

import json
import argparse
from daemon.weaprous import WeApRous

# Dùng một port khác cho tracker để tránh xung đột
TRACKER_PORT = 9999 

# 1. Khởi tạo một dictionary để lưu các peer đang hoạt động
# Định dạng: { 'peer_id': {'ip': 'x.x.x.x', 'port': yyyy} }
active_peers = {}

app = WeApRous()

# 2. API để các peer tự đăng ký
@app.route('/submit-info', methods=['POST'])
def submit_info(headers, body):
    """
    Xử lý việc đăng ký của peer.
    Mong đợi một body dạng JSON chứa 'peer_id', 'ip', và 'port'.
    """
    try:
        peer_data = json.loads(body)
        peer_id = peer_data['peer_id']
        active_peers[peer_id] = {
            'ip': peer_data['ip'],
            'port': peer_data['port']
        }
        print(f"[Tracker] Đã đăng ký peer: {peer_id} tại {peer_data['ip']}:{peer_data['port']}")
        print(f"[Tracker] Các peer hiện tại: {active_peers}")
        # Giá trị trả về cho POST có thể là một xác nhận đơn giản
        return json.dumps({"status": "thành công", "message": f"Peer {peer_id} đã được đăng ký."})
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[Tracker] Lỗi khi xử lý thông tin peer: {e}")
        # Trong ứng dụng thực tế, bạn nên trả về một response lỗi phù hợp
        return json.dumps({"status": "lỗi", "message": "Định dạng dữ liệu không hợp lệ."})

# 3. API để các peer lấy danh sách các peer khác đang hoạt động
@app.route('/get-list', methods=['GET'])
def get_list(headers, body):
    """
    Trả về danh sách các peer đang hoạt động dưới dạng đối tượng JSON.
    """
    print("[Tracker] Một peer đã yêu cầu danh sách hoạt động.")
    return json.dumps(active_peers)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='Tracker', description='Tracker server cho ứng dụng chat P2P')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=TRACKER_PORT)
 
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    app.prepare_address(ip, port)
    app.run()