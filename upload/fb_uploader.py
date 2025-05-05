import os
import shutil
import argparse
import json
import time
import requests
from datetime import datetime

# print(f"Current working directory: {os.getcwd()}")

def upload_videos_to_facebook(folder_path, access_token, page_id, caption=None, debug=False):
    """
    Upload videos from a folder to a Facebook page in batches of 5, delete after successful upload
    
    Args:
        folder_path: Path to folder containing videos
        access_token: Facebook access token
        page_id: Facebook page ID
        caption: Optional caption to use for all videos
        debug: Whether to show detailed error information
    """
    # Check if folder exists
    if not os.path.isdir(folder_path):
        print(f"Error: {folder_path} is not a valid directory")
        return False
    
    # Verify token and page access
    try:
        response = requests.get(
            f"https://graph.facebook.com/v16.0/{page_id}",
            params={"access_token": access_token}
        )
        if response.status_code != 200:
            print(f"Error connecting to Facebook page: {response.json().get('error', {}).get('message', 'Unknown error')}")
            if debug:
                print(f"Full error response: {response.json()}")
            return False
        page_info = response.json()
        print(f"Connected to Facebook Page: {page_info.get('name', 'Unknown')}")
        response.close()
    
    except Exception as e:
        print(f"Error verifying access: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return False
    
    # Get all video files in the folder
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.wmv']
    video_files = [f for f in os.listdir(folder_path) 
                   if any(f.lower().endswith(ext) for ext in video_extensions)]
    
    if not video_files:
        print(f"No video files found in {folder_path}")
        return False
    
    # Sort files by name
    video_files.sort()
    print(f"Found {len(video_files)} video file(s) to upload")
    
    # Read caption from file if it exists
    caption_file = "caption.txt"
    if os.path.exists(caption_file):
        with open(caption_file, 'r') as f:
            caption = f.read().strip()
        print(f"Using caption from {caption_file}")
    
    # Set default caption if none provided and no caption file
    if not caption:
        caption = "Check out this video!"
    
    # Read hashtags from file if it exists
    hashtags = ""
    hashtags_file = "hashtags.txt"
    if os.path.exists(hashtags_file):
        with open(hashtags_file, 'r') as f:
            hashtags = f.read().strip()
        print(f"Using hashtags from {hashtags_file}")
    
    # Combine caption and hashtags
    if hashtags:
        full_caption = f"{caption}\n\n{hashtags}"
    else:
        full_caption = caption
    
    # Track results and file paths
    upload_status = {}
    batch_size = 5
    
    # Process videos in batches
    for batch_start in range(0, len(video_files), batch_size):
        batch_files = video_files[batch_start:batch_start + batch_size]
        batch_results = []
        files_to_delete = []
        
        print(f"\nProcessing batch {batch_start // batch_size + 1} ({len(batch_files)} videos)")
        
        # Process each video in the batch
        for i, video_file in enumerate(batch_files):
            video_path = os.path.join(folder_path, video_file)
            print(f"\n[{i+1}/{len(batch_files)} in batch] Processing {video_file}")
            
            file_name = os.path.basename(video_path) 
            full_caption = file_name + full_caption
            try:
                # Check if file exists and get size
                if not os.path.exists(video_path):
                    print(f"Error: File not found - {video_path}")
                    upload_status[video_path] = {"status": "failed", "error": "File not found"}
                    batch_results.append({"file": video_file, "status": "failed", "error": "File not found"})
                    continue
                
                file_size = os.path.getsize(video_path) / (1024 * 1024)  # Size in MB
                print(f"File size: {file_size:.2f} MB")
                
                # Direct single-request upload
                print("Uploading to Facebook... (this may take several minutes)")
                
                with open(video_path, 'rb') as video_file_obj:
                    post_url = f"https://graph.facebook.com/v16.0/{page_id}/videos"
                    
                    payload = {
                        'access_token': access_token,
                        'description': full_caption,
                        'title': os.path.splitext(video_file)[0]
                    }
                    
                    files = {
                        'source': (video_file, video_file_obj, 'video/mp4')
                    }
                    
                    response = requests.post(post_url, data=payload, files=files, timeout=300)
                    
                    if response.status_code != 200:
                        error_msg = response.json().get('error', {}).get('message', 'Unknown error during upload')
                        print(f"Error: {error_msg}")
                        if debug:
                            print(f"Full error response: {response.json()}")
                        upload_status[video_path] = {"status": "failed", "error": error_msg}
                        batch_results.append({"file": video_file, "status": "failed", "error": error_msg})
                        response.close()
                        continue
                    
                    video_info = response.json()
                    video_id = video_info.get('id')
                    video_url = f"https://www.facebook.com/{page_id}/videos/{video_id}"
                    
                    print(f"Upload successful! Video ID: {video_id}")
                    print(f"Video URL: {video_url}")
                    upload_status[video_path] = {
                        "status": "success",
                        "video_id": video_id,
                        "url": video_url
                    }
                    batch_results.append({
                        "file": video_file,
                        "status": "success",
                        "video_id": video_id,
                        "url": video_url
                    })
                    files_to_delete.append(video_path)
                    response.close()
            
            except requests.exceptions.RequestException as e:
                print(f"Network error during upload: {e}")
                upload_status[video_path] = {"status": "failed", "error": str(e)}
                batch_results.append({"file": video_file, "status": "failed", "error": str(e)})
            except Exception as e:
                print(f"Error during upload: {e}")
                if debug:
                    import traceback
                    traceback.print_exc()
                upload_status[video_path] = {"status": "failed", "error": str(e)}
                batch_results.append({"file": video_file, "status": "failed", "error": str(e)})
        
        # Delete files that were successfully uploaded
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")
                upload_status[file_path]["error"] = f"Failed to delete: {str(e)}"
        
        # Save batch results to log
        log_file = f"fb_upload_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, 'w') as f:
            json.dump(batch_results, f, indent=2)
        print(f"Batch log saved to {log_file}")
        
        # Wait before next batch
        if batch_start + batch_size < len(video_files):
            print("Waiting 1 hour before next batch...")
            time.sleep(3600)
    
    # Save overall upload status
    status_log = f"fb_upload_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(status_log, 'w') as f:
        json.dump(upload_status, f, indent=2)
    print(f"\nOverall upload status saved to {status_log}")
    
    # Print summary
    successful = sum(1 for status in upload_status.values() if status["status"] == "success")
    print(f"\nUpload Summary: {successful}/{len(video_files)} videos uploaded successfully")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Upload videos to Facebook page")
    parser.add_argument("folder", help="Path to the folder containing videos")
    parser.add_argument("--token", help="Facebook access token (or will look for token.txt file)")
    parser.add_argument("--page", help="Facebook page ID (or will look for page_id.txt file)")
    parser.add_argument("--caption", help="Caption to use for all videos (overrides caption.txt)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode for detailed error information")
    args = parser.parse_args()
    
    # Get access token
    access_token = args.token
    if not access_token:
        token_file = os.path.join("D:/python/Python Video Clipper/upload", "token.txt")
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                access_token = f.read().strip()
        else:
            access_token = input("Please enter your Facebook access token: ")
            save = input("Save token for future use? (y/n): ")
            if save.lower() == 'y':
                with open(token_file, 'w') as f:
                    f.write(access_token)
    
    # Get page ID
    page_id = args.page
    if not page_id:
        page_file = os.path.join("D:/python/Python Video Clipper/upload", "page_id.txt")
        if os.path.exists(page_file):
            with open(page_file, 'r') as f:
                page_id = f.read().strip()
        else:
            page_id = input("Please enter your Facebook Page ID: ")
            save = input("Save Page ID for future use? (y/n): ")
            if save.lower() == 'y':
                with open(page_file, 'w') as f:
                    f.write(page_id)
    
    # Upload videos
    upload_videos_to_facebook(args.folder, access_token, page_id, args.caption, args.debug)

if __name__ == "__main__":
    main()