# 🎼 Mozart

Mozart is a powerful, hybrid Discord bot designed to bring high-quality music and automated moderation to your server, coupled with a sleek **Web Dashboard** for real-time control.

---

## ✨ Features

### 🎵 Advanced Music System

* **Slash Commands:** Modern interaction using `/play`, `/skip`, `/stop`, etc.
* **Multi-Platform Support:** Stream audio from YouTube, SoundCloud, and more via `yt-dlp`.
* **Interactive UI:** Control playback with beautiful Discord buttons (Pause, Skip, Stop).
* **Persistent Queue:** Queue data is stored in a SQLite database, ensuring stability.

### 🛡️ Automated Moderation

* **Strike System:** Automated profanity filtering with a "3-strikes and you're out" policy.
* **Auto-Ban:** Users are automatically banned from the server upon reaching their 3rd warning.
* **Safe Handling:** Respects Discord permissions and provides feedback when actions cannot be performed.

### 📊 Web Dashboard

* **OAuth2 Integration:** Secure login using your Discord account.
* **Real-time Controls:** Pause, resume, skip, and manage volume directly from your browser.
* **Status Monitoring:** View bot latency, uptime, and current server counts at a glance.
* **Partial Updates:** High-performance dashboard using HTMX-style partial refreshes for a smooth experience.

---

## 🛠️ Tech Stack

* **Language:** Python 3.11+
* **Bot Framework:** [discord.py](https://github.com/Rapptz/discord.py)
* **Web Framework:** [Flask](https://flask.palletsprojects.com/) + [Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/)
* **Audio Engine:** [yt-dlp](https://github.com/yt-dlp/yt-dlp) + FFmpeg
* **Database:** SQLite (Persistent storage for warnings and queues)
* **DevOps:** Docker, GitHub Actions

---

## 📂 Project Structure

```text
Mozart/
├── src/
│   ├── cogs/          # Bot modules (Music, Moderation)
│   ├── utils/         # Database and helper functions
│   ├── web/           # Flask app, templates, and static assets
│   └── main.py        # Discord bot entry point
├── run.py             # Main application orchestrator (Flask + Bot)
├── Dockerfile         # Multi-stage Alpine-based Docker image
└── compose.yaml       # Docker Compose configuration
```

---

## 🚀 Getting Started

### Prerequisites

* Python 3.11 or higher
* FFmpeg installed on your system
* A Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))

### Local Setup

1. **Clone the repository:**

    ```bash
    git clone https://github.com/RenX86/Mozart.git
    cd Mozart
    ```

2. **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3. **Configure Environment:**
    Create a `.env` file in the root directory:

    ```env
    DISCORD_TOKEN=your_bot_token_here
    DISCORD_CLIENT_ID=your_client_id
    DISCORD_CLIENT_SECRET=your_client_secret
    FLASK_SECRET_KEY=something_very_secret
    OAUTH2_REDIRECT_URI=http://localhost:5000/callback
    ```

4. **Run the application:**

    ```bash
    python run.py
    ```

### Docker Setup

```bash
docker compose up -d
```

---

## 🎮 Discord Commands

| Command | Description |
| :--- | :--- |
| `/play <query>` | Searches and plays a song or adds it to the queue. |
| `/pause` | Pauses the current track. |
| `/resume` | Resumes a paused track. |
| `/skip` | Skips to the next song in the queue. |
| `/stop` | Stops the music and clears the session. |
| `!sync` | (Admin) Syncs slash commands to the current server. |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
