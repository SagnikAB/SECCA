"""Run the Vercel API locally while Vite serves the frontend."""

from analyze import app


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
