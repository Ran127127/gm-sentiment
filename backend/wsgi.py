import sys
import os

# 确保项目根目录在Python路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("[WSGI] Starting application...", file=sys.stderr)
print(f"[WSGI] Python: {sys.version}", file=sys.stderr)
print(f"[WSGI] PORT env: {os.getenv('PORT', 'not set')}", file=sys.stderr)

try:
    from app import create_app
    app = create_app()
    print("[WSGI] Application created successfully!", file=sys.stderr)
except Exception as e:
    print(f"[WSGI] FATAL: Failed to create app: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    raise

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
