#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A minimal RESTful backend for the Bewerbermanagement‑Tool.

This server uses only Python's built‑in modules to ensure that it runs in
restricted environments without external dependencies. It provides endpoints
for managing anonymised candidate records, storing evaluation data and
generating PDF reports via the headless Chromium browser. The API is
described below:

Endpoints:

  GET  /api/candidates                -> list all candidates (id, created_at, consented)
  POST /api/candidates               -> create a new candidate; returns id and created_at
  GET  /api/candidates/<id>           -> fetch candidate details
  PUT  /api/candidates/<id>           -> update candidate fields (JSON body)
  DELETE /api/candidates/<id>         -> delete a candidate
  POST /api/candidates/<id>/export    -> generate a PDF report for the candidate

All responses are JSON except for the PDF export which returns a PDF file.

The server also implements basic CORS handling so that the React frontend can
communicate with it from a different origin during development.
"""
import os
import json
import sqlite3
import random
import subprocess
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse


DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')


def init_db():
    """Create the SQLite database and the candidates table if needed."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS candidates (
            id TEXT PRIMARY KEY,
            created_at TEXT,
            self_reflection TEXT,
            ratings TEXT,
            conclusion TEXT,
            notes TEXT,
            star_notes TEXT,
            vesier_notes TEXT,
            reflection_consistency TEXT,
            consented INTEGER DEFAULT 0,
            consent_date TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def generate_candidate_id() -> str:
    """Return a new anonymised candidate ID of the form BW-YYYY-XXXXX."""
    year = datetime.now().year
    number = random.randint(0, 99999)
    return f"BW-{year}-{number:05d}"


def dict_from_row(row):
    """Convert a SQLite row to a Python dictionary."""
    if row is None:
        return None
    (
        cid,
        created_at,
        self_reflection,
        ratings,
        conclusion,
        notes,
        star_notes,
        vesier_notes,
        reflection_consistency,
        consented,
        consent_date,
    ) = row
    return {
        'id': cid,
        'created_at': created_at,
        'self_reflection': self_reflection,
        'ratings': json.loads(ratings) if ratings else None,
        'conclusion': conclusion,
        'notes': notes,
        'star_notes': star_notes,
        'vesier_notes': vesier_notes,
        'reflection_consistency': reflection_consistency,
        'consented': bool(consented),
        'consent_date': consent_date,
    }


def build_html(candidate):
    """Construct an HTML document summarising a candidate's evaluation."""
    # Escape missing values with placeholder dashes
    def esc(val):
        return val if val else '–'
    ratings_rows = ''
    ratings = candidate.get('ratings') or {}
    for dim, rating in ratings.items():
        ratings_rows += f'<tr><td>{dim}</td><td>{rating}</td></tr>'
    html = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="utf-8">
        <title>Bewerberauswertung {candidate['id']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 40px; }}
            h1 {{ color: #2563eb; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; }}
            th {{ background-color: #f2f2f2; text-align: left; }}
            .section {{ margin-top: 30px; }}
        </style>
    </head>
    <body>
        <h1>Auswertung für Bewerber {candidate['id']}</h1>
        <p>Erstellt am {candidate['created_at']}</p>
        <div class="section">
            <h2>Selbstreflexion</h2>
            <p>{esc(candidate.get('self_reflection'))}</p>
        </div>
        <div class="section">
            <h2>Bewertung (1–5)</h2>
            <table>
                <tr><th>Dimension</th><th>Bewertung</th></tr>
                {ratings_rows}
            </table>
        </div>
        <div class="section">
            <h2>Notizen</h2>
            <p>{esc(candidate.get('notes'))}</p>
        </div>
        <div class="section">
            <h2>STAR‑Notizen</h2>
            <p>{esc(candidate.get('star_notes'))}</p>
        </div>
        <div class="section">
            <h2>VeSiEr‑Notizen</h2>
            <p>{esc(candidate.get('vesier_notes'))}</p>
        </div>
        <div class="section">
            <h2>Fazit</h2>
            <p>{esc(candidate.get('conclusion'))}</p>
        </div>
    </body>
    </html>
    """
    return html


def generate_pdf_from_html(html_content: str, output_path: str) -> None:
    """
    Create a PDF from an HTML string using headless Chromium. The function
    writes the HTML to a temporary file and then invokes Chromium with
    --headless and --print-to-pdf.
    """
    import tempfile
    # Write HTML to a temporary file
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as tmp_html:
        tmp_html.write(html_content)
        tmp_html.flush()
        html_file_path = tmp_html.name
    # Determine the output PDF path
    # Use file:// scheme to access the HTML file
    file_url = f'file://{html_file_path}'
    # Use Chromium to convert to PDF
    # The container includes the chromium binary at /usr/bin/chromium
    cmd = [
        'chromium',
        '--headless',
        '--no-sandbox',
        '--disable-gpu',
        f'--print-to-pdf={output_path}',
        file_url,
    ]
    subprocess.run(cmd, check=True)
    # Remove the temporary HTML file
    try:
        os.unlink(html_file_path)
    except OSError:
        pass


class CandidateServer(BaseHTTPRequestHandler):
    """HTTP request handler implementing the REST API."""

    # Allowed methods for CORS preflight
    def _set_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _send_json(self, data, status=200):
        """Send a JSON response."""
        response = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self._set_cors()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_OPTIONS(self):
        """Respond to CORS preflight requests."""
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path_parts = [p for p in parsed.path.split('/') if p]
        # Handle /api/candidates or /api/candidates/<id>
        if len(path_parts) == 2 and path_parts[:2] == ['api', 'candidates']:
            # List all candidates
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, created_at, consented FROM candidates")
            rows = c.fetchall()
            conn.close()
            items = [
                {'id': r[0], 'created_at': r[1], 'consented': bool(r[2])}
                for r in rows
            ]
            self._send_json({'candidates': items})
            return
        if len(path_parts) == 3 and path_parts[:2] == ['api', 'candidates']:
            candidate_id = path_parts[2]
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
            row = c.fetchone()
            conn.close()
            candidate = dict_from_row(row)
            if candidate is None:
                self._send_json({'error': 'Candidate not found'}, status=404)
            else:
                self._send_json(candidate)
            return
        # Unknown route
        self._send_json({'error': 'Not found'}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path_parts = [p for p in parsed.path.split('/') if p]
        # Create new candidate
        if path_parts == ['api', 'candidates']:
            candidate_id = generate_candidate_id()
            created_at = datetime.utcnow().isoformat()
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                "INSERT INTO candidates (id, created_at) VALUES (?, ?)",
                (candidate_id, created_at)
            )
            conn.commit()
            conn.close()
            self._send_json({'id': candidate_id, 'created_at': created_at}, status=201)
            return
        # Export PDF for candidate
        if len(path_parts) == 4 and path_parts[:2] == ['api', 'candidates'] and path_parts[3] == 'export':
            candidate_id = path_parts[2]
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
            row = c.fetchone()
            conn.close()
            candidate = dict_from_row(row)
            if candidate is None:
                self._send_json({'error': 'Candidate not found'}, status=404)
                return
            # Generate HTML and convert to PDF
            html = build_html(candidate)
            import tempfile
            pdf_path = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
            try:
                generate_pdf_from_html(html, pdf_path)
            except Exception as e:
                self._send_json({'error': f'PDF generation failed: {e}'}, status=500)
                return
            # Read PDF file and send with appropriate headers
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
            os.unlink(pdf_path)
            self.send_response(200)
            self._set_cors()
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition', f'attachment; filename="{candidate_id}.pdf"')
            self.send_header('Content-Length', str(len(pdf_data)))
            self.end_headers()
            self.wfile.write(pdf_data)
            return
        # Unknown POST route
        self._send_json({'error': 'Not found'}, status=404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        path_parts = [p for p in parsed.path.split('/') if p]
        if len(path_parts) == 3 and path_parts[:2] == ['api', 'candidates']:
            candidate_id = path_parts[2]
            # Read request body
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8') if length > 0 else '{}'
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self._send_json({'error': 'Invalid JSON'}, status=400)
                return
            allowed_fields = {
                'self_reflection',
                'ratings',
                'conclusion',
                'notes',
                'star_notes',
                'vesier_notes',
                'reflection_consistency',
                'consented',
                'consent_date',
            }
            updates = {}
            for key, value in data.items():
                if key in allowed_fields:
                    updates[key] = value
            if not updates:
                self._send_json({'error': 'No valid fields to update'}, status=400)
                return
            # Build SQL update statement
            set_clauses = []
            values = []
            for key, value in updates.items():
                if key == 'ratings' and value is not None:
                    set_clauses.append(f"{key} = ?")
                    values.append(json.dumps(value))
                elif key == 'consented':
                    set_clauses.append(f"{key} = ?")
                    values.append(1 if value else 0)
                else:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            values.append(candidate_id)
            sql = f"UPDATE candidates SET {', '.join(set_clauses)} WHERE id = ?"
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(sql, tuple(values))
            conn.commit()
            conn.close()
            self._send_json({'status': 'updated'})
            return
        # Unknown PUT route
        self._send_json({'error': 'Not found'}, status=404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path_parts = [p for p in parsed.path.split('/') if p]
        if len(path_parts) == 3 and path_parts[:2] == ['api', 'candidates']:
            candidate_id = path_parts[2]
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
            conn.commit()
            conn.close()
            self._send_json({'status': 'deleted'})
            return
        # Unknown DELETE route
        self._send_json({'error': 'Not found'}, status=404)


def run_server(port: int = 5000):
    """Start the HTTP server."""
    init_db()
    server = HTTPServer(('0.0.0.0', port), CandidateServer)
    print(f"Server running on port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down server...")
        server.server_close()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5000'))
    run_server(port)