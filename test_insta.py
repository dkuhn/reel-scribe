
import requests

def check_video_availability(url):
    """
    Checks if an Instagram video is available by inspecting the final URL
    and page content for known error signatures.
    """
    # Instagram blocks requests without a User-Agent, so we must spoof one.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, allow_redirects=True)
        
        # 1. Check for redirection to the login page
        # Instagram often redirects deleted/private content to: https://www.instagram.com/accounts/login/...
        if "accounts/login" in response.url:
            return False, "Redirected to login (Likely deleted or private)"

        # 2. Check for the specific error text seen in your screenshot
        # Note: Instagram is a JavaScript app, so the exact text "Post isn't available" 
        # is sometimes rendered dynamically, but "Page Not Found" often appears in the <title> tag.
        page_content = response.text.lower()
        
        signatures = [
            "post isn't available",
            "page not found",
            "link may be broken",
            "content isn't available"
        ]
        
        for sig in signatures:
            if sig in page_content:
                return False, f"Found error signature: '{sig}'"

        # 3. Check HTTP Status (Just in case they do return 404)
        if response.status_code == 404:
            return False, "HTTP 404 Not Found"

        return True, "Available"

    except Exception as e:
        return False, f"Script Error: {e}"

# --- Main Execution ---

# The 17 failed URLs from your previous log file
failed_urls = [
    "https://www.instagram.com/reel/CvFO1_ALAj1",
    "https://www.instagram.com/reel/CtkH0rCJMLC",
    "https://www.instagram.com/reel/ChxOhzUpdvo",
    "https://www.instagram.com/reel/CWwAqAchjoH",
    "https://www.instagram.com/reel/CWJYPSJAtnv",
    "https://www.instagram.com/reel/CVxs1mglu5W",
    "https://www.instagram.com/reel/CV_pOliosri",
    "https://www.instagram.com/reel/CVhp1I6Be5B",
    "https://www.instagram.com/reel/CVS8UHiF6E8",
    "https://www.instagram.com/reel/CUyMucbNM5p",
    "https://www.instagram.com/reel/CT9n9AxAj3G",
    "https://www.instagram.com/reel/CUCo7dxDYHA",
    "https://www.instagram.com/reel/CULSmDBhd0x",
    "https://www.instagram.com/reel/CTu4Nc3l9WS",
    "https://www.instagram.com/reel/CTpIm0wNocH",
    "https://www.instagram.com/reel/CQjbGrAgy4S",
    "https://www.instagram.com/reel/CMT4WIGAnyo"
]

print(f"Checking {len(failed_urls)} URLs...\n")

for url in failed_urls:
    is_available, reason = check_video_availability(url)
    
    if is_available:
        print(f"✅ AVAILABLE: {url}")
    else:
        print(f"❌ UNAVAILABLE: {url} | Reason: {reason}")
