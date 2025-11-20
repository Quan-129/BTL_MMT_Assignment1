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
daemon.request
~~~~~~~~~~~~~~~~~

This module provides a Request object to manage and persist 
request settings (cookies, auth, proxies).
"""
from .dictionary import CaseInsensitiveDict

class Request():
    """The fully mutable "class" `Request <Request>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a "class" `Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    Usage::

      >>> import deamon.request
      >>> req = request.Request()
      ## Incoming message obtain aka. incoming_msg
      >>> r = req.prepare(incoming_msg)
      >>> r
      <Request>
    """
    __attrs__ = [
        "method",
        "url",
        "headers",
        "body",
        "reason",
        "cookies",
        "body",
        "routes",
        "hook",
    ]

    def __init__(self):
        #: HTTP verb to send to the server.
        self.method = None
        #: HTTP URL to send the request to.
        self.url = None
        #: dictionary of HTTP headers.
        self.headers = None
        #: HTTP path
        self.path = None 
        # The cookies set used to create Cookie header
        self.cookies = None
        #: request body to send to the server.
        self.body = None
        #: Routes
        self.routes = {}
        #: Hook point for routed mapped-path
        self.hook = None

    def extract_request_line(self, request):
        try:
            lines = request.splitlines()
            first_line = lines[0]
            method, path, version = first_line.split()

            if path == '/':
                path = '/index.html'
        except Exception:
            return None, None

        return method, path, version
            
    def prepare_headers(self, request):
        """Prepares the given HTTP headers."""
        lines = request.split('\r\n')
        headers = {}
        for line in lines[1:]:
            if ': ' in line:
                # Sửa: split(': ', 1) để đảm bảo key không bị thừa khoảng trắng
                key, val = line.split(': ', 1)
                headers[key.lower()] = val.strip() # Sửa: Strip giá trị để làm sạch
        return headers

    def prepare(self, request, routes=None):
        """Prepares the entire request with the given parameters."""

        # Prepare the request line from the request header
        self.method, self.path, self.version = self.extract_request_line(request)
        print(("[Request] {} path {} version {}".format(self.method, self.path, self.version)))

        # Routing logic (giữ nguyên)
        if not routes == {}:
            self.routes = routes
            self.hook = routes.get((self.method, self.path))

        self.headers = self.prepare_headers(request)
        
        # --- BẮT ĐẦU PHẦN SỬA LỖI PARSING COOKIE TRONG REQUEST.PY ---
        self.cookies = {}
        cookie_string = self.headers.get('cookie', '')

        # Phân tích chuỗi cookie nếu nó tồn tại
        if cookie_string:
            # Tách các cặp key=value bằng dấu '; ' hoặc ';'
            pairs = cookie_string.split('; ')
            if len(pairs) == 1:
                 pairs = cookie_string.split(';')

            for pair in pairs:
                # Tách key và value, giới hạn 1 lần tách
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    
                    # LƯU Ý QUAN TRỌNG: Làm sạch key và value
                    key = key.strip()
                    value = value.strip()
                    
                    # Lưu key và value đã được làm sạch
                    self.cookies[key] = value
        
        print(f"[Request] Cookies found: {self.cookies}")
        # --- KẾT THÚC PHẦN SỬA ---

        return

    # ... (Các hàm khác giữ nguyên)
    def prepare_body(self, data, files, json=None):
        self.prepare_content_length(self.body)
        self.body = body
        return


    def prepare_content_length(self, body):
        self.headers["Content-Length"] = "0"
        return


    def prepare_auth(self, auth, url=""):
        return

    def prepare_cookies(self, cookies):
            self.headers["Cookie"] = cookies