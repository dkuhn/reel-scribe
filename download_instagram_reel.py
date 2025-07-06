"""
Module to download Instagram content (such as Reels) using Instaloader and transcribe audio using Whisper CLI.
This module provides functionality to:
- Scrape liked reels URLs from a user's Instagram account.
- Download Instagram videos (Reels) using Instaloader.
- Transcribe audio or video files using Whisper CLI.


Functions:
    get_liked_reels_urls(username, password):
        Scrapes URLs of liked reels from the user's Instagram account.

    download_instagram_video(url, download_dir='.'):
        Downloads an Instagram video given its URL to the specified directory.

    transcribe_with_whisper(input_file, output_dir, language="English", model="turbo", task="transcribe"):
        Transcribes audio/video files using Whisper CLI.

Usage:
    python download_instagram_reel.py --url <INSTAGRAM_URL> [--dir <DOWNLOAD_DIR>] [--scraping]
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





import time
import random
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# Optional: Import selenium-stealth for more advanced bot evasion
try:
    from selenium_stealth import stealth
    STEALTH_ENABLED = True
    print("selenium-stealth found. Will attempt to use it.")
except ImportError:
    STEALTH_ENABLED = False
    print("selenium-stealth not found. Install with: pip install selenium-stealth")


def type_slowly(element, text):
    """Types text into an element character by character with random delays."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.2)) # Random delay between characters

def get_liked_reel_links(username, password, num_reels_to_collect=24):
    """
    Collects a specified number of Instagram reel links from the user's liked posts.

    Args:
        username (str): The Instagram username.
        password (str): The Instagram password.
        num_reels_to_collect (int): The maximum number of reel links to collect.

    Returns:
        list: A list of unique URLs to Instagram reels that the user has liked, up to the specified limit.
    """
    chrome_options = ChromeOptions()
    # Uncomment the line below to see the browser UI for debugging
    chrome_options.add_argument("--headless=new") # Use "new" headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    # --- IMPORTANT: Persistent User Data Directory ---
    # This will store cookies, login session, etc.
    # Create a directory for your profile data if it doesn't exist
    user_data_dir = os.path.join(os.getcwd(), "selenium_profile")
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
    chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    # chrome_options.add_argument(f"profile-directory=Default") # Use default profile within user-data-dir


    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

    # --- Apply selenium-stealth if installed ---
    if STEALTH_ENABLED:
        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32", # Mimic a Windows user (or "MacIntel" for macOS)
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )
        print("Applied stealth options.")


    reel_links = set()
    wait = WebDriverWait(driver, 30) # Increased timeout for robustness

    try:
        driver.get("https://www.instagram.com/accounts/login/")
        print("Navigated to login page.")
        time.sleep(random.uniform(2, 4)) # Initial random delay

        # --- Handle Cookie Consent Page ---
        try:
            # More specific XPath for the "Allow all cookies" button
            allow_cookies_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Allow all cookies']")), 10)
            allow_cookies_button.click()
            print("Accepted cookies.")
            time.sleep(random.uniform(2, 3))
        except TimeoutException:
            print("Cookie consent button did not appear within 10s timeout, or was already handled.")
        except NoSuchElementException:
            print("Cookie consent button not found by specified XPATH.")
        # --- End Cookie Consent Handling ---

        # Check if already logged in (by checking for elements on the main feed page)
        # If the URL is not the login page, we might be logged in.
        if "login" not in driver.current_url:
            print("Already logged in, skipping login process.")
        else:
            wait.until(EC.presence_of_element_located((By.NAME, "username")))
            username_input = driver.find_element(By.NAME, "username")
            password_input = driver.find_element(By.NAME, "password")

            print("Attempting to input credentials...")
            type_slowly(username_input, username)
            time.sleep(random.uniform(0.5, 1.5)) # Pause after username
            type_slowly(password_input, password)
            time.sleep(random.uniform(1, 2)) # Pause after password

            password_input.send_keys(Keys.RETURN)
            print("Login form submitted.")

            # --- Wait for successful login or specific error ---
            # Wait for elements on the home feed or profile page to appear, NOT just URL change from login
            try:
                # Common elements on the home page after successful login
                wait.until(EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//a[@href='/']//span[@aria-label='Home']")), # Home icon
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/explore/')]//span[@aria-label='Explore']")), # Explore icon
                    EC.url_contains(username) # If it redirects to your profile immediately
                ), 15) # Wait up to 15 seconds for these elements
                print("Login successful.")
                time.sleep(random.uniform(2, 4)) # Post-login delay
            except TimeoutException:
                print("Login failed or took too long. Still on login page or redirected back.")
                if "login" in driver.current_url:
                    print("Error: Script is stuck on the login page. Check credentials or bot detection.")
                    # Add more debugging info here:
                    # driver.save_screenshot("login_failure.png")
                    # print(driver.page_source) # Print page source for manual inspection
                return [] # Exit if login fails and returns to login page

        # Navigate to liked posts page
        driver.get("https://www.instagram.com/your_activity/interactions/likes/")
        print("Navigated to liked posts page.")
        wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='grid']")))
        time.sleep(random.uniform(3, 5)) # Give more time for the grid to load

        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 10

        processed_post_ids = set()

        while len(reel_links) < num_reels_to_collect and scroll_attempts < max_scroll_attempts:
            current_all_post_elements = driver.find_elements(By.XPATH, "//div[@role='grid']//div[@role='button' and @aria-label='Image with button']")
            print(f"Found {len(current_all_post_elements)} post elements in the current view.")

            if not current_all_post_elements and scroll_attempts == 0:
                print("No post elements found with the refined XPath. Double-check browser inspection.")
                break

            new_elements_processed_in_this_scroll = False
            for post_element in current_all_post_elements:
                if len(reel_links) >= num_reels_to_collect:
                    break

                # Get a unique identifier for the post element
                # Using outerHTML as a last resort, better to find a stable ID or href
                post_unique_id = post_element.get_attribute("outerHTML")[:100] # Use part of HTML as a temp ID
                if post_unique_id in processed_post_ids:
                    continue
                processed_post_ids.add(post_unique_id)
                new_elements_processed_in_this_scroll = True

                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", post_element)
                    time.sleep(random.uniform(0.1, 0.3))

                    is_reel_thumbnail = False
                    try:
                        reel_icon_check = post_element.find_element(By.XPATH, ".//div[@data-bloks-name='ig.components.Icon' and contains(@style, 'reels__filled__')]")
                        is_reel_thumbnail = True
                    except NoSuchElementException:
                        pass

                    if not is_reel_thumbnail:
                        continue

                    print(f"Clicking a reel thumbnail. Collected: {len(reel_links)}/{num_reels_to_collect})")
                    post_element.click()
                    time.sleep(random.uniform(3, 5))

                    current_post_url = driver.current_url
                    if "/reel/" in current_post_url:
                        cleaned_url = current_post_url.split('?')[0]
                        if cleaned_url not in reel_links:
                            reel_links.add(cleaned_url)
                            print(f"Successfully captured reel link: {cleaned_url} (Total: {len(reel_links)}/{num_reels_to_collect})")
                    else:
                        print(f"Opened post is not a reel (URL: {current_post_url}).")

                    if current_post_url != "https://www.instagram.com/your_activity/interactions/likes/":
                        driver.back()
                        print("Navigated back to likes page.")
                        wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='grid']")))
                        time.sleep(random.uniform(2, 3))
                    else:
                        try:
                            # Try to find a specific link within the modal for the actual reel permalink, if the URL didn't change.
                            modal_reel_link = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//a[contains(@href, '/reel/')]")), 5)
                            href_from_modal = modal_reel_link.get_attribute("href")
                            if href_from_modal:
                                cleaned_url = href_from_modal.split('?')[0]
                                if cleaned_url not in reel_links:
                                    reel_links.add(cleaned_url)
                                    print(f"Captured reel link from modal: {cleaned_url} (Total: {len(reel_links)}/{num_reels_to_collect})")
                        except TimeoutException:
                            print("No reel link found directly in modal or modal didn't fully load.")
                        except NoSuchElementException:
                             print("No reel link found directly in modal.")
                        
                        try:
                            driver.find_element(By.CSS_SELECTOR, "body").send_keys(Keys.ESCAPE)
                            print("Closed modal via ESC.")
                            wait.until(EC.invisibility_of_element_located((By.XPATH, "//div[@role='dialog']")))
                            time.sleep(random.uniform(1, 2))
                        except (NoSuchElementException, TimeoutException) as close_err:
                            print(f"Could not close modal via ESC for post: {close_err}. Attempting refresh as fallback.")
                            driver.refresh()
                            time.sleep(random.uniform(4, 6))
                            wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='grid']")))

                except StaleElementReferenceException:
                    print("StaleElementReferenceException. Re-fetching elements on next scroll.")
                    new_elements_processed_in_this_scroll = False
                    break
                except Exception as click_err:
                    print(f"General error processing thumbnail: {click_err}")
                    try:
                        if driver.current_url != "https://www.instagram.com/your_activity/interactions/likes/":
                             driver.get("https://www.instagram.com/your_activity/interactions/likes/")
                             wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='grid']")))
                             time.sleep(random.uniform(2, 3))
                    except:
                        pass

            if len(reel_links) >= num_reels_to_collect:
                break

            if not new_elements_processed_in_this_scroll and len(current_all_post_elements) > 0:
                print("No new unique reel elements found in this view. Proceeding to scroll.")
            elif not new_elements_processed_in_this_scroll and len(current_all_post_elements) == 0:
                print("No elements found in current view. Cannot scroll further.")
                break

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(3, 5))
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("No more content to scroll (scroll height unchanged). Breaking scroll loop.")
                break
            last_height = new_height
            scroll_attempts += 1

        print(f"Finished collecting reels. Total collected: {len(reel_links)}.")


    except Exception as e:
        print(f"An overarching error occurred: {e}")
    finally:
        driver.quit()
        print("Browser closed.")

    return list(reel_links)

# Example Usage (replace with your actual Instagram credentials):
# my_username = "your_instagram_username"
# my_password = "your_instagram_password"
#
# # To get the first 24 reels
# first_24_liked_reels = get_liked_reel_links(my_username, my_password, num_reels_to_collect=24)
#
# if first_24_liked_reels:
#     print("\nCollected the first 24 liked reel links:")
#     for reel_link in first_24_liked_reels:
#         print(reel_link)
# else:
#     print("\nNo liked reel links found or an error occurred during processing.")





def get_liked_reel_links(username, password, num_reels_to_collect=24):
    """
    Collects a specified number of Instagram reel links from the user's liked posts.

    Args:
        username (str): The Instagram username.
        password (str): The Instagram password.
        num_reels_to_collect (int): The maximum number of reel links to collect.

    Returns:
        list: A list of unique URLs to Instagram reels that the user has liked, up to the specified limit.
    """
    chrome_options = ChromeOptions()
    # Uncomment the line below to see the browser UI for debugging
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    reel_links = set()
    wait = WebDriverWait(driver, 20)

    try:
        driver.get("https://www.instagram.com/accounts/login/")
        print("Navigated to login page.")

        # --- Handle Cookie Consent Page ---
        try:
            allow_cookies_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Allow all cookies')]")))
            allow_cookies_button.click()
            print("Accepted cookies.")
            time.sleep(2)
        except TimeoutException:
            print("Cookie consent button did not appear within the timeout, or was already handled.")
        except NoSuchElementException:
            print("Cookie consent button not found by the specified XPATH. It might have different text or structure.")
        # --- End Cookie Consent Handling ---

        wait.until(EC.presence_of_element_located((By.NAME, "username")))

        username_input = driver.find_element(By.NAME, "username")
        password_input = driver.find_element(By.NAME, "password")

        username_input.send_keys(username)
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)
        print("Attempting to log in...")

        wait.until(EC.url_changes("https://www.instagram.com/accounts/login/"))
        print("Login successful.")
        time.sleep(5)

        driver.get("https://www.instagram.com/your_activity/interactions/likes/")
        print("Navigated to liked posts page.")
        wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='grid']")))
        time.sleep(6)

        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 10

        processed_post_ids = set() # Store a unique identifier for processed posts (e.g., the alt text of the image or a generated ID)

        while len(reel_links) < num_reels_to_collect and scroll_attempts < max_scroll_attempts:
            # --- UPDATED LOCATOR FOR POST THUMBNAILS ---
            # Targets the clickable div with role="button" and aria-label="Image with button"
            current_all_post_elements = driver.find_elements(By.XPATH, "//div[@role='grid']//div[@role='button' and @aria-label='Image with button']")
            print(f"Found {len(current_all_post_elements)} post elements in the current view.")

            if not current_all_post_elements and scroll_attempts == 0:
                print("No post elements found with the refined XPath. Double-check browser inspection.")
                break

            new_elements_processed_in_this_scroll = False
            for post_element in current_all_post_elements:
                if len(reel_links) >= num_reels_to_collect:
                    break

                # Get a unique identifier for the post element to avoid re-processing
                # The 'alt' attribute of the image within the post_element might be useful,
                # or a combination of attributes. For simplicity, let's use the current `href` if it exists on a child <a>.
                # If there's no direct href on the clickable div, we'll click and then get the URL.
                
                # Try to get an underlying link if available to check if already processed
                try:
                    inner_link = post_element.find_element(By.XPATH, ".//a")
                    post_id_or_href = inner_link.get_attribute("href")
                except NoSuchElementException:
                    # If no inner <a>, then the clickable div is the primary element.
                    # We can use its outerHTML or a combination of its attributes to generate an ID.
                    post_id_or_href = post_element.get_attribute("outerHTML")[:50] # Use part of HTML as a temp ID
                
                if post_id_or_href in processed_post_ids:
                    continue # Skip if already processed
                
                processed_post_ids.add(post_id_or_href)
                new_elements_processed_in_this_scroll = True

                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", post_element)
                    time.sleep(0.2)

                    is_reel_thumbnail = False
                    try:
                        # Check for the reel icon *within* this specific post_element
                        # The reel icon is a div with data-bloks-name="ig.components.Icon" and a specific mask-image
                        reel_icon_check = post_element.find_element(By.XPATH, ".//div[@data-bloks-name='ig.components.Icon' and contains(@style, 'reels__filled__')]")
                        is_reel_thumbnail = True
                    except NoSuchElementException:
                        pass # Not a reel thumbnail

                    if not is_reel_thumbnail:
                        continue # Skip to the next post if it's not a reel

                    print(f"Clicking a reel thumbnail. Collected: {len(reel_links)}/{num_reels_to_collect})")
                    post_element.click()
                    time.sleep(3) # Wait for post to load (modal or new page)

                    current_post_url = driver.current_url
                    if "/reel/" in current_post_url:
                        cleaned_url = current_post_url.split('?')[0]
                        if cleaned_url not in reel_links:
                            reel_links.add(cleaned_url)
                            print(f"Successfully captured reel link: {cleaned_url} (Total: {len(reel_links)}/{num_reels_to_collect})")
                    else:
                        print(f"Opened post is not a reel (URL: {current_post_url}).")
                        # If it's not a reel, we still need to go back or close the modal

                    # Decide whether to go back or close modal
                    # If the URL changed from the likes page URL, it means we navigated to a new page
                    if current_post_url != "https://www.instagram.com/your_activity/interactions/likes/":
                        driver.back()
                        print("Navigated back to likes page.")
                        wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='grid']")))
                        time.sleep(2)
                    else: # URL didn't change, assume modal
                        try:
                            # Try to find a specific link within the modal for the actual reel permalink, if the URL didn't change.
                            # This is a fallback if direct URL check missed it (e.g., if it's a modal and a specific link is present)
                            modal_reel_link = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//a[contains(@href, '/reel/')]")), 5)
                            href_from_modal = modal_reel_link.get_attribute("href")
                            if href_from_modal:
                                cleaned_url = href_from_modal.split('?')[0]
                                if cleaned_url not in reel_links:
                                    reel_links.add(cleaned_url)
                                    print(f"Captured reel link from modal: {cleaned_url} (Total: {len(reel_links)}/{num_reels_to_collect})")
                        except TimeoutException:
                            print("No reel link found directly in modal or modal didn't fully load.")
                        except NoSuchElementException:
                             print("No reel link found directly in modal.")

                        try:
                            driver.find_element(By.CSS_SELECTOR, "body").send_keys(Keys.ESCAPE)
                            print("Closed modal via ESC.")
                            wait.until(EC.invisibility_of_element_located((By.XPATH, "//div[@role='dialog']")))
                            time.sleep(1)
                        except (NoSuchElementException, TimeoutException) as close_err:
                            print(f"Could not close modal via ESC for post (ID/HTML start: {post_id_or_href}): {close_err}. Attempting refresh as fallback.")
                            driver.refresh()
                            time.sleep(5)
                            wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='grid']")))

                except StaleElementReferenceException:
                    print(f"StaleElementReferenceException for post (ID/HTML start: {post_id_or_href}). Will re-fetch elements on next scroll.")
                    new_elements_processed_in_this_scroll = False # Indicate that we need to re-scan this batch
                    break
                except Exception as click_err:
                    print(f"General error processing thumbnail (ID/HTML start: {post_id_or_href}): {click_err}")
                    try:
                        if driver.current_url != "https://www.instagram.com/your_activity/interactions/likes/":
                             driver.get("https://www.instagram.com/your_activity/interactions/likes/")
                             wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='grid']")))
                             time.sleep(2)
                    except:
                        pass

            if len(reel_links) >= num_reels_to_collect:
                break

            # Scroll only if new elements were processed in this iteration AND we still need more reels
            # or if no elements were found initially and we are still below max_scroll_attempts.
            if new_elements_processed_in_this_scroll or (len(current_all_post_elements) == 0 and scroll_attempts == 0):
                # If we found and processed new elements, or if we found no elements but haven't scrolled, try scrolling.
                pass
            else:
                # If no new unique elements were found AND we already found some posts, it means we're done with the current view
                if len(current_all_post_elements) > 0:
                    print("No new unique elements to process in current view. Proceeding to scroll.")
                else:
                    print("No elements to scroll for.")
                    break # Break if no elements to process.

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("No more content to scroll (scroll height unchanged). Breaking scroll loop.")
                break
            last_height = new_height
            scroll_attempts += 1

        print(f"Finished collecting reels. Total collected: {len(reel_links)}.")


    except Exception as e:
        print(f"An overarching error occurred: {e}")
    finally:
        driver.quit()
        print("Browser closed.")

    return list(reel_links)

# Example Usage (replace with your actual Instagram credentials):
# my_username = "your_instagram_username"
# my_password = "your_instagram_password"
#
# # To get the first 24 reels
# first_24_liked_reels = get_liked_reel_links(my_username, my_password, num_reels_to_collect=24)
#
# if first_24_liked_reels:
#     print("\nCollected the first 24 liked reel links:")
#     for reel_link in first_24_liked_reels:
#         print(reel_link)
# else:
#     print("\nNo liked reel links found or an error occurred during processing.")



def get_liked_reels_urls(username, password):
    driver = webdriver.Chrome()
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(3)

    # Log in
    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password + Keys.RETURN)
    time.sleep(5)

    # Go to your profile
    driver.get(f"https://www.instagram.com/{username_short}/")
    time.sleep(3)

    # Instagram does not have a direct "liked reels" page on web.
    # You may need to navigate to "Saved" or "Your activity" and filter for Reels.
    # This part is highly dependent on Instagram's current UI.
    # Example: Open "Saved" tab (if you save liked Reels)
    driver.get(f"https://www.instagram.com/{username_short}/saved/")
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

    print(list(reel_urls))

    reel_like_urls = set()
    # https://www.instagram.com/your_activity/interactions/likes/

    driver.quit()
    return list(reel_urls)










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
    for w,s in yake.KeywordExtractor(top=8, stopwords=None, lan="en", n=3).extract_keywords(t): 
        # print nicely with 2 digits after the comma
    
        print (w,"{:.2f}".format(s))
   
    return tags


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Download Instagram Reel Videos")
    parser.add_argument('--url', help='Full URL of the Instagram post or reel', default="DJUSG1uuj-_")
    parser.add_argument('--dir', default='/tmp/', help='Directory to save the downloaded video (default: current directory)')
    parser.add_argument('--scraping', default=False, help='Scrape your reels)', action='store_true')
    args = parser.parse_args()
    print(args)
   
    load_dotenv()
    
    if args.scraping is True:
        print("Scraping liked reels URLs...")
        username = os.getenv("IG_USERNAME")
        username_short = os.getenv("IG_USERNAME_SHORT")
        password = os.getenv("IG_PASSWORD")
        print(username, password)
        get_liked_reel_links(username, password)  


    downloaded_files = download_instagram_video(args.url, args.dir)
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
        transcript_file, ret_code = transcribe_with_whisper(mp4_file,output_dir)
        tags=tags_for_transcript(transcript_file)
    else:
        print("No MP4 file found in downloaded files. Skipping transcription and conversion.")