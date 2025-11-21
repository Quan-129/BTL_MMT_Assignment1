// static/js/chat_client.js (Phiên bản Sửa lỗi Khởi tạo và Bổ sung Notification)

const WEAPROUS_BASE_URL = window.location.origin;
const POLLING_INTERVAL = 2000;
const TRACKER_UNREACHABLE_MSG = "Tracker is unreachable. Please ensure start_tracker.py is running.";

// Keys for Local Storage
const PEER_ID_KEY = 'chat_peer_id';
const USERNAME_KEY = 'chat_username';

let CURRENT_TARGET_ID = null; 
let CURRENT_TARGET_TYPE = null; // 'peer' hoặc 'channel'
let CURRENT_TARGET_INTERNAL_ID = null; // actual internal id used for sending (username@ip:p2p_port)
let MY_PEER_ID = null;
let MY_USERNAME = null;

// Map để lưu trữ tra cứu (IP:Port -> Username)
const PEER_USERNAME_MAP = {}; 

// --- HÀM TRỢ GIÚP CHO NOTIFICATION ---

function displayNotification(message, type = 'info') {
    const window = document.getElementById('notification-window');
    if (!window) return;
    
    const time = new Date().toLocaleTimeString();
    const p = document.createElement('p');
    p.style.margin = '2px 0';
    p.style.padding = '2px 5px';
    
    // Đặt màu nền cho thông báo
    let bgColor = '#fff3cd'; // default info (yellowish)
    if (type === 'success') bgColor = '#d4edda'; // green
    if (type === 'error') bgColor = '#f8d7da'; // red
    if (type === 'sent') bgColor = '#e6f7ff'; // blue/cyan for sent confirmation
    
    p.style.backgroundColor = bgColor;
    p.textContent = `[${time}] ${message}`;
    
    window.appendChild(p);
    // Cuộn xuống dưới cùng
    window.scrollTop = window.scrollHeight;
}


// --- LOGIC KHỞI TẠO VÀ ĐĂNG KÝ (Gắn vào nút Register) ---

function initAppLogic() {
    // 1. Tải trạng thái từ Local Storage
    MY_PEER_ID = localStorage.getItem(PEER_ID_KEY);
    MY_USERNAME = localStorage.getItem(USERNAME_KEY);
    
    // 2. Nếu ở trang Chat chính (/index.html) VÀ có Peer ID, bắt đầu chat
    if (window.location.pathname.endsWith('/index.html') && MY_PEER_ID) {
        
        // --- BẮT ĐẦU KHỐI TRY/CATCH CỨNG ---
        try { 
            setTarget(null); // Không chọn target nào ban đầu
            // Hiển thị username (nếu có)
            const titleElement = document.getElementById('current-chat-title');
            if (titleElement) titleElement.textContent = `Welcome, ${MY_USERNAME}!`;
            
            // Tải cả Peers VÀ Channels
            loadPeersAndChannels(); 
            startPollingForNewMessages();
            
            // Gắn sự kiện cho nút Refresh
            const refreshButton = document.getElementById('refresh-button');
            if (refreshButton) refreshButton.onclick = loadPeersAndChannels;

            // Gắn sự kiện cho nút CREATE CHANNEL
            const createButton = document.getElementById('create-channel-button');
            if (createButton) createButton.onclick = createChannel;
            
        } catch (e) {
            console.error("Fatal Error during initAppLogic:", e);
            displaySystemMessage("Application initialization failed. Check Console (F12).");
        }
        // --- KẾT THÚC KHỐI TRY/CATCH CỨNG ---

    } else if (window.location.pathname.endsWith('/index.html')) {
        // Nếu ở trang Chat nhưng không có ID, buộc quay lại đăng ký
        alert("Session expired. Please register your Peer again.");
        window.location.href = `${WEAPROUS_BASE_URL}/register.html`;
    }
    
    // Gắn sự kiện click cho nút Register (chỉ tồn tại trên /register.html)
    const registerButton = document.getElementById('register-button');
    if (registerButton) {
        registerButton.onclick = registerAndInit;
    }
}
// ... (các hàm registerAndInit, registerPeer, setTarget, loadPeersAndChannels, createChannel, joinChannel giữ nguyên)

function registerAndInit() {
    const usernameInput = document.getElementById('peer-username-input');
    const username = usernameInput.value.trim();
    const statusElement = document.getElementById('registration-status');

    if (!username) {
        alert("Error: Username is required.");
        statusElement.textContent = "Error: Username is required.";
        statusElement.style.color = 'red';
        return;
    }
    
    // 1. Tự động lấy Port hiện tại từ URL
    const urlParts = window.location.href.split(':');
    const http_port = parseInt(urlParts[urlParts.length - 1].split('/')[0]);
    
    // Vô hiệu hóa input trong khi chờ đăng ký
    usernameInput.disabled = true;
    document.getElementById('register-button').disabled = true;
    statusElement.textContent = "Attempting registration...";
    statusElement.style.color = 'orange';

    // 2. Gọi hàm đăng ký
    registerPeer(username, '127.0.0.1', http_port, statusElement);
}

async function registerPeer(username, ip, http_port, statusElement) {
    const url = `${WEAPROUS_BASE_URL}/register-peer`;
    
    try {
        const response = await fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username })
        });
        const data = await response.json();
        
        if (response.ok) {
            MY_PEER_ID = data.peer_id;
            MY_USERNAME = username;
            
            // LƯU TRỮ TRẠNG THÁI VÀO LOCAL STORAGE
            localStorage.setItem(PEER_ID_KEY, MY_PEER_ID);
            localStorage.setItem(USERNAME_KEY, MY_USERNAME);
            
            statusElement.textContent = `Registered successfully! Redirecting to Chat...`;
            statusElement.style.color = 'green';
            
            // CHUYỂN HƯỚNG TRÌNH DUYỆT SANG TRANG CHAT CHÍNH
            // Ensure the browser has an 'auth' cookie so protected GET /index.html won't return 401.
            // Some browsers (and fetch flows) may not persist Set-Cookie in all cases, so set it client-side
            // as a fallback. This is safe for this local dev app (not for production with HttpOnly cookies).
            try {
                document.cookie = 'auth=true; Path=/';
            } catch (e) {
                console.warn('Could not set cookie via document.cookie', e);
            }

            await new Promise(resolve => setTimeout(resolve, 300));
            window.location.href = `${WEAPROUS_BASE_URL}/index.html`;
            
        } else {
            // Lỗi từ backend (ví dụ: 503 Tracker Down)
            statusElement.textContent = `Error: Failed to register with Tracker.`;
            statusElement.style.color = 'red';
            alert(`Registration failed. Server error: ${data.message} (Is Tracker running?)`);
        }
    } catch (e) {
        // Lỗi kết nối mạng/Fetch API
        statusElement.textContent = "Error: Could not connect to Peer Server/Tracker.";
        statusElement.style.color = 'red';
        alert("Fatal Error: Could not connect to Backend.");
    } finally {
        // Nếu thất bại, cho phép thử lại
        if (!MY_PEER_ID) {
            document.getElementById('peer-username-input').disabled = false;
            document.getElementById('register-button').disabled = false;
        }
    }
}

function setTarget(targetId, targetType, internalId=null) {
    // Nếu chọn cùng một mục, không làm gì
    if (CURRENT_TARGET_ID === targetId && CURRENT_TARGET_TYPE === targetType) return;

    CURRENT_TARGET_ID = targetId;
    CURRENT_TARGET_TYPE = targetType;
    CURRENT_TARGET_INTERNAL_ID = internalId; // may be null for channels/broadcast
    const titleElement = document.getElementById('current-chat-title');
    const messageWindow = document.getElementById('message-window'); 

    // Làm sạch nội dung cũ
    messageWindow.innerHTML = ''; 

    if (targetId === null) {
        titleElement.textContent = 'Please select a Peer or Channel';
    } else if (targetType === 'broadcast') {
        titleElement.textContent = 'General Chat (Broadcast)';
    } else if (targetType === 'channel') {
        titleElement.textContent = `Channel: #${targetId}`;
    } else { // peer
        titleElement.textContent = `Direct Chat with ${targetId}`;
    }
}


async function loadPeersAndChannels() {
    const peerListElement = document.getElementById('peer-list');
    const channelListElement = document.getElementById('channel-list');

    // Khởi tạo/Xóa sạch cả hai danh sách trước khi fetch
    peerListElement.innerHTML = `<li onclick="setTarget('BROADCAST', 'broadcast')"><strong># BROADCAST</strong></li>`; 
    channelListElement.innerHTML = ``; 

    try {
        let peerFetchSuccess = false;
        
        // 1. TẢI DANH SÁCH PEER (Direct Peer)
        const peerResponse = await fetch(`${WEAPROUS_BASE_URL}/get-list`);
        const peerData = await peerResponse.json();
        
        if (peerResponse.ok) {
            peerFetchSuccess = true;
            peerData.peers.forEach(peer => {
                // Skip showing ourselves in the peer list. Compare by username
                // because MY_PEER_ID may use a different host representation (0.0.0.0 vs LAN IP).
                if (peer.username !== MY_USERNAME) {
                        // Display the peer using the HTTP/WEB port (p2p_port - 1)
                        const peerP2pPort = parseInt(peer.port);
                        const peerHttpPort = peerP2pPort - 1;
                        const peerIdActual = `${peer.username}@${peer.ip}:${peerP2pPort}`; // internal id used for sending
                        const peerIdDisplay = `${peer.username}@${peer.ip}:${peerHttpPort}`; // shown in UI per request

                        // Map incoming P2P sender address (ip:p2p_port) to username for display
                        const incomingIpPort = `${peer.ip}:${peerP2pPort}`;
                        PEER_USERNAME_MAP[incomingIpPort] = peer.username;

                        const li = document.createElement('li');
                        li.textContent = peerIdDisplay;
                        // Khi click vào peer, pass display id for UI and actual id for sending
                        li.onclick = () => setTarget(peerIdDisplay, 'peer', peerIdActual);
                        peerListElement.appendChild(li);
                }
            });
        } else if (peerResponse.status === 503) {
            displaySystemMessage(`Peer List Error: ${peerData.message}`);
        }
        
        // 2. TẢI DANH SÁCH KÊNH (Channel)
        const channelResponse = await fetch(`${WEAPROUS_BASE_URL}/get-channels`);
        const channelData = await channelResponse.json();

        if (channelResponse.ok) {
            for (const name in channelData.channels) {
                const channel = channelData.channels[name];
                const isMember = channel.members.includes(MY_USERNAME);
                
                const li = document.createElement('li');
                li.classList.add('channel-item');
                li.innerHTML = `
                    <span class="channel-name" onclick="setTarget('${name}', 'channel')"># ${name}</span>
                    <span class="member-count">(${channel.members.length} thành viên)</span>
                `;
                
                // Thêm nút JOIN/CHAT
                if (!isMember) {
                    const joinBtn = document.createElement('button');
                    joinBtn.textContent = 'JOIN';
                    joinBtn.style.cssText = 'margin-left: 5px; float: right;';
                    joinBtn.onclick = (e) => {
                        e.stopPropagation(); // Ngăn sự kiện click lan truyền lên li
                        joinChannel(name);
                    };
                    li.appendChild(joinBtn);
                } else {
                    const chatBtn = document.createElement('button');
                    chatBtn.textContent = 'CHAT';
                    chatBtn.style.cssText = 'margin-left: 5px; float: right;';
                    chatBtn.onclick = (e) => {
                        e.stopPropagation();
                        setTarget(name, 'channel');
                    };
                    li.appendChild(chatBtn);
                }
                
                channelListElement.appendChild(li);
            }
        } else if (channelResponse.status === 503) {
             displaySystemMessage(`Channel List Error: ${channelData.message}`);
        }

    } catch (e) {
        console.error("Error loading peers/channels (Fatal):", e);
        // Nếu lỗi kết nối, hiển thị thông báo hệ thống lớn.
        displaySystemMessage(TRACKER_UNREACHABLE_MSG);
    } finally {
        // BỔ SUNG: Thông báo chung sau khi fetch xong
        displayNotification("Peer and Channel lists refreshed.", 'info');
    }
}

async function createChannel() {
    const channelNameInput = document.getElementById('channel-name-input');
    const channelName = channelNameInput.value.trim();

    if (!channelName || !MY_USERNAME) {
        alert("Tên kênh và Username là bắt buộc.");
        return;
    }
    
    // Đặt nút CREATE vào trạng thái vô hiệu hóa tạm thời
    const createButton = document.getElementById('create-channel-button');
    if (createButton) createButton.disabled = true;

    try {
        const response = await fetch(`${WEAPROUS_BASE_URL}/create-channel`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ channel_name: channelName, owner: MY_USERNAME })
        });

        const data = await response.json();

        if (response.ok) {
            alert(`Kênh '${channelName}' đã được tạo thành công!`);
            channelNameInput.value = ''; // Xóa input
            loadPeersAndChannels(); // Cập nhật danh sách
            
            // LOGIC NOTIFICATION: Thông báo thành công cho người tạo
            displayNotification(`Channel #${channelName} created successfully!`, 'success'); 
            
        } else {
            // Xử lý lỗi API (ví dụ: Tên kênh đã tồn tại, 409 Conflict)
            alert(`Tạo kênh thất bại: ${data.message}`);
            displayNotification(`Failed to create channel: ${data.message}`, 'error'); 
        }
    } catch (e) {
        // Xử lý lỗi kết nối mạng/Web App Down (503)
        alert("Lỗi kết nối khi tạo kênh. Vui lòng kiểm tra Server.");
        displayNotification("Connection error when creating channel.", 'error'); 
    } finally {
        // Phục hồi nút CREATE
        if (createButton) createButton.disabled = false;
    }
}

async function joinChannel(channelName) {
    if (!MY_USERNAME) {
        alert("Vui lòng đăng ký Peer trước.");
        return;
    }

    try {
        const response = await fetch(`${WEAPROUS_BASE_URL}/join-channel`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ channel_name: channelName, username: MY_USERNAME })
        });

        const data = await response.json();

        if (response.ok) {
            alert(`Bạn đã tham gia kênh #${channelName}!`);
            
            // BỔ SUNG: Thông báo thành công cho người vừa tham gia
            displayNotification(`Joined channel #${channelName}.`, 'success'); 
            
            loadPeersAndChannels(); // Cập nhật UI để hiển thị nút CHAT
            setTarget(channelName, 'channel'); // Tự động chuyển sang kênh vừa join
        } else {
            alert(`Tham gia kênh thất bại: ${data.message}`);
            // BỔ SUNG: Thông báo thất bại
            displayNotification(`Failed to join channel: ${data.message}`, 'error');
        }
    } catch (e) {
        alert("Lỗi kết nối khi tham gia kênh.");
        // BỔ SUNG: Thông báo lỗi kết nối
        displayNotification("Connection error when joining channel.", 'error');
    }
}

// --- GỬI VÀ NHẬN TIN NHẮN (Pha P2P) ---

async function sendMessage() {
    const inputElement = document.getElementById('message-input');
    const message = inputElement.value.trim();
    
    // KIỂM TRA ĐIỀU KIỆN GỬI
    if (!MY_PEER_ID || !MY_USERNAME) {
        alert("Please register your Peer before sending a message.");
        return;
    }
    
    if (!CURRENT_TARGET_ID || !CURRENT_TARGET_TYPE) {
        alert("Please select a Peer or Channel before sending a message.");
        return;
    }
    
    if (!message) return;

    let url = '';
    let body = { 
        message: message,
        sender_username: MY_USERNAME // Gửi kèm username để phân biệt
    };
    
    let targetName;

    if (CURRENT_TARGET_TYPE === 'broadcast') {
        url = `${WEAPROUS_BASE_URL}/broadcast-peer`;
        body.message = `📢 Broadcast: [${MY_USERNAME}] ${message}`; // Thêm tiền tố
        targetName = "Broadcast";

    } else if (CURRENT_TARGET_TYPE === 'channel') {
        // Gửi qua WebApp API /send-peer với target_type='channel'
        url = `${WEAPROUS_BASE_URL}/send-peer`;
        body.target_id = CURRENT_TARGET_ID; // Tên kênh
        body.target_type = 'channel'; // CỜ CHẾ ĐỘ KÊNH
        targetName = `#${CURRENT_TARGET_ID}`; // Tên kênh cho thông báo
        
    } else { // peer (Direct Peer)
        // Gửi qua WebApp API /send-peer với target_type='peer'
        url = `${WEAPROUS_BASE_URL}/send-peer`;
        // Use the internal actual peer id (with p2p port) when sending. If not set,
        // fall back to the visible CURRENT_TARGET_ID (best-effort).
        body.target_id = CURRENT_TARGET_INTERNAL_ID || CURRENT_TARGET_ID; // Peer ID (username@ip:p2p_port)
        body.target_type = 'peer'; // CỜ CHẾ ĐỘ PEER
        targetName = (CURRENT_TARGET_ID || body.target_id).split('@')[0]; // Lấy username đích
    }

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await response.json(); // Phải đọc data để lấy sent/failed count

        if (response.ok) {
            displayMessage(MY_USERNAME, message, 'sent', CURRENT_TARGET_TYPE);
            inputElement.value = '';

            // LOGIC THÔNG BÁO GỬI THÀNH CÔNG (BÊN GỬI)
            let notificationMessage;
            if (CURRENT_TARGET_TYPE === 'channel') {
                 notificationMessage = `Sent to ${targetName} (Success: ${data.sent_to}, Failed: ${data.failed}).`;
            } else if (CURRENT_TARGET_TYPE === 'broadcast') {
                 notificationMessage = "Broadcast message sent successfully.";
            } else { // Direct Peer
                 notificationMessage = `Sent message to ${targetName}.`;
            }
            displayNotification(notificationMessage, 'sent');

        } else {
            const error = data;
            alert(`Sending failed: ${error.message}`);
             displayNotification(`Failed to send message: ${error.message}`, 'error');
        }
    } catch (e) {
        alert("Connection error when sending message.");
        displayNotification("Connection error when sending message.", 'error');
    }
}


async function startPollingForNewMessages() {
    // API: /check-new-messages
    setInterval(async () => {
        try {
            const response = await fetch(`${WEAPROUS_BASE_URL}/check-new-messages`);
            if (response.ok) {
                const data = await response.json();
                
                data.messages.forEach(msg => {
                    const raw = msg.message || '';

                    // Tìm tất cả các nhóm trong ngoặc vuông, ví dụ: "[192.168:8000] [alice] Hello"
                    const bracketMatches = Array.from(raw.matchAll(/\[([^\]]+)\]/g)).map(m => m[1]);

                    // Regex để xác định ip:port
                    const ipPortRegex = /^\d+\.\d+\.\d+\.\d+:\d+$/;

                    let sender = null;
                    let content = raw;

                    // Prefer the network-resolved username (based on msg.sender_addr) when available
                    const networkName = PEER_USERNAME_MAP[msg.sender_addr];

                    if (networkName) {
                        sender = networkName;
                        // Remove any occurrence of [networkName] from the raw content, if present
                        content = raw.replace(new RegExp('\\[' + escapeRegExp(networkName) + '\\]', 'g'), '').trim();
                        // Also remove any leftover leading bracketed token (e.g., an ip:port) at the start
                        content = content.replace(/^\s*\[[^\]]+\]\s*/, '');
                    } else if (bracketMatches.length === 0) {
                        // No brackets and no network mapping -> fallback to sender_addr
                        sender = msg.sender_addr;
                        content = raw;
                    } else {
                        // No network mapping; pick a non-ip bracket if available, else first bracket
                        let chosen = bracketMatches.find(b => !ipPortRegex.test(b));
                        if (!chosen) chosen = bracketMatches[0];

                        if (!ipPortRegex.test(chosen)) {
                            sender = chosen;
                            // Remove only that chosen bracket occurrence
                            content = raw.replace(new RegExp('\\[' + escapeRegExp(chosen) + '\\]', ''), '').trim();
                            content = content.replace(/^\s*\[[^\]]+\]\s*/, '');
                        } else {
                            // chosen is ip:port -> use msg.sender_addr mapping fallback
                            sender = msg.sender_addr;
                            const afterFirst = raw.replace(/^[^\]]*\]\s*/, '');
                            content = afterFirst.trim();
                        }
                    }

                    let type = 'received';
                    displayMessage(sender, content, type, 'peer');

                    // Thông báo sử dụng tên (nếu có mapping) hoặc sender
                    let displaySender = typeof sender === 'string' ? (PEER_USERNAME_MAP[msg.sender_addr] || sender) : sender;
                    displayNotification(`New message received from ${displaySender}.`, 'success');
                });
            }
        } catch (error) {
            // Suppress error to avoid constant popups
        }
    }, POLLING_INTERVAL); 
}

// ... (hàm displayMessage và displaySystemMessage giữ nguyên)

function displayMessage(sender, content, type, targetType) {
    const window = document.getElementById('message-window');
    
    if (!window) return; 

    let displaySender = sender;

    // 1. Logic Tra cứu
    if (PEER_USERNAME_MAP[sender]) {
        displaySender = PEER_USERNAME_MAP[sender]; 
    } else if (type === 'sent') {
        displaySender = MY_USERNAME;
    }
    
    // 2. Logic Hiển thị
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message-bubble', type);

    // Xử lý Broadcast (giữ nguyên logic hiện có)
    let isBroadcast = false;
    if (content.startsWith('📢 Broadcast:')) {
        isBroadcast = true;
        displaySender = content.substring(content.indexOf('[')+1, content.indexOf(']'));
        content = content.substring(content.indexOf(']')+1).trim();
    }

    // Bỏ [username] đứng đầu nội dung (ví dụ: "[alice] Hello" -> "Hello")
    // Điều này loại bỏ nhãn người nhận phía trước nội dung kênh/peer khi hiển thị.
    content = content.replace(/^\s*\[[^\]]+\]\s*/, '');

    // Nếu là Broadcast, thêm icon trước tên người gửi để hiển thị biểu tượng loa
    const senderLabel = isBroadcast ? `📢 ${displaySender}` : displaySender;
    msgDiv.innerHTML = `<strong>${senderLabel}:</strong> ${content}`;
    
    window.appendChild(msgDiv);
    window.scrollTop = window.scrollHeight; 
}

// Escape string for RegExp construction
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function displaySystemMessage(message) {
    const window = document.getElementById('message-window');
    if (!window) return; 
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('system-message');
    msgDiv.textContent = `[SYSTEM] ${message}`;
    window.appendChild(msgDiv);
    window.scrollTop = window.scrollHeight;
}


document.addEventListener('DOMContentLoaded', initAppLogic);