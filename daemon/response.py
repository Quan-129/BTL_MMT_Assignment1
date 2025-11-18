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
daemon.response
~~~~~~~~~~~~~~~~~

This module provides a :class: `Response <Response>` object to manage and persist 
response settings (cookies, auth, proxies), and to construct HTTP responses
based on incoming requests. 

The current version supports MIME type detection, content loading and header formatting
"""
import datetime
import os
import mimetypes
from .dictionary import CaseInsensitiveDict

BASE_DIR = ""

class Response(): 
    """The :class:`Response <Response>` object, which contains a
    server's response to an HTTP request.

    Instances are generated from a :class:`Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    :class:`Response <Response>` object encapsulates headers, content, 
    status code, cookies, and metadata related to the request-response cycle.
    It is used to construct and serve HTTP responses in a custom web server.

    :attrs status_code (int): HTTP status code (e.g., 200, 404).
    :attrs headers (dict): dictionary of response headers.
    :attrs url (str): url of the response.
    :attrsencoding (str): encoding used for decoding response text.
    :attrs history (list): list of previous Response objects (for redirects).
    :attrs reason (str): textual reason for the status code (e.g., "OK", "Not Found").
    :attrs cookies (CaseInsensitiveDict): response cookies.
    :attrs elapsed (datetime.timedelta): time taken to complete the request.
    :attrs request (PreparedRequest): the original request object.

    Usage::

      >>> import Response
      >>> resp = Response()
      >>> resp.build_response(req)
      >>> resp
      <Response>
    """

    __attrs__ = [
        "_content",
        "_header",
        "status_code",
        "method",
        "headers",
        "url",
        "history",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
        "request",
        "body",
        "reason",
    ]


    def __init__(self, request=None):
        """
        Initializes a new :class:`Response <Response>` object.

        : params request : The originating request object.
        """

        self._content = False
        self._content_consumed = False
        self._next = None

        #: Integer Code of responded HTTP Status, e.g. 404 or 200.
        self.status_code = 200 # Khởi tạo mặc định
        
        #: Case-insensitive Dictionary of Response Headers.
        self.headers = CaseInsensitiveDict() # Sử dụng CaseInsensitiveDict cho headers

        #: URL location of Response.
        self.url = None

        #: Encoding to decode with when accessing response text.
        self.encoding = None

        #: A list of :class:`Response <Response>` objects from
        #: the history of the Request.
        self.history = []

        #: Textual reason of responded HTTP Status, e.g. "Not Found" or "OK".
        self.reason = "OK" # Khởi tạo mặc định

        #: A of Cookies the response headers.
        self.cookies = CaseInsensitiveDict()

        #: The amount of time elapsed between sending the request
        self.elapsed = datetime.timedelta(0)

        #: The :class:`PreparedRequest <PreparedRequest>` object to which this
        #: is a response.
        self.request = request

        # ✅ FIX: Thuộc tính để lưu trữ cookies cần Set-Cookie (Task 1A)
        self.cookies_to_set = CaseInsensitiveDict() 
        self._header_sent = False # Cờ kiểm tra header đã được gửi chưa

    # ✅ FIX: Phương thức set_cookie để HttpAdapter gọi (Task 1A)
    def set_cookie(self, key, value, path='/', max_age=None):
        """Lưu một cookie để đưa vào Set-Cookie header."""
        cookie_parts = [f"{key}={value}"]
        cookie_parts.append(f"Path={path}")
        
        if max_age is not None:
            # max_age phải là số nguyên (giây)
            cookie_parts.append(f"Max-Age={max_age}")

        # Lưu chuỗi cookie thô vào bộ lưu trữ
        self.cookies_to_set[key] = "; ".join(cookie_parts)

    def get_mime_type(self, path):
        """
        Determines the MIME type of a file based on its path.

        "params path (str): Path to the file.

        :rtype str: MIME type string (e.g., 'text/html', 'image/png').
        """

        try:
            mime_type, _ = mimetypes.guess_type(path)
        except Exception:
            return 'application/octet-stream'
        return mime_type or 'application/octet-stream'


    def prepare_content_type(self, mime_type='text/html'):
        """
        Prepares the Content-Type header and determines the base directory
        for serving the file based on its MIME type.

        :params mime_type (str): MIME type of the requested resource.

        :rtype str: Base directory path for locating the resource.

        :raises ValueError: If the MIME type is unsupported.
        """
        
        base_dir = ""

        # Processing mime_type based on main_type and sub_type
        main_type, sub_type = mime_type.split('/', 1)
        print(("[Response] processing MIME main_type={} sub_type={}".format(main_type,sub_type)))
        if main_type == 'text':
            self.headers['Content-Type']='text/{}'.format(sub_type)
            if sub_type == 'plain' or sub_type == 'css' or sub_type == 'javascript':
                base_dir = BASE_DIR+"static/"
            elif sub_type == 'html':
                base_dir = BASE_DIR+"www/"
            else:
                base_dir = BASE_DIR+"static/" 
        elif main_type == 'image':
            base_dir = BASE_DIR+"static/"
            self.headers['Content-Type']='image/{}'.format(sub_type)
        elif main_type == 'application':
            base_dir = BASE_DIR+"apps/"
            self.headers['Content-Type']='application/{}'.format(sub_type)
        #
        #   TODO: process other mime_type
        #
        else:
            raise ValueError("Invalid MEME type: main_type={} sub_type={}".format(main_type,sub_type))

        return base_dir

    def build_content(self, path, base_dir):
        """
        Loads the objects file from storage space.
        (Đã sửa để xử lý đường dẫn file tĩnh /static/ chính xác)
        """
        
        # 1. Xử lý đường dẫn file tĩnh (loại bỏ /static/ hoặc /www/)
        # Nếu base_dir là 'static/', ta cần loại bỏ /static/ khỏi path
        if path.startswith('/static/'):
            filepath = path[8:] # Bỏ đi 8 ký tự đầu tiên '/static/'
        elif path.startswith('/www/'): # Trường hợp path có tiền tố /www/
            filepath = path[5:] # Bỏ đi 5 ký tự đầu tiên '/www/'
        else:
            filepath = path.lstrip('/')

        full_path = os.path.join(base_dir, filepath)

        print(("[Response] serving the object at location {}".format(full_path)))
        
        try:
            # Mở file ở chế độ đọc nhị phân ('rb')
            with open(full_path, 'rb') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"[Error] File not found: {full_path}")
            # Trả về nội dung lỗi để build_response biết mà gọi build_notfound
            return 0, b"404 Not Found"
            
        return len(content), content

    def build_response_header(self, request):
        """
        Constructs the HTTP response headers based on the class:`Request <Request>
        and internal attributes.

        :params request (class:`Request <Request>`): incoming request object.

        :rtypes bytes: encoded HTTP response header.
        """
        # Nếu chưa set Content-Length, set nó bằng độ dài nội dung
        if 'Content-Length' not in self.headers and self._content is not False:
             self.headers['Content-Length'] = len(self._content)

        # Cập nhật trạng thái và lý do (dùng self.status_code và self.reason)
        status_line = f"HTTP/1.1 {self.status_code} {self.reason}\r\n"
        header_lines = []

        # Thêm các header chuẩn (giữ nguyên các header động/tĩnh cần thiết)
        # Khởi tạo headers mặc định nếu chưa có
        if not self.headers.get('Date'):
            self.headers['Date'] = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        if not self.headers.get('Connection'):
             self.headers['Connection'] = 'close'

        # Thêm các header từ self.headers
        for key, value in self.headers.items():
            header_lines.append(f"{key}: {value}")

        # ✅ FIX: Thêm Set-Cookie headers từ cookies_to_set (Task 1A)
        for cookie_key, cookie_string in self.cookies_to_set.items():
            header_lines.append(f"Set-Cookie: {cookie_string}")
        
        # Thêm Connection: close nếu chưa có (để đảm bảo đóng kết nối)

        return (status_line + "\r\n".join(header_lines) + "\r\n\r\n").encode('utf-8')


    def build_notfound(self):
        """
        Constructs a standard 404 Not Found HTTP response.

        :rtype bytes: Encoded 404 response.
        """
        content = b"<h1>404 Not Found</h1>"
        
        return (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(content)}\r\n"
            "Connection: close\r\n"
            "\r\n"
            ).encode('utf-8') + content
    
    # ✅ FIX: Định nghĩa phương thức build_unauthorized (401) (Task 1B)
    def build_unauthorized(self):
        """
        Constructs a standard 401 Unauthorized HTTP response.

        :rtype bytes: Encoded 401 response.
        """
        self.status_code = 401
        self.reason = "Unauthorized"
        # Nội dung trang 401
        content = b"<h1>401 Unauthorized</h1><p>Access denied. Please log in.</p>" 
        
        return (
            "HTTP/1.1 401 Unauthorized\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(content)}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode("utf-8") + content


    def build_response(self, request):
        """
        Builds a full HTTP response including headers and content based on the request.

        :params request (class:`Request <Request>`): incoming request object.

        :rtype bytes: complete HTTP response using prepared headers and content.
        """

        path = request.path

        mime_type = self.get_mime_type(path)
        print(("[Response] {} path {} mime_type {}".format(request.method, request.path, mime_type)))

        # Nếu path bị None hoặc rỗng → trả về 404 (logic cũ)
        if not path:
             return self.build_notfound()

        # 1. Chuẩn bị Content-Type và Base Dir
        base_dir = ""
        try:
            base_dir = self.prepare_content_type(mime_type = mime_type)
        except ValueError:
            return self.build_notfound() 

        # 2. Load Content từ file
        c_len, self._content = self.build_content(path, base_dir)
        
        # 3. Nếu build_content trả về nội dung lỗi (do FileNotFoundError)
        if self._content == b"404 Not Found":
            return self.build_notfound()
            
        # 4. Xây dựng Header và ghép nối
        self._header = self.build_response_header(request)

        return self._header + self._content