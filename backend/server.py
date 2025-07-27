from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Beispielrouten
@app.route('/api/candidates', methods=['GET'])
def get_candidates():
    return jsonify([{"id": "BW-2025-00001", "name": "Testbewerber"}])

@app.route('/api/save', methods=['POST'])
def save_eval():
    data = request.json
    print("Speichern:", data)
    return jsonify({"status": "ok"})

@app.route('/api/export', methods=['POST'])
def export_pdf():
    return jsonify({"status": "PDF generation stub"})

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)
