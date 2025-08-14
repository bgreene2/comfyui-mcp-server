from PIL import Image
from flask import Flask, send_from_directory, render_template_string, request, abort
import argparse
import os

# Parse command line arguments
parser = argparse.ArgumentParser(description='Image hosting server')
parser.add_argument('--output-dir', default='output', help='Directory containing images to serve (default: output)')
args = parser.parse_args()

app = Flask(__name__)
OUTPUT_DIR = args.output_dir
THUMBNAIL_DIR = os.path.join(OUTPUT_DIR, 'thumbnails')
PAGE_SIZE = 12  # Items per page

# Create directories
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(THUMBNAIL_DIR, exist_ok=True)

def generate_thumbnail(original_path, thumbnail_path):
    """Create thumbnail for the given image"""
    try:
        with Image.open(original_path) as img:
            img.thumbnail((150, 150), Image.LANCZOS)
            img.save(thumbnail_path, "PNG")
    except Exception as e:
        print(f"Error generating thumbnail: {e}")

@app.route('/')
def list_files():
    """List all files in output directory with thumbnails and pagination"""
    page = int(request.args.get('page', 1))
    files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.lower().endswith('.png')])
    files.reverse()

    # Generate thumbnails if missing
    for f in files:
        original_path = os.path.join(OUTPUT_DIR, f)
        thumbnail_path = os.path.join(THUMBNAIL_DIR, f)
        if not os.path.exists(thumbnail_path):
            generate_thumbnail(original_path, thumbnail_path)
    
    # Paginate files
    total_pages = (len(files) + PAGE_SIZE - 1) // PAGE_SIZE
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    paginated_files = files[start:end]

    # Build HTML links
    file_items = []
    for f in paginated_files:
        safe_filename = f.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        file_items.append(f'''
            <div class="file-item">
                <a href="/view/{f}" class="file-link">
                    <img src="/thumb/{f}" alt="{safe_filename}" class="thumbnail">
                    <span class="file-name">{safe_filename}</span>
                </a>
            </div>
        ''')

    return render_template_string('''
        <html>
        <head>
            <title>PNG Gallery</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                :root {
                    --bg-primary: #121212;
                    --bg-secondary: #1e1e1e;
                    --text-primary: #ffffff;
                    --text-secondary: #b0b0b0;
                    --accent: #bb86fc;
                    --accent-hover: #985eff;
                    --border: #333333;
                }
                
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                
                body {
                    background-color: var(--bg-primary);
                    color: var(--text-primary);
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    line-height: 1.6;
                    padding: 20px;
                }
                
                h1 {
                    margin-bottom: 20px;
                    text-align: center;
                    font-weight: 300;
                    letter-spacing: 1px;
                }
                
                .gallery {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                    gap: 20px;
                    margin-bottom: 40px;
                }
                
                .file-item {
                    background-color: var(--bg-secondary);
                    border-radius: 8px;
                    overflow: hidden;
                    transition: transform 0.2s, box-shadow 0.2s;
                    border: 1px solid var(--border);
                }
                
                .file-item:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 10px 20px rgba(0,0,0,0.3);
                }
                
                .file-link {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    padding: 15px;
                    text-decoration: none;
                    color: inherit;
                    width: 100%;
                }
                
                .thumbnail {
                    width: 100%;
                    height: 150px;
                    object-fit: contain;
                    background-color: var(--bg-primary);
                    border-radius: 4px;
                    margin-bottom: 10px;
                }
                
                .file-name {
                    font-size: 0.9rem;
                    text-align: center;
                    color: var(--text-secondary);
                    word-break: break-all;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    max-width: 100%;
                }
                
                .pagination {
                    display: flex;
                    justify-content: center;
                    gap: 10px;
                    margin: 20px 0;
                }
                
                .pagination a, .pagination span {
                    padding: 8px 16px;
                    background-color: var(--bg-secondary);
                    color: var(--text-primary);
                    border-radius: 4px;
                    text-decoration: none;
                    transition: background-color 0.2s;
                }
                
                .pagination a:hover {
                    background-color: var(--accent-hover);
                }
                
                .pagination .current {
                    background-color: var(--accent);
                    font-weight: bold;
                }
                
                .pagination-input {
                    margin: 20px 0;
                    text-align: center;
                }
                
                .pagination-input input {
                    width: 80px;
                    padding: 8px;
                    background-color: var(--bg-secondary);
                    color: var(--text-primary);
                    border: 1px solid var(--border);
                    border-radius: 4px;
                }
                
                .pagination-input button {
                    padding: 8px 16px;
                    background-color: var(--accent);
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    transition: background-color 0.2s;
                }
                
                .pagination-input button:hover {
                    background-color: var(--accent-hover);
                }
                
                .refresh-btn {
                    display: block;
                    margin: 20px auto;
                    padding: 10px 20px;
                    background-color: var(--accent);
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 1rem;
                    transition: background-color 0.2s;
                }
                
                .refresh-btn:hover {
                    background-color: var(--accent-hover);
                }
                
                @media (max-width: 768px) {
                    .gallery {
                        grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
                        gap: 15px;
                    }
                    
                    .thumbnail {
                        height: 120px;
                    }
                }
                
                @media (max-width: 480px) {
                    .gallery {
                        grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
                    }
                    
                    .file-name {
                        font-size: 0.8rem;
                    }
                }
            </style>
        </head>
        <body>
            <h1>Available PNG Images</h1>
            
            <div class="gallery">
                {% for item in file_items %}
                    {{ item|safe }}
                {% endfor %}
            </div>
            
            <div class="pagination">
                {% if page > 1 %}
                    <a href="/?page={{ page-1 }}">Previous</a>
                {% endif %}
                
                {% if total_pages <= 7 %}
                    {% for p in range(1, total_pages + 1) %}
                        {% if p == page %}
                            <span class="current">{{ p }}</span>
                        {% else %}
                            <a href="/?page={{ p }}">{{ p }}</a>
                        {% endif %}
                    {% endfor %}
                {% else %}
                    {% if page <= 4 %}
                        {% for p in range(1, 6) %}
                            {% if p == page %}
                                <span class="current">{{ p }}</span>
                            {% else %}
                                <a href="/?page={{ p }}">{{ p }}</a>
                            {% endif %}
                        {% endfor %}
                        <span>...</span>
                        <a href="/?page={{ total_pages }}">{{ total_pages }}</a>
                    {% elif page >= total_pages - 3 %}
                        <a href="/?page=1">1</a>
                        <span>...</span>
                        {% for p in range(total_pages - 4, total_pages + 1) %}
                            {% if p == page %}
                                <span class="current">{{ p }}</span>
                            {% else %}
                                <a href="/?page={{ p }}">{{ p }}</a>
                            {% endif %}
                        {% endfor %}
                    {% else %}
                        <a href="/?page=1">1</a>
                        <span>...</span>
                        {% for p in range(page - 1, page + 2) %}
                            {% if p == page %}
                                <span class="current">{{ p }}</span>
                            {% else %}
                                <a href="/?page={{ p }}">{{ p }}</a>
                            {% endif %}
                        {% endfor %}
                        <span>...</span>
                        <a href="/?page={{ total_pages }}">{{ total_pages }}</a>
                    {% endif %}
                {% endif %}
                
                {% if page < total_pages %}
                    <a href="/?page={{ page+1 }}">Next</a>
                {% endif %}
            </div>
            
            <div class="pagination-input">
                <form method="GET" style="display: flex; gap: 10px; align-items: center; justify-content: center;">
                    <span>Go to page:</span>
                    <input type="number" name="page" min="1" max="{{ total_pages }}" value="{{ page }}" 
                           style="width: 80px; padding: 8px; background-color: var(--bg-secondary); 
                                  color: var(--text-primary); border: 1px solid var(--border); border-radius: 4px;">
                    <button type="submit" 
                            style="padding: 8px 16px; background-color: var(--accent); color: white; 
                                   border: none; border-radius: 4px; cursor: pointer;">
                        Go
                    </button>
                </form>
            </div>
            
            <button class="refresh-btn" onclick="window.location.reload()">Refresh</button>
        </body>
        </html>
    ''', file_items=file_items, page=page, total_pages=total_pages)

@app.route('/thumb/<path:filename>')
def serve_thumbnail(filename):
    """Serve thumbnail images"""
    if not filename.lower().endswith('.png'):
        abort(400, "Only PNG files are allowed")
    return send_from_directory(THUMBNAIL_DIR, filename)

@app.route('/view/<path:filename>')
def view_file(filename):
    """Serve original PNG files"""
    if not filename.lower().endswith('.png'):
        abort(400, "Only PNG files are allowed")
    return send_from_directory(OUTPUT_DIR, filename)

if __name__ == '__main__':
    print(f"Starting server at http://0.0.0.0:8081")
    print(f"Place PNG files in the '{OUTPUT_DIR}/' directory")
    print("Access from other devices using: http://<YOUR_IP>:8081")
    app.run(host='0.0.0.0', port=8081, debug=True)
