import os
import json
import subprocess
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='web_ui', static_url_path='')
CORS(app)

@app.route('/')
def index():
    return send_from_directory('web_ui', 'index.html')

@app.route('/api/transactions')
def get_transactions():
    """Serve the generated transactions.json file"""
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    tx_file = os.path.join(output_dir, 'transactions.json')
    if os.path.exists(tx_file):
        with open(tx_file, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({"error": "transactions.json not found. Run the pipeline first."}), 404

@app.route('/api/run-pipeline', methods=['POST'])
def run_pipeline():
    """Run the pipeline and stream the output back to the client using SSE"""
    data = request.json
    source = data.get('source')
    base_url = data.get('base_url')
    skip_carbon = data.get('skip_carbon', False)
    
    if not source:
        return jsonify({"error": "Source is required"}), 400
        
    def generate():
        cmd = ['python', 'pipeline.py', '--source', source]
        if base_url:
            cmd.extend(['--base-url', base_url])
        if skip_carbon:
            cmd.append('--skip-carbon')
            
        # Ensure unbuffered output so we get lines immediately
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        for line in iter(process.stdout.readline, ''):
            if line:
                # Format as Server-Sent Event
                yield f"data: {line.strip()}\n\n"
                
        process.stdout.close()
        return_code = process.wait()
        
        if return_code == 0:
            yield "data: [DONE]\n\n"
        else:
            yield f"data: [ERROR] Pipeline exited with code {return_code}\n\n"
            
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    print("Starting Code Carbon Server at http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
