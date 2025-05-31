"""
Module to download Instagram videos (such as Reels) using Instaloader.

Functions:
    download_instagram_video(url, download_dir='.'):
        Downloads an Instagram video given its URL to the specified directory.

Usage:
    python Untitled-1.py --url <INSTAGRAM_URL> [--dir <DOWNLOAD_DIR>]
"""
import os
import argparse
import instaloader
import time
import subprocess

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from dotenv import load_dotenv
import os




def get_liked_reels_urls(username, password):
    driver = webdriver.Chrome()
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(3)

    # Log in
    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password + Keys.RETURN)
    time.sleep(5)

    # Go to your profile
    driver.get(f"https://www.instagram.com/{username}/")
    time.sleep(3)

    # Instagram does not have a direct "liked reels" page on web.
    # You may need to navigate to "Saved" or "Your activity" and filter for Reels.
    # This part is highly dependent on Instagram's current UI.
    # Example: Open "Saved" tab (if you save liked Reels)
    driver.get(f"https://www.instagram.com/{username}/saved/")
    time.sleep(3)

    # Scroll and collect Reel URLs
    reel_urls = set()
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(10):  # Adjust range for more scrolling
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            href = link.get_attribute("href")
            if "/reel/" in href:
                reel_urls.add(href)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    driver.quit()
    return list(reel_urls)









def convert_mp4_to_mp3(mp4_file, mp3_file=None):
    """
    Convert an MP4 file to MP3 format.

    Args:
        mp4_file (str): Path to the input MP4 file.
        mp3_file (str, optional): Path to save the output MP3 file. Defaults to None, which will use the same name as mp4_file but with .mp3 extension.

    Returns:
        str: Path to the converted MP3 file.
    """
    from pydub import AudioSegment
    import os

    if mp3_file is None:
        mp3_file = mp4_file.rsplit('.', 1)[0] + '.mp3'

    audio = AudioSegment.from_file(mp4_file, format='mp4')
    audio.export(mp3_file, format='mp3')
    
    return mp3_file


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

    loader = instaloader.Instaloader(
        dirname_pattern=target_dir,  # <-- Use target_dir here!
        filename_pattern="{date_utc}_UTC_{shortcode}",
        save_metadata=False,
        download_comments=False
    )
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    else:
        print(f"Directory {target_dir} already exists. Skipping download.")
        return []
    
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


def transcribe_with_whisper(input_file, output_dir, language="English", model="turbo", task="transcribe"):
    """
    Call the Whisper CLI to transcribe an audio/video file.

    Args:
        input_file (str): Path to the input audio/video file.
        language (str): Language to use for transcription.
        model (str): Whisper model to use.
        task (str): Task for Whisper (default: "transcribe").

    Returns:
        int: The return code from the Whisper CLI process.
    """
    
    cmd = [
        "whisper",
        "--language", language,
        "--model", model,
        "--task", task,
        input_file,
        "--output_dir", output_dir
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode




if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Download Instagram Reel Videos")
    parser.add_argument('--url', help='Full URL of the Instagram post or reel', default="DJUSG1uuj-_")
    parser.add_argument('--dir', default='/tmp/', help='Directory to save the downloaded video (default: current directory)')
    parser.add_argument('--scraping', default=False, help='Scrape your reels)', action='store_true')
    args = parser.parse_args()
    load_dotenv()
    username = os.getenv("IG_USERNAME")
    password = os.getenv("IG_PASSWORD")
    print(username, password)
    print(args)
   
    if args.scraping is True:

   
        get_liked_reels_urls(username, password)  


    downloaded_files = download_instagram_video(args.url, args.dir)
    """"
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
        transcribe_with_whisper(mp4_file,output_dir)
    else:
        print("No MP4 file found in downloaded files. Skipping transcription and conversion.")