#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.httpadapter
~~~~~~~~~~~~~~~~~

This module provides a http adapter object to manage and persist 
http settings (headers, bodies). The adapter supports both
raw URL paths and RESTful route definitions, and integrates with
Request and Response objects to handle client-server communication.
"""

from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict

class HttpAdapter:
    """
    A mutable :class:`HTTP adapter <HTTP adapter>` for managing client connections
    and routing requests.

    The `HttpAdapter` class encapsulates the logic for receiving HTTP requests,
    dispatching them to appropriate route handlers, and constructing responses.
    It supports RESTful routing via hooks and integrates with :class:`Request <Request>` 
    and :class:`Response <Response>` objects for full request lifecycle management.

    Attributes:
        ip (str): IP address of the client.
        port (int): Port number of the client.
        conn (socket): Active socket connection.
        connaddr (tuple): Address of the connected client.
        routes (dict): Mapping of route paths to handler functions.
        request (Request): Request object for parsing incoming data.
        response (Response): Response object for building and sending replies.
    """

    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        """
        Initialize a new HttpAdapter instance.

        :param ip (str): IP address of the client.
        :param port (int): Port number of the client.
        :param conn (socket): Active socket connection.
        :param connaddr (tuple): Address of the connected client.
        :param routes (dict): Mapping of route paths to handler functions.
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

    # daemon/httpadapter.py

    def handle_client(self, conn, addr, routes):
        self.conn = conn        
        self.connaddr = addr
        req = self.request
        resp = self.response
        response = None

        # Nhận và kiểm tra request rỗng
        try:
            # Tăng kích thước buffer lên 4096 để đảm bảo nhận đủ headers và body
            msg = conn.recv(4096).decode()
        except ConnectionResetError:
            print("[Error] Connection reset by client.")
            return
            
        if not msg:
            print("[Info] Received an empty request, closing connection.")
            conn.close()
            return

        header_part, _, body_part = msg.partition('\r\n\r\n')
        
        # 1. Chuẩn bị Request và Body
        # Lấy cookies từ headers và gán vào req.cookies (quan trọng cho Task 1B)
        req.cookies = self.get_request_cookies(req) 
        req.prepare(header_part, routes)
        req.body = body_part

        # --- BẮT ĐẦU LOGIC SỬA CHO TASK 1 & TASK 2 ---
        
        # 2. Kiểm tra nếu có hook (API route) khớp với request (Task 2: WeApRous)
        if req.hook:
            print("[HttpAdapter] hook in route-path METHOD {} PATH {}".format(req.hook._route_path, req.hook._route_methods))
            
            # Giả định hàm hook trả về chuỗi/dict/json hợp lệ
            json_response_body = req.hook(headers=req.headers, body=req.body)
            
            # Xây dựng response HTTP cho API (giữ nguyên logic bạn đã viết)
            if isinstance(json_response_body, dict):
                response_body_bytes = json.dumps(json_response_body).encode('utf-8')
                content_type = "application/json"
            else: 
                response_body_bytes = str(json_response_body).encode('utf-8')
                content_type = "application/octet-stream" 

            status_line = "HTTP/1.1 200 OK\r\n"
            headers = [
                f"Content-Type: {content_type}",
                f"Content-Length: {len(response_body_bytes)}",
                "Connection: close"
            ]
            header_part = "\r\n".join(headers) + "\r\n\r\n"
            response = status_line.encode('utf-8') + header_part.encode('utf-8') + response_body_bytes

        # 3. Xử lý Logic đăng nhập và Access Control (Task 1)
        else:
            current_path = req.path
            is_authenticated = req.cookies.get('auth') == 'true'

            # --- TASK 1A: Xử lý POST /login ---
            if req.method == 'POST' and current_path == '/login':
                params = {}
                if req.body:
                    # Parse body kiểu application/x-www-form-urlencoded
                    params = dict(p.split('=', 1) for p in req.body.split('&') if '=' in p)
                
                username = params.get('username')
                password = params.get('password')

                if username == 'admin' and password == 'password':
                    # Đăng nhập thành công -> Set-Cookie và chuyển hướng đến /index.html
                    print("[Login Success] Setting auth=true cookie and redirecting.")
                    
                    # *** ĐIỂM SỬA QUAN TRỌNG: Gọi hàm set_cookie để thêm Set-Cookie header ***
                    resp.set_cookie('auth', 'true') 
                    
                    # Cập nhật đường dẫn để serve trang index
                    req.path = '/index.html' 
                    response = resp.build_response(req)
                else:
                    # Đăng nhập thất bại -> 401 Unauthorized
                    print("[Login Fail] Responding with 401 Unauthorized.")
                    response = resp.build_unauthorized()
                    
            # --- TASK 1B: Xử lý Access Control cho / và /index.html ---
            elif req.method == 'GET' and (current_path == '/' or current_path == '/index.html'):
                
                if is_authenticated:
                    # Nếu truy cập / -> chuyển hướng nội bộ sang /index.html
                    if current_path == '/':
                        req.path = '/index.html'
                    
                    print(f"[Access Granted] Serving {req.path}.")
                    response = resp.build_response(req)
                else:
                    # Nếu chưa xác thực -> 401 Unauthorized
                    print(f"[Access Denied] No auth cookie for {current_path}, responding with 401.")
                    response = resp.build_unauthorized()
                    
            # 4. Xử lý các request file tĩnh khác (CSS, JS, images, login.html)
            else:
                # Các file tĩnh còn lại không cần bảo vệ
                response = resp.build_response(req)
        
        # --- KẾT THÚC LOGIC SỬA ---
        
        # Gửi response và đóng kết nối
        if response:
            conn.sendall(response)
        
        conn.close()
    
    def get_request_cookies(self, req):
        """
        Extracts cookies from the request headers.
        """
        cookies = {}
        
        # *** ĐIỂM SỬA: Kiểm tra req.headers có tồn tại (không phải None) trước khi gọi .get() ***
        if req.headers is None:
            return cookies
            
        cookie_header = req.headers.get('Cookie') 
        if cookie_header:
            for pair in cookie_header.split(';'):
                try:
                    # Split only on the first '='
                    key, value = pair.strip().split('=', 1) 
                    cookies[key] = value
                except ValueError:
                    continue 
        return cookies
    
    @property
    def extract_cookies(self, req, resp):
        """
        Build cookies from the :class:`Request <Request>` headers.

        :param req:(Request) The :class:`Request <Request>` object.
        :param resp: (Response) The res:class:`Response <Response>` object.
        :rtype: cookies - A dictionary of cookie key-value pairs.
        """
        cookies = {}
        for header in headers:
            if header.startswith("Cookie:"):
                cookie_str = header.split(":", 1)[1].strip()
                for pair in cookie_str.split(";"):
                    key, value = pair.strip().split("=")
                    cookies[key] = value
        return cookies

    def build_response(self, req, resp):
        """Builds a :class:`Response <Response>` object 

        :param req: The :class:`Request <Request>` used to generate the response.
        :param resp: The  response object.
        :rtype: Response
        """
        response = Response()

        # Set encoding.
        response.encoding = get_encoding_from_headers(response.headers)
        response.raw = resp
        response.reason = response.raw.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Add new cookies from the server.
        response.cookies = extract_cookies(req)

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response

    # def get_connection(self, url, proxies=None):
        # """Returns a url connection for the given URL. 

        # :param url: The URL to connect to.
        # :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        # :rtype: int
        # """

        # proxy = select_proxy(url, proxies)

        # if proxy:
            # proxy = prepend_scheme_if_needed(proxy, "http")
            # proxy_url = parse_url(proxy)
            # if not proxy_url.host:
                # raise InvalidProxyURL(
                    # "Please check proxy URL. It is malformed "
                    # "and could be missing the host."
                # )
            # proxy_manager = self.proxy_manager_for(proxy)
            # conn = proxy_manager.connection_from_url(url)
        # else:
            # # Only scheme should be lower case
            # parsed = urlparse(url)
            # url = parsed.geturl()
            # conn = self.poolmanager.connection_from_url(url)

        # return conn


    def add_headers(self, request):
        """
        Add headers to the request.

        This method is intended to be overridden by subclasses to inject
        custom headers. It does nothing by default.

        
        :param request: :class:`Request <Request>` to add headers to.
        """
        pass

    def build_proxy_headers(self, proxy):
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. 

        :class:`HttpAdapter <HttpAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        :rtype: dict
        """
        headers = {}
        #
        # TODO: build your authentication here
        #       username, password =...
        # we provide dummy auth here
        #
        username, password = ("user1", "password")

        if username:
            headers["Proxy-Authorization"] = (username, password)

        return headers
    

    