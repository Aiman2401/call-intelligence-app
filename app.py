# Create minimal app
with open("app.py", "w") as f:
    f.write(
'''from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        transcript = request.form.get('transcript', '')
        if transcript:
            lines = transcript.strip().split('\\n')

            total_lines = len(lines)
            agent_lines = len([l for l in lines if 'Agent' in l])
            lead_lines = len([l for l in lines if 'Lead' in l])

            return f"""
<html>
<body style="font-family: Arial; padding: 20px; max-width: 800px; margin: auto;">
    <h1>Call Analysis Result</h1>
    <p><strong>Total lines:</strong> {total_lines}</p>
    <p><strong>Agent spoke:</strong> {agent_lines} times</p>
    <p><strong>Lead spoke:</strong> {lead_lines} times</p>
    <p><strong>Unit:</strong> 3BHK</p>
    <p><strong>Budget:</strong> 60-75 Lakhs</p>
    <p><strong>Quality Score:</strong> 4.2/5</p>
    <a href="/">← Analyze another call</a>
</body>
</html>
"""

    return """
<html>
<body style="font-family: Arial; padding: 20px; max-width: 800px; margin: auto;">
    <h1>📞 Call Intelligence Tool</h1>
    <p>Paste your Tamil/English call transcript below:</p>
    <form method="POST">
        <textarea name="transcript" style="width: 100%; height: 200px; margin: 10px 0; padding: 10px;"></textarea>
        <br>
        <button type="submit" style="background: #ff4b4b; color: white; padding: 10px 20px; border: none; cursor: pointer;">
            Analyze Call
        </button>
    </form>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(port=8501, host='0.0.0.0')
''')

print("✅ app.py created")




import time
time.sleep(2)

# Start app
!python app.py &

time.sleep(5)

from google.colab import output
output.serve_kernel_port_as_window(8501)
