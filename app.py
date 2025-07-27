import os
import json
import sqlite3
from datetime import datetime
import asyncio
from flask import Flask, request, jsonify, send_file, abort, make_response
from flask_cors import CORS
from jinja2 import Template

try:
    from pyppeteer import launch
except ImportError:
    launch = None


DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')


def init_db():
    """Initialise the SQLite database and ensure required tables exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Using TEXT for JSON storage; consented is integer 0/1
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


def get_connection():
    return sqlite3.connect(DB_PATH)


def row_to_dict(row):
    """Convert a SQLite row to dictionary."""
    if row is None:
        return None
    (
        candidate_id,
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
        'id': candidate_id,
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


def generate_candidate_id():
    """Generate a new anonymised candidate ID following the pattern BW-YYYY-XXXXX."""
    year = datetime.now().year
    # generate five-digit random number
    import random
    number = random.randint(0, 99999)
    return f"BW-{year}-{number:05d}"


app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
CORS(app)


@app.before_first_request
def setup_database():
    init_db()


@app.route('/api/candidates', methods=['GET'])
def list_candidates():
    """Return all candidates with minimal data."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, created_at, consented FROM candidates")
    rows = c.fetchall()
    conn.close()
    data = [
        {
            'id': row[0],
            'created_at': row[1],
            'consented': bool(row[2]),
        }
        for row in rows
    ]
    return jsonify({'candidates': data})


@app.route('/api/candidates', methods=['POST'])
def create_candidate():
    """Create a new candidate with default empty values."""
    candidate_id = generate_candidate_id()
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO candidates (id, created_at) VALUES (?, ?)",
        (candidate_id, now),
    )
    conn.commit()
    conn.close()
    return jsonify({'id': candidate_id, 'created_at': now}), 201


@app.route('/api/candidates/<candidate_id>', methods=['GET'])
def get_candidate(candidate_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
    row = c.fetchone()
    conn.close()
    candidate = row_to_dict(row)
    if candidate is None:
        return jsonify({'error': 'Candidate not found'}), 404
    return jsonify(candidate)


@app.route('/api/candidates/<candidate_id>', methods=['PUT'])
def update_candidate(candidate_id):
    """Update candidate data. Expect JSON with fields to update."""
    data = request.get_json(force=True)
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
        return jsonify({'error': 'No valid fields to update'}), 400
    # Build query
    set_clause = []
    values = []
    for key, value in updates.items():
        # JSON encode ratings
        if key == 'ratings' and value is not None:
            set_clause.append(f"{key} = ?")
            values.append(json.dumps(value))
        elif key == 'consented':
            set_clause.append(f"{key} = ?")
            values.append(1 if value else 0)
        else:
            set_clause.append(f"{key} = ?")
            values.append(value)
    values.append(candidate_id)
    query = f"UPDATE candidates SET {', '.join(set_clause)} WHERE id = ?"
    conn = get_connection()
    c = conn.cursor()
    c.execute(query, tuple(values))
    conn.commit()
    conn.close()
    return jsonify({'status': 'updated'})


@app.route('/api/candidates/<candidate_id>', methods=['DELETE'])
def delete_candidate(candidate_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM candidates WHERE id = ?", (candidate_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'deleted'})


def build_html_for_candidate(candidate):
    """
    Build a simple HTML representation of a candidate's evaluation. This HTML
    will be converted to PDF. It uses inline styles for a consistent look.
    """
    # Use a basic template to render candidate information
    html_template = Template(
        """
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="utf-8" />
            <style>
                body { font-family: Arial, sans-serif; padding: 40px; }
                h1 { color: #2563eb; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; }
                th { background-color: #f2f2f2; text-align: left; }
                .section { margin-top: 30px; }
            </style>
            <title>Bewerberauswertung {{ candidate.id }}</title>
        </head>
        <body>
            <h1>Auswertung für Bewerber {{ candidate.id }}</h1>
            <p>Erstellt am {{ candidate.created_at }}</p>

            <div class="section">
                <h2>Selbstreflexion</h2>
                <p>{{ candidate.self_reflection | default('Keine Angaben', true) }}</p>
            </div>
            <div class="section">
                <h2>Bewertung (1–5)</h2>
                <table>
                    <tr>
                        <th>Dimension</th>
                        <th>Bewertung</th>
                    </tr>
                    {% for dim, rating in candidate.ratings.items() %}
                    <tr>
                        <td>{{ dim }}</td>
                        <td>{{ rating }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            <div class="section">
                <h2>Notizen</h2>
                <p>{{ candidate.notes | default('–', true) }}</p>
            </div>
            <div class="section">
                <h2>STAR-Notizen</h2>
                <p>{{ candidate.star_notes | default('–', true) }}</p>
            </div>
            <div class="section">
                <h2>VeSiEr-Notizen</h2>
                <p>{{ candidate.vesier_notes | default('–', true) }}</p>
            </div>
            <div class="section">
                <h2>Fazit</h2>
                <p>{{ candidate.conclusion | default('–', true) }}</p>
            </div>
        </body>
        </html>
        """
    )
    return html_template.render(candidate=candidate)


async def generate_pdf(html_content, output_path):
    """Use pyppeteer to generate a PDF file from HTML content."""
    # Launch headless browser; using '--no-sandbox' for environments like containers
    browser = await launch(options={
        'args': ['--no-sandbox'],
        'headless': True
    })
    page = await browser.newPage()
    # Set content and wait for network to be idle
    await page.setContent(html_content, waitUntil=['networkidle0'])
    await page.pdf({'path': output_path, 'format': 'A4', 'printBackground': True})
    await browser.close()


@app.route('/api/candidates/<candidate_id>/export', methods=['POST'])
def export_candidate(candidate_id):
    """Generate PDF report for a candidate and return it as a downloadable file."""
    # Fetch candidate
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
    row = c.fetchone()
    conn.close()
    candidate = row_to_dict(row)
    if candidate is None:
        return jsonify({'error': 'Candidate not found'}), 404
    # Validate we have ratings; fallback to empty dict
    if not candidate.get('ratings'):
        candidate['ratings'] = {}
    html = build_html_for_candidate(candidate)
    # Create temporary PDF
    tmp_pdf = os.path.join('/tmp', f"{candidate_id}.pdf")
    # If pyppeteer is not available, return error
    if launch is None:
        return jsonify({'error': 'PDF generation unavailable (pyppeteer not installed)'}), 500
    try:
        # Use asyncio to run generation
        asyncio.get_event_loop().run_until_complete(generate_pdf(html, tmp_pdf))
    except Exception as e:
        return jsonify({'error': f'PDF generation failed: {str(e)}'}), 500
    # Send file as response
    response = make_response(send_file(tmp_pdf, as_attachment=True, download_name=f"{candidate_id}.pdf"))
    response.headers['Content-Type'] = 'application/pdf'
    return response


if __name__ == '__main__':
    # For local development. In production, use a WSGI server.
    init_db()
    app.run(host='0.0.0.0', port=5000)