from flask import Flask, request, jsonify
import subprocess
import re, os

app = Flask(__name__)

# --- Configuration ---
AUTH_TOKEN = "mysecrettoken123"  # Change this to your secret token
URL_REGEX = r'\b(?:http|https|tcp)://[^\s:/?#]+(?::\d+)?(?:/[^\s]*)?'

# --- Helpers ---
def extract_urls(text):
    return re.findall(URL_REGEX, text)

def is_authorized(req):
    token = req.headers.get("Authorization")
    return token == f"Bearer {AUTH_TOKEN}"

# --- Main Endpoint ---
@app.route('/run', methods=['POST'])
def run_command():
    if not is_authorized(request):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    action = data.get("action")

    if action == "extract_urls":
        file_path = data.get("file_path")
        if not file_path:
            return jsonify({"error": 'Missing "file_path"'}), 400
        if not os.path.isfile(file_path):
            return jsonify({"error": f"File not found: {file_path}"}), 404
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            urls = extract_urls(content)
            return jsonify({"urls": urls})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif action == "exec":
        command = data.get("command")
        if not command:
            return jsonify({"error": 'Missing "command"'}), 400
        if isinstance(command, str):
            command = command.strip()
        try:
            result = subprocess.run(
                command,
                shell=isinstance(command, str),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return jsonify({
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            })
        except subprocess.CalledProcessError as e:
            return jsonify({
                "error": "Command failed",
                "stdout": e.stdout,
                "stderr": e.stderr,
                "returncode": e.returncode
            }), 500

    else:
        return jsonify({"error": "Unsupported action"}), 400

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8000)
