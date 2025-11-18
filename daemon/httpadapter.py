# daemon/httpadapter.py (Phiên bản Hoàn thiện, Sửa lỗi ký tự ẩn và Thêm Logging)

from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict
import json
import socket
from urllib.parse import parse_qs

class HttpAdapter:
    """
    A mutable :class:`HTTP adapter <HTTP adapter>` for managing client connections
    and routing requests.
    """

    __attrs__ = [
        "ip", "port", "conn", "connaddr", "routes", "request", "response",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        """
        Initialize a new HttpAdapter instance.
        """
        #: IP address.
        self.ip = ip
        #: Port.
        self.port = port
        #: Connection
        self.conn = conn
        #: Conndection address
        self.connaddr = connaddr
        #: Routes
        self.routes = routes
        #: Request
        self.request = Request()
        #: Response
        self.response = Response()

    def get_request_cookies(self, req):
        """
        Extracts cookies from the request headers.
        """
        cookies = {}
        if req.headers is None:
            return cookies
            
        cookie_header = req.headers.get('Cookie') 
        if cookie_header:
            for pair in cookie_header.split(';'):
                try:
                    key, value = pair.strip().split('=', 1) 
                    cookies[key] = value
                except ValueError:
                    continue 
        return cookies

    def handle_client(self, conn, addr, routes):
        self.conn = conn 
        self.connaddr = addr
        req = self.request
        resp = self.response
        response = None

        try:
            msg_bytes = conn.recv(4096)
            if not msg_bytes:
                conn.close()
                return
            msg = msg_bytes.decode('utf-8', errors='ignore')

        except ConnectionResetError:
            print("[Error] Connection reset by client.")
            return

        header_part, _, body_part = msg.partition('\r\n\r\n')
        
        # 1. Chuẩn bị Request
        req.prepare(header_part, routes)
        req.body = body_part
        req.cookies = self.get_request_cookies(req)

        current_path = req.path
        is_authenticated = req.cookies.get('auth') == 'true'

        # --- TASK 2: XỬ LÝ API ROUTE (req.hook) ---
        if req.hook:
            # Logic xử lý API Chat (sử dụng logic route của WeApRous)
            
            try:
                # req.hook trả về tuple (raw_response_string, status_code)
                raw_response_string, status_code = req.hook(headers=req.headers, body=req.body)
            except Exception as e:
                # Xử lý lỗi nếu API Chat gặp lỗi
                print(f"[API ERROR] Hook execution failed: {e}")
                raw_response_string = json.dumps({"status": "error", "message": f"Server error: {e}"})
                status_code = 500
            
            # Phục vụ phản hồi API thô (đã được định dạng sẵn)
            response = raw_response_string.encode('utf-8')
            
        # --- TASK 1: XỬ LÝ ĐĂNG NHẬP & ACCESS CONTROL ---
        else:
            # 1A. Xử lý POST /login (Xác thực và Set-Cookie)
            if req.method == 'POST' and current_path == '/login':
                # Parse body (application/x-www-form-urlencoded)
                params = parse_qs(req.body)
                
                username = params.get('username', [None])[0]
                password = params.get('password', [None])[0]

                if username == 'admin' and password == 'password':
                    # LOGGING: Login thành công
                    print("[AUTH SUCCESS] User 'admin' logged in and cookie 'auth=true' set.")
                    
                    # 1. Thiết lập Cookie (Path=/)
                    resp.set_cookie('auth', 'true', path='/') 
                    
                    # 2. Phục vụ index.html (trang Chat UI)
                    req.path = '/index.html' 
                    response = resp.build_response(req) 
                else:
                    # LOGGING: Login thất bại
                    print("[AUTH FAIL] Invalid credentials submitted. Returning 401.")
                    # Đăng nhập thất bại -> 401
                    response = resp.build_unauthorized()

            # 1B. Xử lý GET / và /index.html (Kiểm soát truy cập)
            elif req.method == 'GET':
                
                is_protected_path = (current_path == '/' or current_path == '/index.html')

                # Buộc chuyển hướng đến /login nếu chưa xác thực
                if is_protected_path and not is_authenticated:
                    
                    # LOGGING: Truy cập bị từ chối
                    print(f"[ACCESS DENIED] Access to {current_path} denied. Cookie 'auth=true' missing/invalid.")
                    
                    # Chuyển hướng (Redirect 302) đến /login để lấy form
                    redirect_lines = [
                        "HTTP/1.1 302 Found",
                        "Location: /login",
                        "Content-Length: 0",
                        "Connection: close",
                        "",
                        ""
                    ]
                    response = "\r\n".join(redirect_lines).encode('utf-8')

                elif is_protected_path and is_authenticated:
                    # LOGGING: Truy cập thành công
                    print(f"[ACCESS GRANTED] Access to {current_path} successful. Serving Chat UI.")
                    
                    # Nếu đã xác thực -> phục vụ index.html (Chat UI)
                    if current_path == '/':
                        req.path = '/index.html'
                    response = resp.build_response(req) 
                    
                else:
                    # Phục vụ các file tĩnh khác (login.html, css, js, images)
                    response = resp.build_response(req) 

        # --- GỬI PHẢN HỒI ---
        
        # Gửi response và đóng kết nối
        if response:
            conn.sendall(response)
            
        conn.close()
    
    # --- CÁC HÀM KHÁC (GIỮ NGUYÊN HOẶC MÔ PHỎNG) ---
    # NOTE: Bạn phải đảm bảo các hàm này tồn tại trong các module khác của bạn:

    def build_response(self, req, resp):
        """Builds a :class:`Response <Response>` object 
        (Cần được định nghĩa trong Response.py để xử lý Set-Cookie)
        """
        response = Response()
        # ... (giữ nguyên logic gốc hoặc đảm bảo nó gọi đúng hàm trong Response)
        return response 

    def build_proxy_headers(self, proxy):
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. 
        """
        headers = {}
        username, password = ("user1", "password")

        if username:
            headers["Proxy-Authorization"] = (username, password)

        return headers
    
    @property
    def extract_cookies(self, req, resp):
        """Build cookies from the :class:`Request <Request>` headers."""
        # Giữ nguyên logic gốc nếu cần
        cookies = {}
        # ... (logic gốc)
        return cookies

    def add_headers(self, request):
        """
        Add headers to the request.
        """
        pass