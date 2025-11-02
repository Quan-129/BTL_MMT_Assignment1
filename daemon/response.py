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
    :attrsencoding (str): encoding used for decoding response content.
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
        self.headers = {}

        #: URL location of Response.
        self.url = None

        #: Encoding to decode with when accessing response text.
        self.encoding = None

        #: A list of :class:`Response <Response>` objects from
        #: the history of the Request.
        self.history = []

        #: Textual reason of responded HTTP Status, e.g. "Not Found" or "OK".
        self.reason = None

        #: A of Cookies the response headers.
        self.cookies = CaseInsensitiveDict()

        #: The amount of time elapsed between sending the request
        self.elapsed = datetime.timedelta(0)

        #: The :class:`PreparedRequest <PreparedRequest>` object to which this
        #: is a response.
        self.request = None

        # ✅ FIX: Đổi tên biến để khớp với httpadapter.py
        self.cookie_flag = False 
        self._header_sent = False # Cờ kiểm tra header đã được gửi chưa


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
            if sub_type == 'plain' or sub_type == 'css':
                base_dir = BASE_DIR+"static/"
            elif sub_type == 'html':
                base_dir = BASE_DIR+"www/"
            else:
                # ✅ FIX: Xóa hàm handle_text_other không tồn tại
                base_dir = BASE_DIR+"static/" 
        elif main_type == 'image':
            base_dir = BASE_DIR+"static/"
            self.headers['Content-Type']='image/{}'.format(sub_type)
        elif main_type == 'application':
            base_dir = BASE_DIR+"apps/"
            self.headers['Content-Type']='application/{}'.format(sub_type)
        #
        #  TODO: process other mime_type
        #
        else:
            raise ValueError("Invalid MEME type: main_type={} sub_type={}".format(main_type,sub_type))

        return base_dir


    def build_content(self, path, base_dir):
        """
        Loads the objects file from storage space.

        :params path (str): relative path to the file.
        :params base_dir (str): base directory where the file is located.

        :rtype tuple: (int, bytes) representing content length and content data.
        """

        filepath = os.path.join(base_dir, path.lstrip('/'))

        print(("[Response] serving the object at location {}".format(filepath)))
        
        try:
            # Mở file ở chế độ đọc nhị phân ('rb') để xử lý được cả text và ảnh
            with open(filepath, 'rb') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"[Error] File not found: {filepath}")
            # Trả về nội dung 404 để build_response biết mà gọi build_notfound
            content = b"404 Not Found" 
            return 0, content # Trả về 0 và nội dung lỗi
            
        return len(content), content


    def build_response_header(self, request):
        """
        Constructs the HTTP response headers based on the class:`Request <Request>
        and internal attributes.

        :params request (class:`Request <Request>`): incoming request object.

        :rtypes bytes: encoded HTTP response header.
        """
        reqhdr = request.headers
        
        # Build dynamic headers (LƯU Ý: Đã dùng len(self._content) ở đây)
        headers = {
            "Accept": reqhdr.get("Accept", "application/json"),
            "Accept-Language": reqhdr.get("Accept-Language", "en-US,en;q=0.9"),
            "Authorization": reqhdr.get("Authorization", "Basic <credentials>"),
            "Cache-Control": "no-cache",
            "Content-Type": self.headers.get('Content-Type', 'text/html'),
            "Content-Length": len(self._content), # FIX: Phải là số, nhưng sẽ được convert ở dưới
            "Date": datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "Max-Forward": "10",
            "Pragma": "no-cache",
            "Proxy-Authorization": "Basic dXNlcjpwYXNz",
            "Warning": "199 Miscellaneous warning",
            "User-Agent": reqhdr.get("User-Agent", "Chrome/123.0.0.0"),
        }

        # --- Logic Set-Cookie (Task 1A) ---
        if self.cookie_flag:
            # FIX: Thêm Set-Cookie vào headers.
            headers['Set-Cookie'] = 'auth=true; Path=/'
            
        # Dòng trạng thái HTTP (200 OK)
        status_line = "HTTP/1.1 200 OK\r\n"
        
        # Chuyển đổi dictionary headers thành chuỗi định dạng HTTP
        # FIX: Chuyển tất cả value thành str trước khi join
        header_lines = [f"{key}: {value}" for key, value in headers.items()]
        fmt_header = status_line + "\r\n".join(header_lines) + "\r\n\r\n"
        
        return fmt_header.encode('utf-8')


    def build_notfound(self):
        """
        Constructs a standard 404 Not Found HTTP response.

        :rtype bytes: Encoded 404 response.
        """

        return (
                "HTTP/1.1 404 Not Found\r\n"
                "Accept-Ranges: bytes\r\n"
                "Content-Type: text/html\r\n"
                "Content-Length: 13\r\n"
                "Cache-Control: max-age=86000\r\n"
                "Connection: close\r\n"
                "\r\n"
                "404 Not Found"
            ).encode('utf-8')
    
    def build_unauthorized(self):
        """
        Constructs a standard 401 Unauthorized HTTP response.

        :rtype bytes: Encoded 401 response.
        """
        # Nội dung phản hồi 401 (16 bytes)
        content = b"401 Unauthorized" 
        
        return (
            "HTTP/1.1 401 Unauthorized\r\n"
            "Content-Type: text/html\r\n"
            # ✅ FIX: Content-Length phải là 16 bytes
            "Content-Length: 16\r\n" 
            "Connection: close\r\n"
            "\r\n"
            "401 Unauthorized"
        ).encode("utf-8")


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