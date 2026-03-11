from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
import time
import os

app = Flask(__name__, static_folder="static")
CORS(app)

SUBREDDIT = "JEEAdv26dailyupdates"
HEADERS = {"User-Agent": "jee-viewer/1.0 by local-script"}

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/posts")
def get_posts():
    flair = request.args.get("flair", "GOOD SOLVE")
    from_ts = int(request.args.get("from_ts", int(time.time()) - 5 * 86400))
    to_ts = int(request.args.get("to_ts", int(time.time())))

    all_posts = []
    after = None
    stop = False

    while not stop:
        params = {
            "q": f'flair:"{flair}"',
            "restrict_sr": 1,
            "sort": "new",
            "limit": 100,
            "type": "link"
        }
        if after:
            params["after"] = after

        try:
            url = f"https://www.reddit.com/r/{SUBREDDIT}/search.json"
            res = requests.get(url, headers=HEADERS, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        children = data.get("data", {}).get("children", [])
        if not children:
            break

        for child in children:
            p = child["data"]
            if p["created_utc"] < from_ts:
                stop = True
                break
            if from_ts <= p["created_utc"] <= to_ts:
                flair_text = (p.get("link_flair_text") or "").lower()
                if flair.lower() in flair_text:
                    images = []
                    if p.get("url") and any(p["url"].lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
                        images.append(p["url"])
                    if p.get("preview", {}).get("images"):
                        for img in p["preview"]["images"]:
                            src = img.get("source", {}).get("url", "").replace("&amp;", "&")
                            if src:
                                images.append(src)
                    if p.get("media_metadata"):
                        for m in p["media_metadata"].values():
                            src = (m.get("s", {}).get("u") or m.get("s", {}).get("gif") or "").replace("&amp;", "&")
                            if src:
                                images.append(src)

                    all_posts.append({
                        "id": p["id"],
                        "title": p["title"],
                        "author": p["author"],
                        "score": p["score"],
                        "created_utc": p["created_utc"],
                        "permalink": p["permalink"],
                        "images": list(dict.fromkeys(images)),
                        "flair": p.get("link_flair_text", "")
                    })

        after = data.get("data", {}).get("after")
        if not after:
            break

    return jsonify({"posts": all_posts, "count": len(all_posts)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
