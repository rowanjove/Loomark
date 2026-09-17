import sys
import argparse
import uvicorn
from engine.config import DEFAULT_HOST, DEFAULT_PORT

def main():
    parser = argparse.ArgumentParser(description="Loomark Crawler Engine")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind to")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable reload mode")
    args = parser.parse_args()

    print(f"[*] Starting Loomark Engine on http://{args.host}:{args.port}")
    uvicorn.run("engine.api.app:app", host=args.host, port=args.port, reload=args.reload)

if __name__ == "__main__":
    main()
