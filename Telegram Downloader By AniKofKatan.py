#!/usr/bin/env python3
"""
Made by Twisted Fate [fxp]
Telegram Video Downloader - Downloads videos from a Telegram channel/group
"""

import asyncio, os, time, threading, sys, logging, json, signal, shutil
from telethon import TelegramClient
from dotenv import load_dotenv
from pathlib import Path

# ─── LOAD ENVIRONMENT VARIABLES ───────────────────────────────────────────────
load_dotenv()

# ─── LOGGING SETUP ─────────────────────────────────────────────────────────────
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f'downloader_{time.strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ─── TELEGRAM CREDENTIALS ──────────────────────────────────────────────────────
api_id = int(os.getenv('TELEGRAM_API_ID', '123123123'))
api_hash = os.getenv('TELEGRAM_API_HASH', '123123123123123123')
session_name = os.getenv('TELEGRAM_SESSION', 'downloader_session')

# ─── SOURCE CHANNEL/GROUP ──────────────────────────────────────────────────────
source_group = int(os.getenv('SOURCE_GROUP', '-100123123123'))

# ─── SETTINGS ──────────────────────────────────────────────────────────────────
download_folder = Path(os.getenv('DOWNLOAD_FOLDER', 'downloads'))
progress_file = Path(os.getenv('PROGRESS_FILE', 'download_progress.json'))
min_file_size = int(os.getenv('MIN_SIZE_MB', '1')) * 1024 * 1024
max_file_size = int(os.getenv('MAX_SIZE_MB', '2000')) * 1024 * 1024
max_disk_usage_gb = float(os.getenv('MAX_DISK_GB', '300'))

# ─── STATE VARIABLES ───────────────────────────────────────────────────────────
class Stats:
    def __init__(self):
        self.downloaded = 0
        self.failed = 0
        self.skipped = 0
        self.start_time = time.time()
        self.skip_current = False

stats = Stats()
client = None

# ─── SIGNAL HANDLING ───────────────────────────────────────────────────────────
def setup_signal_handlers():
    def signal_handler(sig, frame):
        logger.info("Received termination signal. Cleaning up...")
        print("\n⚠️ Program terminating. Cleaning up...")
        if client and client.is_connected():
            asyncio.create_task(client.disconnect())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def key_listener():
    """Listen for 'ss' to skip current operation"""
    buf = ''
    while True:
        try:
            if os.name == 'nt':  # Windows
                import msvcrt
                if msvcrt.kbhit():
                    buf += msvcrt.getch().decode('utf-8', errors='ignore')
            else:  # Unix
                import termios, tty, select
                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    tty.setcbreak(sys.stdin.fileno())
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        buf += sys.stdin.read(1)
                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            
            if buf.endswith('ss'):
                stats.skip_current = True
                print("\n⏩ Skipping current file...")
                buf = ''
            elif len(buf) > 10:
                buf = buf[-10:]
            
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Key listener error: {e}")
            time.sleep(1)

# ─── PROGRESS BAR ──────────────────────────────────────────────────────────────
_start_time = {}
def _progress(current, total, label, file_id):
    """Display progress bar with speed and ETA"""
    if stats.skip_current:
        raise Exception("Skipped by user")
        
    if current == 0 or file_id not in _start_time:
        _start_time[file_id] = time.time()
    
    elapsed = time.time() - _start_time[file_id]
    speed = current / 1024 / 1024 / elapsed if elapsed else 0
    remain = (total-current) / 1024 / 1024 / speed if speed else 0
    bar_len = 30
    filled = int(bar_len*current/total) if total else 0
    bar = '█'*filled + '-'*(bar_len-filled)
    pct = current*100/total if total else 0
    m, s = divmod(int(remain), 60)
    h, m = divmod(m, 60)
    
    if h > 0:
        eta = f"{h:02d}:{m:02d}:{s:02d}"
    else:
        eta = f"{m:02d}:{s:02d}"
        
    print(f"\r{label} |{bar}| {pct:5.1f}% ETA {eta} {speed:6.2f} MB/s", end='')

# ─── SUMMARY ───────────────────────────────────────────────────────────────────
def print_summary():
    """Print statistical summary of operations"""
    elapsed = time.time() - stats.start_time
    m, s = divmod(int(elapsed), 60)
    h, m = divmod(m, 60)
    if h > 0:
        time_str = f"{h:02d}:{m:02d}:{s:02d}"
    else:
        time_str = f"{m:02d}:{s:02d}"
    
    print(f"\n📊 Summary → ✅ {stats.downloaded} | ❌ {stats.failed} | " +
          f"⛔ {stats.skipped} | ⏱ {time_str}")

# ─── DISK SPACE MANAGEMENT ─────────────────────────────────────────────────────
def check_disk_space():
    """Check available disk space and clean up if needed"""
    if not download_folder.exists():
        download_folder.mkdir(parents=True)
    
    total, used, free = shutil.disk_usage(download_folder)
    free_gb = free / (1024**3)
    folder_size_gb = sum(f.stat().st_size for f in download_folder.glob('**/*') if f.is_file()) / (1024**3)
    
    logger.info(f"Disk space: {free_gb:.2f} GB free, folder using {folder_size_gb:.2f} GB")
    
    if folder_size_gb > max_disk_usage_gb:
        logger.warning(f"Folder size {folder_size_gb:.2f} GB exceeds limit of {max_disk_usage_gb} GB. Cleaning...")
        files = [(f, f.stat().st_mtime) for f in download_folder.glob('**/*') if f.is_file()]
        files.sort(key=lambda x: x[1])
        
        for file_path, _ in files:
            if folder_size_gb <= max_disk_usage_gb * 0.9:
                break
                
            size_gb = file_path.stat().st_size / (1024**3)
            logger.info(f"Deleting old file: {file_path} ({size_gb:.2f} GB)")
            try:
                file_path.unlink()
                folder_size_gb -= size_gb
            except Exception as e:
                logger.error(f"Failed to delete {file_path}: {e}")

# ─── PROGRESS TRACKING ─────────────────────────────────────────────────────────
def load_progress():
    """Load progress data from file"""
    if progress_file.exists():
        try:
            with open(progress_file, 'r') as f:
                data = json.load(f)
                logger.info(f"Loaded progress: {data}")
                return data
        except Exception as e:
            logger.error(f"Failed to load progress: {e}")
    
    return {"last_id": 0, "processed_ids": []}

def save_progress(last_id, processed_ids=None):
    """Save progress data to file"""
    if processed_ids is None:
        processed_ids = []
        
    data = {"last_id": last_id, "processed_ids": processed_ids}
    
    try:
        with open(progress_file, 'w') as f:
            json.dump(data, f)
        logger.info(f"Saved progress: {data}")
    except Exception as e:
        logger.error(f"Failed to save progress: {e}")

# ─── MAIN DOWNLOAD FUNCTION ────────────────────────────────────────────────────
async def download_message(msg):
    """Download a single message's video"""
    global stats
    
    # Check if it's a video file
    if not (msg.video and msg.file and msg.file.mime_type == "video/mp4"):
        logger.info(f"Skipping non-video message {msg.id}")
        stats.skipped += 1
        return False
        
    # Check file size
    if not (min_file_size <= msg.file.size <= max_file_size):
        logger.info(f"Skipping message {msg.id} - size out of bounds: {msg.file.size / 1024 / 1024:.2f} MB")
        stats.skipped += 1
        return False

    # Create clean filename
    clean_name = ''.join(c if c.isalnum() or c in '._- ' else '_' for c in msg.file.name or 'video.mp4')
    fname = f"{msg.id}_{clean_name}"
    fpath = download_folder / fname
    size_mb = msg.file.size / 1024 / 1024
    
    download_url = f"https://t.me/c/{str(source_group)[4:]}/{msg.id}"
    logger.info(f"Processing message {msg.id}: {clean_name} ({size_mb:.2f} MB)")
    print(f"\n⬇️ Downloading {fname} ({size_mb:.2f} MB)")
    print(f"🔗 {download_url}")

    # Reset skip flag
    stats.skip_current = False

    # Check disk space before download
    check_disk_space()

    # Download if not already present
    if not fpath.exists():
        try:
            await msg.download_media(
                file=str(fpath),
                progress_callback=lambda c, t: _progress(c, t, '⬇️ Download', str(msg.id))
            )
            stats.downloaded += 1
            logger.info(f"Downloaded {fname} ({size_mb:.2f} MB)")
            print(f"\n✅ Downloaded ({size_mb:.2f} MB)")
        except Exception as e:
            if "Skipped by user" in str(e):
                stats.skipped += 1
                stats.skip_current = False
                logger.info(f"Download skipped by user: {msg.id}")
                print("\n⏩ Download skipped by user.")
                return True
            
            logger.error(f"Download failed for message {msg.id}: {e}")
            print(f"\n❌ Download failed: {str(e)[:100]}...")
            stats.failed += 1
            return True
    else:
        logger.info(f"File already exists: {fpath}")
        print("📁 Already downloaded – skipping.")

    # Save progress
    progress_data = load_progress()
    progress_data["last_id"] = max(msg.id, progress_data.get("last_id", 0))
    if msg.id not in progress_data.get("processed_ids", []):
        progress_data["processed_ids"].append(msg.id)
    save_progress(progress_data["last_id"], progress_data.get("processed_ids", []))

    return True

# ─── MAIN PROGRAM ──────────────────────────────────────────────────────────────
async def main():
    """Main program loop"""
    global client, stats
    
    print("Made by Twisted Fate [fxp]")
    print("=" * 50)
    
    # Setup
    setup_signal_handlers()
    threading.Thread(target=key_listener, daemon=True).start()
    download_folder.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting downloader for source: {source_group}")
    print(f"📱 Telegram Video Downloader")
    print(f"📂 Source: {source_group}")
    print(f"💾 Download folder: {download_folder}")
    print(f"💡 Type 'ss' to skip current download")
    print("-" * 50)
    
    # Connect to Telegram
    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()
    logger.info("Connected to Telegram")
    
    # Load progress
    progress_data = load_progress()
    last_id = progress_data.get("last_id", 0)
    processed_ids = set(progress_data.get("processed_ids", []))
    
    logger.info(f"Resuming from message ID: {last_id}, {len(processed_ids)} already processed")
    print(f"▶️ Resuming from message ID: {last_id}")
    
    try:
        # Get messages
        it = client.iter_messages(source_group, reverse=True, min_id=last_id)
        processed_in_session = 0
        
        async for msg in it:
            # Skip already processed messages
            if msg.id in processed_ids:
                logger.info(f"Skipping already processed message: {msg.id}")
                continue
                
            # Download message
            processed = await download_message(msg)
            
            if processed:
                processed_in_session += 1
        
        logger.info(f"Processed {processed_in_session} messages in this session")
        print("\n🎉 All done! No more videos to download.")
        print_summary()
        
    except Exception as e:
        logger.error(f"Main loop error: {e}")
        print(f"\n❌ Error: {e}")
    
    finally:
        await client.disconnect()
        print("\nPress Enter to exit...")
        
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n💤 Program terminated by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        print(f"\n💥 Fatal error: {e}")