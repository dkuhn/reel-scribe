"""
Module to download Instagram content (such as Reels) using Instaloader and transcribe audio using Whisper CLI.
This module provides functionality to:
- Scrape liked reels URLs from a user's Instagram account.
- Download Instagram videos (Reels) using Instaloader.
- Transcribe audio o    if use_cpu:
        # Explicitly requested CPU mode
        cmd.extend(["--device", "cpu"])
        print("🐢 Using CPU (--cpu-only flag)")
    elif use_mps:
        # Experimental MPS mode (may fail due to sparse tensor support)
        cmd.extend(["--device", "mps"])
        print("🚀 Trying MPS (Apple Silicon GPU) - experimental, may crash")
    elif platform.system() == "Darwin":
        # Default to CPU on macOS due to MPS stability issues
        cmd.extend(["--device", "cpu"])
        print("🐢 Using CPU (default for macOS - use --mps to try GPU)")
    else:  # Linux/Windows
        cmd.extend(["--device", "cuda"])
        cmd.extend(["--fp16", "True"])  # FP16 is more stable on CUDA
        print("🚀 Using CUDA GPU acceleration")s using Whisper CLI.


Functions:
    get_liked_reels_urls(username, password):
        Scrapes URLs of liked reels from the user's Instagram account.

    download_instagram_video(url, download_dir='.'):
        Downloads an Instagram video given its URL to the specified directory.

    transcribe_with_whisper(input_file, output_dir, language="English", model="turbo", task="transcribe"):
        Transcribes audio/video files using Whisper CLI with GPU acceleration and optimized settings.

Usage:
    python download_instagram_reel.py --url <INSTAGRAM_URL> [--dir <DOWNLOAD_DIR>] [--scraping]
"""
import os
import sys
import argparse
import instaloader
import time
import subprocess
import re
import json
from datetime import datetime
from bs4 import BeautifulSoup

from dotenv import load_dotenv
import os





import time
import random
import os


def extract_saved_reel_urls(archive_path):
    """
    Extract saved Instagram reel URLs from the Instagram archive HTML file.
    
    Args:
        archive_path (str): Path to the Instagram archive directory 
                           (e.g., ~/Downloads/instagram-kuhnd-2025-05-31-7AsfObZL/)
    
    Returns:
        list: A list of Instagram reel URLs that were saved by the user.
    
    Example:
        urls = extract_saved_reel_urls("~/Downloads/instagram-kuhnd-2025-05-31-7AsfObZL/")
    """
    # Expand ~ to home directory
    archive_path = os.path.expanduser(archive_path)
    
    # Path to the saved posts HTML file
    saved_posts_html = os.path.join(archive_path, "your_instagram_activity", "saved", "saved_posts.html")
    
    if not os.path.exists(saved_posts_html):
        print(f"Error: Could not find saved_posts.html at {saved_posts_html}")
        return []
    
    print(f"Reading saved posts from: {saved_posts_html}")
    
    # Read the HTML file
    with open(saved_posts_html, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all links
    reel_urls = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        # Check if it's a reel URL
        if '/reel/' in href:
            # Clean up the URL (remove trailing slashes if any)
            clean_url = href.rstrip('/')
            if clean_url not in reel_urls:
                reel_urls.append(clean_url)
    
    print(f"Found {len(reel_urls)} saved reel URLs")
    return reel_urls


def load_processing_log(log_file='processed_reels.json'):
    """
    Load the processing log that tracks which reels have been successfully processed.
    
    Args:
        log_file (str): Path to the JSON log file.
    
    Returns:
        dict: Dictionary with shortcodes as keys and processing info as values.
    """
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Could not parse {log_file}, starting fresh")
            return {}
    return {}


def save_processing_log(log_data, log_file='processed_reels.json'):
    """
    Save the processing log to disk.
    
    Args:
        log_data (dict): Dictionary with processing information.
        log_file (str): Path to the JSON log file.
    """
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)


def is_reel_processed(shortcode, download_dir, log_data):
    """
    Check if a reel has been fully processed (downloaded + transcribed) or should be skipped.
    
    Args:
        shortcode (str): The Instagram post shortcode.
        download_dir (str): Base directory where reels are downloaded.
        log_data (dict): Processing log data.
    
    Returns:
        bool: True if the reel has been processed or should be skipped, False otherwise.
    """
    # Check log file first
    if shortcode in log_data:
        status = log_data[shortcode].get('status')
        
        # Statuses that should NEVER trigger an Instagram API call
        # These are terminal states - no point in re-downloading
        skip_statuses = {
            'failed_deleted',      # Post confirmed deleted/not found
            'deleted_by_insta',    # Post deleted by Instagram
            'no_speech_content',   # Successfully processed but no speech audio
        }
        
        if status in skip_statuses:
            return True
            
        if status == 'completed':
            # Verify files still exist
            target_dir = os.path.join(download_dir, shortcode)
            whisper_dir = os.path.join(target_dir, 'whisper')
            
            # Check if whisper directory exists and has transcript files
            if os.path.exists(whisper_dir):
                txt_files = [f for f in os.listdir(whisper_dir) if f.endswith('.txt')]
                if txt_files:
                    return True
            
            # If files don't exist, mark as incomplete in log
            print(f"Warning: {shortcode} marked as completed but files missing, will reprocess")
            return False
        
        # For failed_connection and failed_error, we may want to retry
        # so return False to allow reprocessing
    
    return False


def mark_reel_processed(shortcode, url, download_dir, log_data, log_file='processed_reels.json', status='completed', error_message=None):
    """
    Mark a reel as processed (successfully or unsuccessfully) in the log.
    
    Args:
        shortcode (str): The Instagram post shortcode.
        url (str): The reel URL.
        download_dir (str): Base directory where reel was downloaded.
        log_data (dict): Processing log data.
        log_file (str): Path to the JSON log file.
        status (str): Status of processing - 'completed', 'failed_deleted', 'failed_rate_limit', 'failed_error'
        error_message (str, optional): Error message if status is failed
    """
    log_data[shortcode] = {
        'url': url,
        'shortcode': shortcode,
        'status': status,
        'processed_date': datetime.now().isoformat(),
        'download_dir': os.path.join(download_dir, shortcode)
    }
    
    if error_message:
        log_data[shortcode]['error_message'] = error_message
    
    save_processing_log(log_data, log_file)


def download_instagram_video(url, download_dir='.'):
    """"
    
    Download an Instagram video (e.g., Reel) using Instaloader.

    Args:
        url (str): The full URL of the Instagram post or reel.
        download_dir (str, optional): Directory to save the downloaded video. Defaults to current directory.

    Returns:
        list: List of downloaded files (e.g., .mp4, .jpg, .txt) in the download directory.

    Example:
        download_instagram_video("https://www.instagram.com/reel/DJUSG1uuj-_/", "downloads")
    """
    if not url.startswith("https://www.instagram.com/"):
        # prepend the base URL if not provided
        url = "https://www.instagram.com/reel/" + url.lstrip('/')
        # check if URL exists
    if not url.endswith('/'):
        url += '/'
    
    print(url)
    # Instaloader expects post shortcode, not the full URL
    shortcode = url.rstrip('/').split('/')[-1]
    # Ensure files are downloaded to {download_dir}/{shortcode}
    target_dir = os.path.join(download_dir, shortcode)

    # Create the Instaloader instance with rate limit handling
    loader = instaloader.Instaloader(
        dirname_pattern=target_dir,
        filename_pattern="{date_utc}_UTC_{shortcode}",
        save_metadata=False,
        download_comments=False,
        sleep=True,  # Sleep between requests to avoid rate limits
        max_connection_attempts=3,  # Retry failed connections
        request_timeout=300  # Longer timeout for slow connections
    )
    
    # Get Instagram credentials from environment variables
    USERNAME = os.environ.get("IG_USERNAME")
    PASSWORD = os.environ.get("IG_PASSWORD")
    
    # Attempt to load session or log in
    if USERNAME and PASSWORD:
        session_file = os.path.join(os.path.expanduser("~"), ".instaloader-session")
        try:
            # Load session from file if it exists, to avoid repeated logins
            loader.load_session_from_file(USERNAME, session_file)
            print(f"✓ Loaded existing session for {USERNAME}")
        except FileNotFoundError:
            # If no session file, perform a fresh login
            print(f"🔐 Logging in as {USERNAME}...")
            try:
                loader.login(USERNAME, PASSWORD)
                # Save the session for future use
                loader.save_session_to_file(session_file)
                print(f"✓ Logged in and saved session")
            except Exception as e:
                print(f"⚠️  Login failed: {e}")
                print("Continuing without login (some content may not be accessible)")
    else:
        print("⚠️  No Instagram credentials found in environment variables")
        print("Set IG_USERNAME and IG_PASSWORD to download private content")
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    else:
        print(f"Directory {target_dir} already exists. Skipping download.")
        return []
    
    try:
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        loader.download_post(post, target=target_dir)

        if post.caption:
            print(f"Caption: {post.caption}")
            print(f"Tags: {post.caption_hashtags}")

        print(f"Downloaded files to {target_dir} for post {shortcode}")

        # Only collect files for this shortcode
        downloaded_files = []
        for fname in os.listdir(target_dir):
            if (
                fname.endswith(('.mp4', '.jpg', '.txt')) and
                shortcode in fname
            ):
                downloaded_files.append(os.path.join(target_dir, fname))
        print(f"Downloaded to {target_dir}")
        return downloaded_files
    
    except instaloader.exceptions.QueryReturnedNotFoundException:
        # Post has been deleted or is unavailable
        print(f"❌ Post not found: {shortcode} (likely deleted)")
        return None  # Return None to indicate deleted post
    except instaloader.exceptions.ConnectionException as e:
        if "401" in str(e) or "Please wait" in str(e):
            print(f"⚠️  Rate limited by Instagram: {e}")
            print("💡 Instagram is blocking requests. Wait 5-10 minutes and try again.")
            print("💡 Consider processing your archive instead: --archive <path>")
            return "rate_limited"  # Return special value for rate limit
        else:
            print(f"❌ Connection error: {e}")
            return "connection_error"
    except Exception as e:
        error_msg = str(e)
        if "Fetching Post metadata failed" in error_msg or "not find" in error_msg.lower():
            print(f"❌ Post not found or deleted: {shortcode}")
            return None  # Return None to indicate deleted post
        else:
            print(f"❌ Error downloading {shortcode}: {e}")
            return "error"
    


def transcribe_with_whisper(input_file, output_dir, language=None, model="turbo", task="transcribe", use_cpu=False, use_mps=False):
    """
    Call the Whisper CLI to transcribe an audio/video file with optimized settings for speed.

    Args:
        input_file (str): Path to the input audio/video file.
        language (str, optional): Language to use for transcription. If None, auto-detects language.
        model (str): Whisper model to use (default: "turbo" - fastest large model).
        task (str): Task for Whisper (default: "transcribe").
        use_cpu (bool): Force CPU-only mode (more stable but slower).
        use_mps (bool): Try MPS GPU on Apple Silicon (experimental, may fail).

    Returns:
        tuple: (output_file_path, return_code) from the Whisper CLI process.
        
    Performance Optimizations:
        - Automatic language detection for multilingual content (English, German, etc.)
        - Uses GPU (CUDA/MPS) if available via --device flag
        - Only outputs TXT format (skips VTT, SRT, JSON)
        - Disables condition_on_previous_text for faster processing on short clips
        - Limited to 4 CPU threads to reduce fan noise on MacBooks
    """
    
    cmd = [
        "whisper",
        input_file,
        "--model", model,
        "--task", task,
        "--output_dir", output_dir,
        "--output_format", "txt",  # Only generate TXT, skip other formats
        "--condition_on_previous_text", "False",  # Faster for short clips like reels
        "--threads", "4"  # Limit to 4 threads to reduce CPU load and fan noise
    ]
    
    # Add language parameter only if specified, otherwise let Whisper auto-detect
    if language:
        cmd.extend(["--language", language])
        print(f"🌍 Using specified language: {language}")
    else:
        print(f"🌍 Auto-detecting language (supports English, German, and 90+ languages)")
    
    # Try to use GPU acceleration
    # For M1/M2/M3 Macs: Use MPS (Metal Performance Shaders) for GPU acceleration
    # For CUDA GPUs: Use CUDA
    # Will automatically fall back to CPU if GPU is unavailable
    import platform
    
    # Note: FP16 can cause issues with MPS on some PyTorch versions
    # We'll enable it conditionally based on device
    # For quieter fans: limit threads to 4 and avoid aggressive batch processing
    if use_cpu:
        # Explicitly requested CPU mode with limited threads
        cmd.extend(["--device", "cpu"])
        print("🐢 Using CPU (--cpu-only flag) with 4 threads for quieter operation")
    elif use_mps:
        # Experimental MPS mode (may fail due to sparse tensor support)
        cmd.extend(["--device", "mps"])
        print("🚀 Trying MPS (Apple Silicon GPU) - experimental, may crash")
    elif platform.system() == "Darwin":
        # Default to CPU on macOS due to MPS stability issues
        # Limited threads to reduce fan noise
        cmd.extend(["--device", "cpu"])
        print("🐢 Using CPU (default for macOS - 4 threads for quieter fans)")
    else:  # Linux/Windows
        cmd.extend(["--device", "cuda"])
        cmd.extend(["--fp16", "True"])  # FP16 is more stable on CUDA
        print("🚀 Using CUDA GPU acceleration")
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Check for errors and print them
    if result.returncode != 0:
        print(f"❌ Whisper failed with return code {result.returncode}")
        if result.stderr:
            print(f"Error output: {result.stderr[-500:]}")  # Last 500 chars
        if result.stdout:
            print(f"Standard output: {result.stdout[-500:]}")  # Last 500 chars
    
    outputfile = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(input_file))[0]}.txt")
    return (outputfile, result.returncode)


def tags_for_transcript(input_file, max_tags=10):
    """
    Generate tags for the transcript based on the content.
    
    Args:
        input_file (str): Path to the input audio/video file.
        max_tags (int, optional): Maximum number of tags to generate. Defaults to 10.

    Returns:
        list: A list of tags derived from the transcript.
    """
    # read whisper transcript file
    f = open(input_file, 'r').readlines()
    
    print(f)
    import yake
    kw_extractor = yake.KeywordExtractor(top=max_tags, stopwords=None, lan="en", n=1)
    keywords = kw_extractor.extract_keywords(f)
    tags = [kw for kw, score in keywords]
    print(tags)
    for w,s in yake.KeywordExtractor(top=8, stopwords=None, lan="en", n=3).extract_keywords(f): 
        # print nicely with 2 digits after the comma
    
        print (w,"{:.2f}".format(s))
   
    return tags


def has_required_files(shortcode_dir):
    # Verify mp4, jpg, post txt, and whisper txt exist
    try:
        files = os.listdir(shortcode_dir)
    except Exception:
        return False
    mp4_ok = any(f.endswith('.mp4') for f in files)
    jpg_ok = any(f.endswith('.jpg') for f in files)
    post_txt_ok = any(f.endswith('.txt') and 'UTC_' in f and shortcode_dir.split(os.sep)[-1] in f for f in files)
    whisper_dir = os.path.join(shortcode_dir, 'whisper')
    whisper_txt_ok = False
    if os.path.isdir(whisper_dir):
        whisper_txt_ok = any(f.endswith('.txt') for f in os.listdir(whisper_dir))
    return mp4_ok and jpg_ok and post_txt_ok and whisper_txt_ok


def cleanup_empty_directories(base_dir):
    """
    Recursively scan through a directory and delete empty subdirectories.
    
    Args:
        base_dir (str): Base directory to scan for empty subdirectories.
    
    Returns:
        int: Number of empty directories deleted.
    """
    base_dir = os.path.expanduser(base_dir)
    
    if not os.path.exists(base_dir):
        print(f"Directory does not exist: {base_dir}")
        return 0
    
    deleted_count = 0
    
    # Walk through directory tree bottom-up to handle nested empty dirs
    for root, dirs, files in os.walk(base_dir, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                # Check if directory is empty (no files and no subdirectories)
                if not os.listdir(dir_path):
                    print(f"Deleting empty directory: {dir_path}")
                    os.rmdir(dir_path)
                    deleted_count += 1
            except Exception as e:
                print(f"Error checking/deleting {dir_path}: {e}")
    
    return deleted_count


def process_missing_transcriptions(base_dir, use_cpu=False, use_mps=False):
    """
    Scan through all subdirectories and transcribe videos that don't have whisper output.
    
    Args:
        base_dir (str): Base directory containing reel subdirectories.
        use_cpu (bool): Force CPU-only mode for transcription.
        use_mps (bool): Try MPS GPU acceleration (experimental).
    
    Returns:
        tuple: (processed_count, failed_count)
    """
    base_dir = os.path.expanduser(base_dir)
    
    if not os.path.exists(base_dir):
        print(f"Directory does not exist: {base_dir}")
        return 0, 0
    
    log_file = os.path.join(base_dir, 'processed_reels.json')
    processing_log = load_processing_log(log_file)
    
    processed = 0
    failed = 0
    
    # Scan all subdirectories
    subdirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    
    print(f"\n{'='*60}")
    print(f"Scanning {len(subdirs)} subdirectories for missing transcriptions")
    print(f"{'='*60}\n")
    
    for idx, shortcode in enumerate(subdirs, 1):
        subdir = os.path.join(base_dir, shortcode)
        whisper_dir = os.path.join(subdir, 'whisper')
        
        # First check if this shortcode should be skipped based on log status
        if shortcode in processing_log:
            status = processing_log[shortcode].get('status')
            # Skip entries that are already fully processed or known to have no speech
            skip_statuses = {
                'no_speech_content',   # Already processed, no speech detected
                'failed_deleted',      # Post was deleted, no files to transcribe
                'deleted_by_insta',    # Post deleted by Instagram
            }
            if status in skip_statuses:
                print(f"[{idx}/{len(subdirs)}] {shortcode} - skipping (status: {status})")
                continue
        
        # Check if whisper directory exists and has transcript files
        needs_transcription = True
        if os.path.exists(whisper_dir):
            txt_files = [f for f in os.listdir(whisper_dir) if f.endswith('.txt')]
            if txt_files:
                needs_transcription = False
        
        if needs_transcription:
            print(f"\n[{idx}/{len(subdirs)}] Processing {shortcode} (missing whisper output)")
            
            # Find MP4 file in the subdirectory
            try:
                files = os.listdir(subdir)
                mp4_files = [f for f in files if f.endswith('.mp4')]
                
                if not mp4_files:
                    print(f"⚠️  No MP4 file found in {shortcode}, skipping")
                    failed += 1
                    continue
                
                mp4_file = os.path.join(subdir, mp4_files[0])
                output_dir = os.path.join(subdir, 'whisper')
                
                print(f"Transcribing {mp4_file}...")
                transcript_file, ret_code = transcribe_with_whisper(
                    mp4_file, 
                    output_dir, 
                    use_cpu=use_cpu, 
                    use_mps=use_mps
                )
                
                if ret_code == 0:
                    # Check if whisper actually produced output (some reels have no speech)
                    if not os.path.exists(transcript_file) or os.path.getsize(transcript_file) == 0:
                        # No speech content detected - create dummy file
                        print(f"🔇 No speech detected in {shortcode}, creating dummy whisper output")
                        dummy_file = os.path.join(output_dir, "whisper-output.txt")
                        with open(dummy_file, "w", encoding="utf-8") as f:
                            f.write("no speech audio content")
                        
                        # Create empty tags file
                        tags_file = os.path.join(subdir, f"{shortcode}.tags.txt")
                        with open(tags_file, "w", encoding="utf-8") as tf:
                            tf.write("")
                        print(f"Saved empty tags to: {tags_file}")
                        
                        # Mark as processed with no_speech_content status
                        url = f"https://www.instagram.com/reel/{shortcode}"
                        mark_reel_processed(shortcode, url, base_dir, processing_log, log_file, 
                                          status='no_speech_content')
                        processed += 1
                        print(f"✓ Marked {shortcode} as no_speech_content")
                    else:
                        # Normal case - speech was detected and transcribed
                        # Generate and save tags
                        tags = tags_for_transcript(transcript_file)
                        print(f"Generated tags: {tags}")
                        
                        try:
                            tags_file = os.path.join(subdir, f"{shortcode}.tags.txt")
                            with open(tags_file, "w", encoding="utf-8") as tf:
                                if tags:
                                    tf.write("\n".join(tags))
                                else:
                                    tf.write("")
                            print(f"Saved tags to: {tags_file}")
                        except Exception as e:
                            print(f"Failed to write tags file: {e}")
                        
                        # Mark as processed in the log
                        url = f"https://www.instagram.com/reel/{shortcode}"
                        mark_reel_processed(shortcode, url, base_dir, processing_log, log_file)
                        processed += 1
                        print(f"✓ Marked {shortcode} as processed")
                else:
                    print(f"❌ Transcription failed with code {ret_code}")
                    failed += 1
                    
            except Exception as e:
                print(f"❌ Error processing {shortcode}: {e}")
                failed += 1
        else:
            print(f"[{idx}/{len(subdirs)}] {shortcode} - whisper output exists, skipping")
    
    return processed, failed

# ...existing code...
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Download Instagram Reel Videos")
    parser.add_argument('--url', help='Full URL of the Instagram post or reel', default=None)
    parser.add_argument('--dir', default=os.path.expanduser('~/reel_archive'), help='Directory to save the downloaded video (default: ~/reel_archive)')
    parser.add_argument('--scraping', default=False, help='Scrape your reels)', action='store_true')
    parser.add_argument('--archive', help='Path to Instagram archive directory to process all saved reels', default=None)
    parser.add_argument('--cpu-only', action='store_true', help='Force CPU-only transcription (more stable, but slower)')
    parser.add_argument('--mps', action='store_true', help='Try MPS (Apple Silicon GPU) acceleration (experimental, may fail)')
    parser.add_argument('--cleanup', action='store_true', help='Clean up empty subdirectories in the archive directory')
    parser.add_argument('--transcribe-missing', action='store_true', help='Transcribe all subdirectories missing whisper output')
    parser.add_argument('--start-idx', type=int, default=1, help='Start processing from this index (1-based, default: 1)')
    args = parser.parse_args()
    print(args)
   
    load_dotenv()
    
    # Handle cleanup if --cleanup flag is provided
    if args.cleanup:
        print(f"\n{'='*60}")
        print(f"Cleaning up empty directories in: {args.dir}")
        print(f"{'='*60}\n")
        deleted = cleanup_empty_directories(args.dir)
        print(f"\n{'='*60}")
        print(f"Cleanup complete! Deleted {deleted} empty directories.")
        print(f"{'='*60}\n")
        if not args.archive and not args.url:
            # If only cleanup was requested, exit
            exit(0)
    
    if args.scraping is True:
        print("Note: Direct scraping of liked reels is no longer supported.")
        print("Please use --archive flag with your Instagram data export file.")

    # Handle transcribe-missing if --transcribe-missing flag is provided
    if args.transcribe_missing:
        print(f"\n{'='*60}")
        print(f"Processing missing transcriptions in: {args.dir}")
        print(f"{'='*60}\n")
        processed, failed = process_missing_transcriptions(args.dir, use_cpu=args.cpu_only, use_mps=args.mps)
        print(f"\n{'='*60}")
        print(f"Transcription processing complete!")
        print(f"Successfully processed: {processed}")
        print(f"Failed: {failed}")
        print(f"{'='*60}\n")
        if not args.archive and not args.url:
            # If only transcribe-missing was requested, exit
            exit(0)

    # Process archive if --archive flag is provided
    if args.archive:
        print(f"Processing archive from: {args.archive}")
        reel_urls = extract_saved_reel_urls(args.archive)
        
        # Load processing log to track what we've already done
        log_file = os.path.join(args.dir, 'processed_reels.json')
        processing_log = load_processing_log(log_file)
        
        # Apply start index filter
        total_reels = len(reel_urls)
        start_idx = max(1, args.start_idx)  # Ensure at least 1
        if start_idx > 1:
            print(f"\n⏩ Starting from index {start_idx} (skipping first {start_idx - 1} reels)")
            reel_urls = reel_urls[start_idx - 1:]  # Convert to 0-based index
        
        print(f"\n{'='*60}")
        print(f"Starting batch download of {len(reel_urls)} reels")
        if start_idx > 1:
            print(f"Starting from reel #{start_idx} of {total_reels} in the archive")
        print(f"Previously processed: {len(processing_log)} reels")
        print(f"{'='*60}\n")
        
        skipped = 0
        processed = 0
        failed = 0
        
        for idx, url in enumerate(reel_urls, start_idx):
            try:
                # Extract shortcode from URL
                shortcode = url.rstrip('/').split('/')[-1]
                target_dir = os.path.join(args.dir, shortcode)
                
                # Check if already processed or should be skipped
                if shortcode in processing_log:
                    status = processing_log[shortcode].get('status')
                    
                    # Statuses that should NEVER trigger an Instagram API call
                    skip_statuses = {
                        'failed_deleted',      # Post confirmed deleted/not found
                        'deleted_by_insta',    # Post deleted by Instagram
                        'no_speech_content',   # Successfully processed but no speech audio
                    }
                    
                    if status in skip_statuses:
                        print(f"[{idx}/{len(reel_urls)}] Skipping {shortcode} (status: {status})")
                        skipped += 1
                        continue
                    
                    if status == 'completed' and has_required_files(target_dir):
                        print(f"[{idx}/{len(reel_urls)}] Skipping {shortcode} (already processed and files present)")
                        skipped += 1
                        continue
                    elif status == 'completed':
                        # Completed but files missing - need to redownload
                        print(f"[{idx}/{len(reel_urls)}] {shortcode} marked completed but missing files, reprocessing...")
                        if os.path.exists(target_dir):
                            import shutil
                            print(f"Removing incomplete directory: {target_dir}")
                            shutil.rmtree(target_dir)
                    # For failed_connection and failed_error, allow retry
                    elif status in ('failed_connection', 'failed_error'):
                        print(f"[{idx}/{len(reel_urls)}] {shortcode} had previous error ({status}), retrying...")
                        if os.path.exists(target_dir):
                            import shutil
                            shutil.rmtree(target_dir)
                elif os.path.exists(target_dir):
                    # Directory exists but not in log - probably an incomplete download
                    print(f"[{idx}/{len(reel_urls)}] {shortcode} directory exists but not tracked, cleaning up...")
                    import shutil
                    shutil.rmtree(target_dir)
                
                print(f"\n[{idx}/{len(reel_urls)}] Processing: {url}")
                downloaded_files = download_instagram_video(url, args.dir)
                
                # Handle different return values
                if downloaded_files is None:
                    # Post was deleted or not found
                    print(f"Marking {shortcode} as deleted")
                    mark_reel_processed(shortcode, url, args.dir, processing_log, log_file, 
                                      status='failed_deleted', 
                                      error_message='Post not found or has been deleted')
                    failed += 1
                    continue
                elif downloaded_files == "rate_limited":
                    # Rate limited - don't mark in log, will retry next time
                    print(f"⚠️  Skipping {shortcode} due to rate limit")
                    failed += 1
                    continue
                elif downloaded_files == "connection_error":
                    # Connection error
                    print(f"Marking {shortcode} as connection error")
                    mark_reel_processed(shortcode, url, args.dir, processing_log, log_file,
                                      status='failed_connection',
                                      error_message='Connection error during download')
                    failed += 1
                    continue
                elif downloaded_files == "error":
                    # General error
                    print(f"Marking {shortcode} as failed")
                    mark_reel_processed(shortcode, url, args.dir, processing_log, log_file,
                                      status='failed_error',
                                      error_message='Unknown error during download')
                    failed += 1
                    continue
                elif not downloaded_files:
                    print(f"Skipped (already exists or failed)")
                    skipped += 1
                    continue
                
                # Find mp4 in downloaded_files
                mp4_file = next((f for f in downloaded_files if f.endswith('.mp4')), None)
                if mp4_file:
                    print(f"Found MP4 file: {mp4_file}")
                    # Remove filename from mp4_file path to get output directory
                    output_dir = os.path.dirname(mp4_file) + "/whisper/"       
                    print(f"Transcribing {mp4_file}...")
                    transcript_file, ret_code = transcribe_with_whisper(mp4_file, output_dir, use_cpu=args.cpu_only, use_mps=args.mps)
                    if ret_code == 0:
                        tags = tags_for_transcript(transcript_file)
                        print(f"Generated tags: {tags}")
                        # Write tags to <shortcode>.tags.txt in the reel directory
                        try:
                            tags_file = os.path.join(os.path.dirname(mp4_file), f"{shortcode}.tags.txt")
                            with open(tags_file, "w", encoding="utf-8") as tf:
                                if tags:
                                    tf.write("\n".join(tags))
                                else:
                                    tf.write("")  # create empty tags file
                            print(f"Saved tags to: {tags_file}")
                        except Exception as e:
                            print(f"Failed to write tags file: {e}")
                        # Mark as successfully processed
                        mark_reel_processed(shortcode, url, args.dir, processing_log, log_file)
                        processed += 1
                        print(f"✓ Marked {shortcode} as processed")
                    else:
                        print(f"Transcription failed with code {ret_code}")
                        failed += 1
                else:
                    print("No MP4 file found in downloaded files.")
                    failed += 1
                    
            except Exception as e:
                print(f"Error processing {url}: {e}")
                failed += 1
                continue
        
        print(f"\n{'='*60}")
        print(f"Batch processing complete!")
        print(f"Total reels in archive: {len(reel_urls)}")
        print(f"Successfully processed: {processed}")
        print(f"Skipped (already done): {skipped}")
        print(f"Failed: {failed}")
        print(f"{'='*60}\n")
        
    # Process single URL if --url flag is provided
    elif args.url:
        downloaded_files = download_instagram_video(args.url, args.dir)
        
        # Handle different return values
        if downloaded_files is None:
            print("❌ Post was deleted or not found")
            sys.exit(1)
        elif downloaded_files == "rate_limited":
            print("⚠️  Rate limited by Instagram. Please wait a few minutes and try again.")
            sys.exit(1)
        elif downloaded_files == "connection_error":
            print("❌ Connection error during download")
            sys.exit(1)
        elif downloaded_files == "error":
            print("❌ Unknown error during download")
            sys.exit(1)
        elif not downloaded_files:
            print("❌ Download failed or returned no files")
            sys.exit(1)
        
        """    # Example output:
        downloaded_files = ['/tmp/DHrEj0JufKf/2025-03-26_18-43-13_UTC_DHrEj0JufKf.mp4',
                            '/tmp/DHrEj0JufKf/2025-03-26_18-43-13_UTC_DHrEj0JufKf.jpg',
                            '/tmp/DHrEj0JufKf/2025-03-26_18-43-13_UTC_DHrEj0JufKf.txt']
        """                    
        print(downloaded_files)
        # find mp4 in downloaded_files
        mp4_file = next((f for f in downloaded_files if f.endswith('.mp4')), None)
        if mp4_file:
            print(f"Found MP4 file: {mp4_file}")
            # remove filename from mp4_file path to get output directory
            output_dir = os.path.dirname(mp4_file) + "/whisper/"       
            print(f"Converting {mp4_file} to MP3 format...")
            transcript_file, ret_code = transcribe_with_whisper(mp4_file, output_dir, use_cpu=args.cpu_only, use_mps=args.mps)
            tags=tags_for_transcript(transcript_file)
        else:
            print("No MP4 file found in downloaded files. Skipping transcription and conversion.")
    else:
        parser.print_help()
        print("\nError: You must specify either --url or --archive")