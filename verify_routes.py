import asyncio
from database import SessionLocal, init_db
from seed_data import seed
from models import User
from app import app

async def test_full_application_flow():
    print("--- Starting Comprehensive Application Flow Verification ---")
    init_db()
    seed()
    
    saved_session_cookie = None

    async def make_asgi_request(path: str, method: str = "GET", headers: dict = None, session_cookie: str = None):
        headers_list = []
        if headers:
            for k, v in headers.items():
                headers_list.append((k.lower().encode("latin1"), v.encode("latin1")))
        if session_cookie:
            headers_list.append((b"cookie", f"cherry_session={session_cookie}".encode("latin1")))

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "path": path,
            "raw_path": path.encode("latin1"),
            "query_string": b"",
            "headers": headers_list,
            "client": ("127.0.0.1", 12345),
            "server": ("127.0.0.1", 8000),
            "scheme": "http",
        }

        response_status = None
        response_headers = []
        response_body = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            nonlocal response_status, response_headers, response_body
            if message["type"] == "http.response.start":
                response_status = message["status"]
                response_headers = message["headers"]
            elif message["type"] == "http.response.body":
                response_body.append(message.get("body", b""))

        await app(scope, receive, send)
        full_body = b"".join(response_body).decode("utf-8", errors="replace")
        
        # Extract Set-Cookie if any
        resp_headers_dict = dict((k.decode("latin1"), v.decode("latin1")) for k, v in response_headers)
        cookie_header = resp_headers_dict.get("set-cookie")
        extracted_cookie = None
        if cookie_header and "cherry_session=" in cookie_header:
            extracted_cookie = cookie_header.split("cherry_session=")[1].split(";")[0]

        return response_status, resp_headers_dict, full_body, extracted_cookie

    # 1. Login Page
    status, _, body, anon_cookie = await make_asgi_request("/login")
    assert status == 200, f"Failed GET /login: {status}"
    print("[PASS] GET /login: 200 OK")

    import re
    csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', body)
    csrf_token = csrf_match.group(1) if csrf_match else ""

    # 2. POST /login with Owner Credentials
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    payload = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="csrf_token"\r\n\r\n'
        f"{csrf_token}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="username"\r\n\r\n'
        f"owner\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="password"\r\n\r\n'
        f"admin123\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    async def make_post_request(path: str, body_bytes: bytes, content_type: str, session_cookie: str = None):
        headers_list = [
            (b"content-type", content_type.encode("latin1")),
            (b"content-length", str(len(body_bytes)).encode("latin1"))
        ]
        if session_cookie:
            headers_list.append((b"cookie", f"cherry_session={session_cookie}".encode("latin1")))
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "path": path,
            "raw_path": path.encode("latin1"),
            "query_string": b"",
            "headers": headers_list,
            "client": ("127.0.0.1", 12345),
            "server": ("127.0.0.1", 8000),
            "scheme": "http",
        }
        response_status = None
        response_headers = []
        response_body = []
        body_sent = False

        async def receive():
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            nonlocal response_status, response_headers, response_body
            if message["type"] == "http.response.start":
                response_status = message["status"]
                response_headers = message["headers"]
            elif message["type"] == "http.response.body":
                response_body.append(message.get("body", b""))

        await app(scope, receive, send)
        resp_headers_dict = dict((k.decode("latin1"), v.decode("latin1")) for k, v in response_headers)
        cookie_header = resp_headers_dict.get("set-cookie")
        cookie_val = None
        if cookie_header and "cherry_session=" in cookie_header:
            cookie_val = cookie_header.split("cherry_session=")[1].split(";")[0]
        return response_status, resp_headers_dict, b"".join(response_body).decode("utf-8", errors="replace"), cookie_val

    status, resp_headers, resp_body, cookie = await make_post_request("/login", payload, f"multipart/form-data; boundary={boundary}", anon_cookie)
    assert status == 302, f"Expected 302 redirect after login, got {status}: {resp_body}"
    assert cookie is not None, "Expected session cookie from login"
    print(f"[PASS] POST /login: 302 Redirect (Session created)")

    # 3. Test Protected Routes with Authenticated Session
    test_routes = [
        ("/dashboard", "Dashboard / Analytics"),
        ("/orders/pos", "Point of Sale (POS)"),
        ("/orders", "Order History"),
        ("/custom-cakes", "Custom Cake Bookings"),
        ("/custom-cakes/create", "New Custom Cake Form"),
        ("/products", "Product Catalog"),
        ("/categories", "Categories"),
        ("/inventory", "Inventory & Stock"),
        ("/reports", "Reports & Analytics"),
        ("/settings", "Shop Settings"),
        ("/staff", "Staff Management"),
        ("/audit-logs", "Audit Logs"),
        ("/profile", "User Profile"),
        ("/payments/pending", "Pending Payments")
    ]

    for path, desc in test_routes:
        status, _, body, _ = await make_asgi_request(path, session_cookie=cookie)
        assert status == 200, f"Route {path} failed with status {status}. Body: {body[:300]}"
        print(f"[PASS] {desc} ({path}): 200 OK")

    print("\n=======================================================")
    print("ALL ROUTES, VIEWS & TEMPLATES RENDERED FLAWLESSLY!")
    print("=======================================================")

if __name__ == "__main__":
    asyncio.run(test_full_application_flow())
