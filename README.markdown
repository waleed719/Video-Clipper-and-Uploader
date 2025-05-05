# Video Clipper and Facebook Uploader

This project provides a set of Python scripts designed to process long-form video content into short, captioned clips suitable for social media platforms like Instagram Reels or TikTok, and to upload these clips to a Facebook page. The main components are:

1. **video_clipper.py**: Processes a video file by extracting audio, transcribing it, adding subtitles, formatting clips to a 9:16 aspect ratio, and optionally adding background music.
2. **fb_uploader.py**: Uploads processed video clips to a specified Facebook page, with support for captions and hashtags.
3. **transcribe_audio_txt.ipynb**: A Jupyter notebook for transcribing audio using the faster-whisper model, generating SRT subtitle files for use in the video clipper script.

The scripts are designed to automate the creation and distribution of engaging short-form video content from longer videos, such as podcasts or interviews.

## Features

### Video Clipper (video_clipper.py)
- **Video Segmentation**: Splits a long video into clips of a specified duration (default: 10 minutes).
- **Audio Transcription**: Uses the Whisper model to transcribe audio, generating subtitles for each clip.
- **Reels Formatting**: Converts clips to a 9:16 aspect ratio (1080x1920) with black padding to fit vertical video formats.
- **Background Music**: Automatically selects and adds background music based on the transcript's mood and speech tempo, with volume ducking during speech.
- **Subtitle Integration**: Generates and embeds SRT subtitle files into clips for accessibility and engagement.
- **Mood and Tempo Analysis**: Analyzes the transcript to determine mood (e.g., happy, sad, energetic) and speech tempo (slow, medium, fast) for music selection.
- **Error Handling and Logging**: Comprehensive logging to a file (`video_clipper.log`) and console for debugging and monitoring.
- **Temporary File Management**: Safely handles temporary files with automatic cleanup to prevent disk clutter.

### Facebook Uploader (fb_uploader.py)
- **Batch Uploading**: Uploads video clips to a Facebook page in batches of 5, with a 1-hour delay between batches to respect API rate limits.
- **Caption and Hashtags**: Supports custom captions and hashtags, either from command-line arguments or text files (`caption.txt`, `hashtags.txt`).
- **Authentication**: Uses a Facebook access token and page ID, with options to save credentials for future use.
- **File Management**: Deletes successfully uploaded videos to save disk space and logs upload status to JSON files.
- **Error Handling**: Detailed error reporting with optional debug mode for troubleshooting.
- **Upload Logging**: Saves detailed logs of upload attempts and results (`fb_upload_log_*.json`, `fb_upload_status_*.json`).

### Audio Transcription Notebook (transcribe_audio_txt.ipynb)
- **Faster-Whisper Integration**: Uses the faster-whisper library for efficient audio transcription, optimized for GPU (CUDA) environments.
- **SRT Output**: Generates SRT subtitle files compatible with the video clipper script.
- **Configurable Model**: Supports various Whisper model sizes (tiny, base, small, medium, large) for transcription accuracy and speed trade-offs.
- **Colab Compatibility**: Designed for Google Colab with GPU acceleration, making it accessible for users without local GPU hardware.

## Prerequisites

Before using the scripts, ensure the following dependencies are installed and configured:

### System Requirements
- **Operating System**: Windows, macOS, or Linux
- **Python**: Version 3.8 or higher
- **FFmpeg**: Required for video and audio processing. Install it and add it to your system PATH:
  - Windows: Download from [FFmpeg website](https://ffmpeg.org/download.html) or install via Chocolatey (`choco install ffmpeg`).
  - macOS: Install via Homebrew (`brew install ffmpeg`).
  - Linux: Install via package manager (e.g., `sudo apt install ffmpeg` on Ubuntu).
- **GPU (Optional)**: Recommended for faster transcription with faster-whisper in the notebook.

### Python Dependencies
Install the required Python packages using pip. Create a virtual environment (optional but recommended) and run:

```bash
pip install -r requirements.txt
```

**requirements.txt**:
```
whisper
faster-whisper
torch
requests
```

For the Jupyter notebook, additional dependencies are installed automatically within the notebook:
- `faster-whisper`
- `ctranslate2`
- `huggingface-hub`
- `tokenizers`
- `onnxruntime`
- `av`

### Additional Setup
- **Facebook Credentials**:
  - Obtain a **Facebook Access Token** with permissions to publish videos to a page. Generate this via the [Facebook Graph API Explorer](https://developers.facebook.com/tools/explorer/) or a Facebook app.
  - Obtain the **Facebook Page ID** for the target page.
  - Store these in `token.txt` and `page_id.txt` in the `upload` directory, or provide them via command-line arguments.
- **Background Music**:
  - Place `.mp3` or `.wav` files in the `music` folder for the video clipper to use as background tracks.
- **Input Video**:
  - Ensure the input video file (e.g., `.mp4`, `.mkv`) is accessible and specified correctly in `video_clipper.py` (default: `your file name.mp4`).

## Project Structure

```
project_root/
├── video_clipper.py                # Main video processing script
├── fb_uploader.py                  # Facebook upload script
├── transcribe_audio_txt.ipynb      # Jupyter notebook for transcription
├── music/                          # Folder for background music files
├── output/                         # Output folder for processed clips
│   └── [video_name]/               # Subfolder for each video's clips
├── upload/                         # Folder for Facebook credentials
│   ├── token.txt                   # Facebook access token (optional)
│   ├── page_id.txt                 # Facebook page ID (optional)
│   ├── caption.txt                 # Optional caption file for uploads
│   ├── hashtags.txt                # Optional hashtags file for uploads
│   ├── fb_upload_log_*.json        # Logs for each upload batch
│   └── fb_upload_status_*.json     # Overall upload status logs
├── logs/                           # Folder for service logs
│   ├── services.txt                # Service execution log
│   └── errors.txt                  # Service error log
├── video_clipper.log               # Log file for video clipper
└── requirements.txt                # Python dependencies
```

## How to Use

### Step 1: Configure the Video Clipper
1. **Edit Configuration**:
   Open `video_clipper.py` and modify the configuration section as needed:
   ```python
   INPUT_VIDEO = "path/to/your/video.mp4"  # Path to your input video
   CLIP_DURATION = 60 * 10                # Duration of each clip in seconds (e.g., 10 minutes)
   WHISPER_MODEL = "base"                 # Whisper model size (tiny, base, small, medium, large)
   OUTPUT_WIDTH = 1080                    # Output width for 9:16 video
   OUTPUT_HEIGHT = 1920                   # Output height for 9:16 video
   MUSIC_FOLDER = "music"                 # Folder for background music
   MUSIC_VOLUME = 0.2                     # Music volume ( radiant energy
   DUCK_FACTOR = 0.3                      # Music volume reduction during speech
   ```
2. **Prepare Music**:
   Place `.mp3` or `.wav` files in the `music` folder. The script will randomly select a track based on the transcript's mood and tempo.
3. **Run the Script**:
   Execute the video clipper script from the command line:
   ```bash
   python video_clipper.py
   ```
   - The script will:
     - Extract audio from the input video.
     - Transcribe the audio using Whisper.
     - Analyze the transcript for mood and tempo.
     - Split the video into clips of `CLIP_DURATION`.
     - Convert clips to 9:16 format.
     - Add subtitles (if transcription is successful).
     - Add background music with volume ducking.
     - Save clips to `output/[video_name]/reel_XX.mp4`.
   - Check `video_clipper.log` for processing details and errors.

### Step 2: Transcribe Audio (Optional)
If you prefer faster transcription or need to use a GPU, use the Jupyter notebook `transcribe_audio_txt.ipynb`:
1. **Open in Google Colab**:
   - Upload the notebook to Google Colab.
   - Ensure you have a GPU runtime enabled (Runtime > Change runtime type > GPU).
2. **Configure the Notebook**:
   Update the configuration section:
   ```python
   WHISPER_MODEL = "base"  # Options: tiny, base, small, medium, large
   AUDIO_FILE = "extracted_audio.mp3"  # Path to your audio file
   ```
   - If running locally, ensure the audio file is in the same directory as the notebook.
   - In Colab, upload the audio file to the Colab environment.
3. **Run the Notebook**:
   Execute all cells. The notebook will:
   - Install `faster-whisper` and dependencies.
   - Load the specified Whisper model.
   - Transcribe the audio and generate `transcription.srt`.
   - Download `transcription.srt` for use in the video clipper script.
4. **Integrate with Video Clipper**:
   - Place `transcription.srt` in the project directory.
   - Modify `video_clipper.py` to use the pre-generated SRT file instead of running Whisper locally (requires code modification).

### Step 3: Upload to Facebook
1. **Prepare Credentials**:
   - Create an `upload` directory if it doesn't exist:
     ```bash
     mkdir upload
     ```
   - Save your Facebook access token in `upload/token.txt` and page ID in `upload/page_id.txt`, or provide them via command-line arguments.
2. **Prepare Captions and Hashtags** (Optional):
   - Create `caption.txt` with a default caption for all videos (e.g., "Check out this clip from our latest podcast!").
   - Create `hashtags.txt` with hashtags (e.g., `#Podcast #Motivation #Reels`).
3. **Run the Uploader**:
   Execute the Facebook uploader script, specifying the folder containing the processed clips:
   ```bash
   python fb_uploader.py output/[video_name] --token YOUR_TOKEN --page YOUR_PAGE_ID --caption "Your custom caption" --debug
   ```
   - **Arguments**:
     - `folder`: Path to the folder with video clips (e.g., `output/[video_name]`).
     - `--token`: Facebook access token (optional if `token.txt` exists).
     - `--page`: Facebook page ID (optional if `page_id.txt` exists).
     - `--caption`: Custom caption (optional, overrides `caption.txt`).
     - `--debug`: Enable detailed error logging.
   - The script will:
     - Verify access to the Facebook page.
     - Upload videos in batches of 5, with a 1-hour delay between batches.
     - Delete successfully uploaded videos.
     - Save upload logs to `fb_upload_log_*.json` and `fb_upload_status_*.json`.
4. **Monitor Uploads**:
   - Check the console output for upload progress and errors.
   - Review JSON log files for detailed results, including video IDs and URLs.

### Step 4: Scheduling with NSSM on Windows
To automate the execution of `video_clipper.py` and `fb_uploader.py` on a Windows system, you can create Windows services using NSSM (Non-Sucking Service Manager). This allows the scripts to run at specified intervals, with logging to `services.txt` for execution details and `errors.txt` for error messages.

#### Prerequisites
- **NSSM**: Download NSSM from [the official website](https://nssm.cc/download) or install via Chocolatey (`choco install nssm`).
- **Python**: Ensure Python is installed and accessible in the system PATH.
- **Scripts Configured**: Verify that `video_clipper.py` and `fb_uploader.py` are configured with correct input paths, credentials, and settings.

#### Steps to Create a Windows Service
1. **Install NSSM**:
   - Extract the NSSM ZIP file to a directory (e.g., `C:\nssm`).
   - Add NSSM to your system PATH or use the full path to `nssm.exe` in commands.
2. **Create a Logs Directory**:
   - Create a `logs` directory in the project root to store service logs:
     ```bash
     mkdir logs
     ```
3. **Create a Service for video_clipper.py**:
   - Open a Command Prompt as Administrator.
   - Run the following command to create a service named `VideoClipperService`:
     ```bash
     nssm install VideoClipperService
     ```
   - In the NSSM GUI:
     - **Application**:
       - **Path**: Path to your Python executable (e.g., `C:\Python39\python.exe`).
       - **Startup directory**: Path to your project directory (e.g., `C:\path\to\project`).
       - **Arguments**: Path to the script (e.g., `video_clipper.py`).
     - **Details**:
       - **Display name**: `Video Clipper Service`
       - **Description**: `Processes videos into short clips with subtitles and music.`
       - **Startup type**: `Automatic` (to start on system boot).
     - **Log on**:
       - Use the default (`Local System account`) or specify a user account with appropriate permissions.
     - **I/O**:
       - **Output (stdout)**: `C:\path\to\project\logs\services.txt`
       - **Error (stderr)**: `C:\path\to\project\logs\errors.txt`
       - **Append**: Check this to append logs instead of overwriting.
     - Click **Install service**.
4. **Create a Service for fb_uploader.py**:
   - Run:
     ```bash
     nssm install FacebookUploaderService
     ```
   - In the NSSM GUI:
     - **Application**:
       - **Path**: Path to your Python executable (e.g., `C:\Python39\python.exe`).
       - **Startup directory**: Path to your project directory (e.g., `C:\path\to\project`).
       - **Arguments**: Script with arguments (e.g., `fb_uploader.py output/[video_name] --debug`).
     - **Details**:
       - **Display name**: `Facebook Uploader Service`
       - **Description**: `Uploads video clips to a Facebook page.`
       - **Startup type**: `Automatic`.
     - **Log on**: Use the default or a specific user account.
     - **I/O**:
       - **Output (stdout)**: `C:\path\to\project\logs\services.txt`
       - **Error (stderr)**: `C:\path\to\project\logs\errors.txt`
       - **Append**: Check this to append logs.
     - Click **Install service**.
5. **Start the Services**:
   - Start the services manually to verify they work:
     ```bash
     net start VideoClipperService
     net start FacebookUploaderService
     ```
   - Alternatively, use the Services management console:
     - Open `services.msc`.
     - Find `Video Clipper Service` and `Facebook Uploader Service`.
     - Right-click and select **Start**.
6. **Schedule Execution**:
   - NSSM does not natively support scheduling, so use Windows Task Scheduler to control service execution:
     - Open Task Scheduler (`taskschd.msc`).
     - Create a new task:
       - **General**:
         - Name: `VideoClipperTask`
         - Description: `Runs the Video Clipper service daily.`
         - Check `Run whether user is logged on or not`.
       - **Triggers**:
         - New > Daily > Set time (e.g., 2:00 AM).
         - Ensure `Enabled` is checked.
       - **Actions**:
         - New > Action: `Start a program`.
         - Program: `net`
         - Arguments: `start VideoClipperService`
       - **Conditions**: Uncheck `Start the task only if the computer is on AC power` if running on a server.
       - **Settings**: Check `Allow task to be run on demand` and `Restart if the task fails`.
     - Create a similar task for `FacebookUploaderService`:
       - Name: `FacebookUploaderTask`
       - Trigger: Daily, set time (e.g., 3:00 AM, after video clipper completes).
       - Action: `net start FacebookUploaderService`
     - Save the tasks, entering admin credentials if prompted.
7. **Verify Logging**:
   - Check `logs/services.txt` for execution details (e.g., script start/stop times, processing steps).
   - Check `logs/errors.txt` for any errors (e.g., missing input video, FFmpeg errors, Facebook API issues).
   - Both files will append new entries with timestamps for each run.

#### Troubleshooting NSSM Services
- **Service Fails to Start**:
  - Check `errors.txt` for details.
  - Verify Python and FFmpeg are in the system PATH.
  - Ensure the script paths and arguments are correct in NSSM.
  - Test the script manually (`python video_clipper.py`) to isolate issues.
- **Logs Not Generated**:
  - Confirm the `logs` directory exists and is writable.
  - Check NSSM's I/O settings to ensure correct paths for `services.txt` and `errors.txt`.
- **Scheduling Issues**:
  - Verify Task Scheduler tasks are enabled and triggered correctly.
  - Check the Task Scheduler history for task execution details.
  - Ensure the services are set to `Automatic` startup in NSSM to avoid conflicts.

#### Notes
- **Sequential Execution**: Schedule `FacebookUploaderTask` after `VideoClipperTask` to ensure clips are processed before uploading.
- **Log Management**: Periodically archive or rotate `services.txt` and `errors.txt` to prevent them from growing too large.
- **Service Removal**: To remove a service, run:
  ```bash
  nssm remove VideoClipperService
  nssm remove FacebookUploaderService
  ```

## Example Workflow
1. **Process a Video**:
   - Place a video file (`podcast.mp4`) in the project directory.
   - Update `INPUT_VIDEO = "podcast.mp4"` in `video_clipper.py`.
   - Add music files to the `music` folder.
   - Run:
     ```bash
     python video_clipper.py
     ```
   - Output clips will be saved to `output/podcast/reel_01.mp4`, `reel_02.mp4`, etc.
2. **Transcribe Audio (if needed)**:
   - Extract audio from `podcast.mp4` using FFmpeg:
     ```bash
     ffmpeg -i podcast.mp4 -q:a 0 -map a extracted_audio.mp3
     ```
   - Upload `extracted_audio.mp3` to Colab and run `transcribe_audio_txt.ipynb`.
   - Download `transcription.srt` and integrate it into the video clipper script.
3. **Upload to Facebook**:
   - Create `caption.txt` with: "New podcast clip!"
   - Create `hashtags.txt` with: `#Podcast #Inspiration`.
   - Run:
     ```bash
     python fb_uploader.py output/podcast
     ```
   - Videos will be uploaded to your Facebook page, with logs saved for reference.
4. **Automate with NSSM**:
   - Set up NSSM services for `video_clipper.py` and `fb_uploader.py` as described above.
   - Schedule daily execution using Task Scheduler.
   - Monitor `services.txt` and `errors.txt` for execution details and issues.

## Troubleshooting

- **FFmpeg Not Found**:
  - Ensure FFmpeg is installed and added to your system PATH.
  - Verify by running `ffmpeg -version` in the terminal.
- **Whisper Transcription Fails**:
  - Check that the Whisper library is installed (`pip install whisper`).
  - Use the Jupyter notebook for faster transcription if local resources are limited.
  - Ensure the input audio file is valid and not corrupted.
- **Facebook Upload Errors**:
  - Verify that the access token is valid and has the necessary permissions (`publish_videos`, `pages_manage_posts`).
  - Check the page ID is correct.
  - Enable `--debug` mode for detailed error messages.
  - Ensure the video files are in a supported format (e.g., `.mp4`).
- **No Music Added**:
  - Confirm that the `music` folder exists and contains `.mp3` or `.wav` files.
  - Check `video_clipper.log` for music selection errors.
- **SRT File Issues**:
  - Ensure the SRT file is in UTF-8 encoding.
  - Verify that the subtitle timings align with the clip durations.

## Limitations
- **Whisper Model Size**: The default `base` model may not be as accurate as `large`. Use larger models for better transcription accuracy, but note increased resource requirements.
- **Music Selection**: Music selection is random and based on basic mood/tempo analysis. Advanced metadata-based matching is not implemented.
- **Facebook API Limits**: The uploader respects rate limits with a 1-hour delay between batches. Adjust `batch_size` or delay if needed.
- **Platform-Specific Issues**: The video clipper uses shell commands that may behave differently on Windows vs. Unix-based systems, particularly for subtitle paths.

## Contributing
Contributions are welcome! To contribute:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/YourFeature`).
3. Commit your changes (`git commit -m "Add YourFeature"`).
4. Push to the branch (`git push origin feature/YourFeature`).
5. Open a pull request.

Please include tests and update documentation for new features.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact
For questions or support, open an issue on the GitHub repository or contact the maintainer at [wqamar719@gmail.com].

---
*Generated on May 05, 2025*