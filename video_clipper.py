import os
import tempfile
import subprocess
import json
import whisper
import torch
import random
from dataclasses import dataclass
import shlex
import glob
import re
import math
import logging
import sys
from contextlib import contextmanager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("video_clipper.log")
    ]
)
logger = logging.getLogger(__name__)


pattern = r'^.*?(?=\.mp4$|\.mkv$)'
# Configuration
INPUT_VIDEO = "Change Your Brain Neuroscientist Dr. Andrew Huberman  Rich Roll Podcast.mp4"
file_name = re.search(pattern, INPUT_VIDEO).group()
OUTPUT_FOLDER = f"output/{file_name}"
CLIP_DURATION = 60 * 10  # in seconds
WHISPER_MODEL = "base"  # Options: "tiny", "base", "small", "medium", "large"
OUTPUT_WIDTH = 1080    # Width for vertical video (9:16 aspect ratio)
OUTPUT_HEIGHT = 1920   # Height for vertical video
MUSIC_FOLDER = "music"  # Folder containing background music tracks
MUSIC_VOLUME = 0.2     # Background music volume (0.0 to 1.0)
DUCK_FACTOR = 0.3      # How much to reduce music during speech (0.0 to 1.0)

# Ensure output directory exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(MUSIC_FOLDER, exist_ok=True)

@dataclass
class Segment:
    start: float
    end: float
    text: str

@dataclass
class AudioFeatures:
    mood: str  # happy, sad, energetic, calm, dramatic
    tempo: str  # slow, medium, fast
    genre: str  # pop, rock, electronic, ambient, classical

@contextmanager
def temp_file(suffix=None):
    """Context manager for temporary files that ensures cleanup"""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        os.close(fd)
        yield path
    finally:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {path}: {e}")

def safe_remove(filepath):
    """Safely remove a file if it exists"""
    try:
        if os.path.exists(filepath):
            os.unlink(filepath)
            logger.debug(f"Removed temporary file: {filepath}")
    except Exception as e:
        logger.warning(f"Failed to remove file {filepath}: {e}")

def safe_rename(src, dst):
    """Safely rename a file, removing destination first if it exists"""
    try:
        if os.path.exists(dst):
            os.unlink(dst)
        os.replace(src, dst)  # os.replace is more robust than os.rename
        logger.debug(f"Renamed {src} to {dst}")
        return True
    except Exception as e:
        logger.error(f"Failed to rename {src} to {dst}: {e}")
        return False

def run_command(cmd, shell=False, check=True):
    """Run a subprocess command with proper error handling and increased buffer size"""
    try:
        logger.debug(f"Running command: {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
        
        if isinstance(cmd, list) and len(' '.join(cmd)) > 8000 and not shell:
            logger.warning("Command is very long, switching to shell mode")
            shell = True
            cmd = ' '.join(cmd) if isinstance(cmd, list) else cmd
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            shell=shell, 
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with error code {e.returncode}: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"Failed to run command: {e}")
        raise

def transcribe_audio(audio_file_path):
    """Transcribe audio using local Whisper model"""
    try:
        # Load Whisper model
        logger.info(f"Loading Whisper model: {WHISPER_MODEL}")
        model = whisper.load_model(WHISPER_MODEL)
        
        # Transcribe audio
        logger.info("Running transcription with Whisper...")
        result = model.transcribe(audio_file_path, word_timestamps=True)
        
        # Process into segments
        segments = []
        for segment in result["segments"]:
            segments.append(Segment(
                start=segment["start"],
                end=segment["end"],
                text=segment["text"].strip()
            ))
        
        logger.info(f"Transcription complete: {len(segments)} segments")
        return segments, result["text"]
    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        return [], ""

def analyze_transcript_mood(transcript):
    """Simple analysis of transcript to determine mood for music selection"""
    # Very basic mood analysis based on keywords
    happy_words = ["happy", "joy", "laugh", "fun", "exciting", "amazing", "great", "love", "smile"]
    sad_words = ["sad", "cry", "tragic", "depressing", "sorry", "apology", "unfortunate", "regret"]
    energetic_words = ["energy", "fast", "quick", "rush", "exciting", "action", "dynamic", "power"]
    calm_words = ["calm", "peaceful", "quiet", "relax", "gentle", "soothing", "slow"]
    dramatic_words = ["dramatic", "intense", "serious", "important", "significant", "critical"]
    
    # Convert transcript to lowercase for matching
    transcript_lower = transcript.lower()
    
    # Count occurrences of mood-related words
    happy_count = sum(1 for word in happy_words if word in transcript_lower)
    sad_count = sum(1 for word in sad_words if word in transcript_lower)
    energetic_count = sum(1 for word in energetic_words if word in transcript_lower)
    calm_count = sum(1 for word in calm_words if word in transcript_lower)
    dramatic_count = sum(1 for word in dramatic_words if word in transcript_lower)
    
    # Determine dominant mood
    mood_counts = {
        "happy": happy_count,
        "sad": sad_count,
        "energetic": energetic_count,
        "calm": calm_count,
        "dramatic": dramatic_count
    }
    
    # Default to calm if no clear mood is detected
    if all(count == 0 for count in mood_counts.values()):
        return "calm"
    
    # Return mood with highest count
    dominant_mood = max(mood_counts, key=mood_counts.get)
    logger.info(f"Dominant mood detected: {dominant_mood}")
    return dominant_mood

def analyze_speech_pattern(segments):
    """Analyze speech patterns to determine tempo"""
    if not segments:
        return "medium"
    
    # Calculate average words per minute
    total_duration = segments[-1].end - segments[0].start
    total_words = sum(len(segment.text.split()) for segment in segments)
    
    if total_duration <= 0:
        return "medium"
    
    words_per_minute = (total_words / total_duration) * 60
    
    # Classify tempo based on words per minute
    if words_per_minute < 120:
        tempo = "slow"
    elif words_per_minute > 160:
        tempo = "fast"
    else:
        tempo = "medium"
        
    logger.info(f"Speech tempo detected: {tempo} ({words_per_minute:.1f} words/min)")
    return tempo

def select_appropriate_music(features):
    """Select appropriate music based on content analysis"""
    # Check if music folder exists and contains files
    if not os.path.exists(MUSIC_FOLDER):
        logger.info(f"Music folder '{MUSIC_FOLDER}' not found. Creating it.")
        os.makedirs(MUSIC_FOLDER)
        return None
    
    music_files = glob.glob(os.path.join(MUSIC_FOLDER, "*.mp3"))
    music_files.extend(glob.glob(os.path.join(MUSIC_FOLDER, "*.wav")))
    
    if not music_files:
        logger.warning(f"No music files found in '{MUSIC_FOLDER}'. Please add some .mp3 or .wav files.")
        return None
    
    # For now, just pick a random track - in a real system you would match by metadata
    logger.info(f"Selecting music track based on mood: {features.mood}, tempo: {features.tempo}")
    selected_track = random.choice(music_files)
    logger.info(f"Selected track: {selected_track}")
    
    return selected_track

def generate_volume_automation(segments, clip_duration, max_points=5):
    """Generate volume automation with reduced complexity"""
    if not segments:
        return None
    
    # Group segments that are close to each other
    grouped_segments = []
    current_group = None
    
    for segment in segments:
        if current_group is None:
            current_group = {"start": segment.start, "end": segment.end}
        elif segment.start - current_group["end"] < 1.0:  # If less than 1 second gap
            current_group["end"] = segment.end
        else:
            grouped_segments.append(current_group)
            current_group = {"start": segment.start, "end": segment.end}
    
    if current_group:
        grouped_segments.append(current_group)
    
    # Reduce number of groups if there are too many
    if len(grouped_segments) > max_points:
        # Further group segments to reduce complexity
        merged_segments = []
        for i in range(0, len(grouped_segments), max(1, len(grouped_segments) // max_points)):
            start = grouped_segments[i]["start"]
            end = grouped_segments[min(i + max(1, len(grouped_segments) // max_points) - 1, len(grouped_segments) - 1)]["end"]
            merged_segments.append({"start": start, "end": end})
        grouped_segments = merged_segments
    
    # Create volume points for each group
    volume_points = []
    
    # Start with full volume
    if grouped_segments[0]["start"] > 0:
        volume_points.append(f"volume={MUSIC_VOLUME}")
    
    for i, group in enumerate(grouped_segments):
        # Add duck point for speech
        volume_points.append(f"volume=enable='between(t,{group['start']},{group['end']})':volume={MUSIC_VOLUME * DUCK_FACTOR}")
        
        # Add normal volume point between speech segments
        if i < len(grouped_segments) - 1 and grouped_segments[i+1]["start"] - group["end"] > 0.5:
            volume_points.append(f"volume=enable='between(t,{group['end']},{grouped_segments[i+1]['start']})':volume={MUSIC_VOLUME}")
    
    # Add final full volume segment if needed
    if grouped_segments[-1]["end"] < clip_duration:
        volume_points.append(f"volume=enable='between(t,{grouped_segments[-1]['end']},{clip_duration})':volume={MUSIC_VOLUME}")
    
    return volume_points

def generate_srt_file(segments, output_srt_path, time_offset=0):
    """Generate SRT subtitle file from segments"""
    try:
        with open(output_srt_path, 'w', encoding='utf-8') as srt_file:
            for i, segment in enumerate(segments, 1):
                # Adjust times based on offset
                start_time = max(0, segment.start - time_offset)
                end_time = max(0, segment.end - time_offset)
                
                # Convert to SRT format (HH:MM:SS,mmm)
                start_formatted = format_time_srt(start_time)
                end_formatted = format_time_srt(end_time)
                
                # Write SRT entry
                srt_file.write(f"{i}\n")
                srt_file.write(f"{start_formatted} --> {end_formatted}\n")
                srt_file.write(f"{segment.text}\n\n")
        
        logger.debug(f"Generated SRT file: {output_srt_path}")
        return output_srt_path
    except Exception as e:
        logger.error(f"Failed to generate SRT file: {e}")
        return None

def format_time_srt(seconds):
    """Format time in seconds to SRT format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_part = seconds % 60
    milliseconds = int((seconds_part - int(seconds_part)) * 1000)
    return f"{hours:02}:{minutes:02}:{int(seconds_part):02},{milliseconds:03}"

def get_video_duration(video_path):
    """Get the duration of a video file using ffprobe"""
    try:
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "json", 
            video_path
        ]
        
        result = run_command(cmd)
        data = json.loads(result.stdout)
        duration = float(data["format"]["duration"])
        logger.info(f"Video duration: {duration:.2f} seconds")
        return duration
    except Exception as e:
        logger.error(f"Failed to get video duration: {e}")
        return 0

def extract_audio(video_path, output_audio_path):
    """Extract audio from video using ffmpeg"""
    try:
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-q:a", "0",
            "-map", "a",
            "-y",  # Overwrite output file if it exists
            output_audio_path
        ]
        
        run_command(cmd)
        logger.info(f"Extracted audio to: {output_audio_path}")
        return output_audio_path
    except Exception as e:
        logger.error(f"Failed to extract audio: {e}")
        return None

def extract_clip_without_subtitles(input_video, output_path, start_time, duration):
    """Extract a clip from the video without adding subtitles"""
    try:
        cmd = [
            "ffmpeg",
            "-ss", str(start_time),
            "-i", input_video,
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "aac",
            "-y",
            output_path
        ]
        
        logger.info(f"Extracting clip from {start_time}s to {start_time + duration}s")
        run_command(cmd)
        return output_path
    except Exception as e:
        logger.error(f"Failed to extract clip: {e}")
        return None

def convert_to_reels_format(input_video, output_path):
    """Convert video to reels format (9:16 aspect ratio) with black padding"""
    try:
        cmd = [
            "ffmpeg",
            "-i", input_video,
            "-vf", f"scale=w={OUTPUT_WIDTH}:h={OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black:",
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "copy",
            "-y",
            output_path
        ]
        
        logger.info(f"Converting to reels format ({OUTPUT_WIDTH}x{OUTPUT_HEIGHT})")
        run_command(cmd)
        return output_path
    except Exception as e:
        logger.error(f"Failed to convert to reels format: {e}")
        return None

def add_subtitles_to_video(input_video, subtitle_file, output_path):
    """Add subtitles to video using the subtitles filter"""
    try:
        # Convert Windows path to safe format for FFmpeg
        subtitle_safe_path = subtitle_file.replace('\\', '/').replace(':', '\\:')
        
        # Prepare subtitle filter
        subtitle_filter = f"subtitles=filename={shlex.quote(subtitle_file)}"
        
        logger.info(f"Adding subtitles to video from {subtitle_file}")
        
        # Use shell=True for Windows to handle the subtitle path correctly
        if os.name == 'nt':
            subprocess_cmd = f'ffmpeg -i "{input_video}" -vf "subtitles={subtitle_file}" -c:v libx264 -preset fast -c:a copy -y "{output_path}"'
            run_command(subprocess_cmd, shell=True)
        else:
            cmd = [
                "ffmpeg",
                "-i", input_video,
                "-vf", subtitle_filter,
                "-c:v", "libx264",
                "-preset", "fast",
                "-c:a", "copy",
                "-y",
                output_path
            ]
            run_command(cmd)
        
        return output_path
    except Exception as e:
        logger.error(f"Failed to add subtitles: {e}")
        return None

def add_background_music(input_video, music_file, output_path, volume_points=None, clip_duration=None):
    """Add background music to video with simplified volume control during speech"""
    try:
        if not music_file or not os.path.exists(music_file):
            logger.warning("No music file available, skipping music addition")
            if os.path.exists(input_video):
                # Just copy the input file to output
                safe_rename(input_video, output_path)
            return output_path
        
        # Use a simpler approach with fewer filter points
        # Instead of many small segments, use a constant volume reduction
        
        # Get clip duration if not provided
        if not clip_duration:
            try:
                result = run_command([
                    "ffprobe", "-v", "error", "-show_entries", "format=duration", 
                    "-of", "json", input_video
                ])
                clip_duration = float(json.loads(result.stdout)["format"]["duration"])
            except Exception as e:
                logger.error(f"Error getting clip duration: {e}")
                clip_duration = 120  # Default to 2 minutes
        
        # Get music duration
        try:
            result = run_command([
                "ffprobe", "-v", "error", "-show_entries", "format=duration", 
                "-of", "json", music_file
            ])
            music_duration = float(json.loads(result.stdout)["format"]["duration"])
            logger.info(f"Music duration: {music_duration:.2f}s, Clip duration: {clip_duration:.2f}s")
        except Exception as e:
            logger.error(f"Error getting music duration: {e}")
            music_duration = 0
        
        # Determine if we need to loop the music
        music_filter = ""
        if music_duration > 0 and clip_duration > 0 and music_duration < clip_duration:
            # Need to loop the music
            loop_count = math.ceil(clip_duration / music_duration)
            music_filter = f"aloop=loop={loop_count-1}:size=0,"
            logger.info(f"Looping music {loop_count} times to match clip duration")
        
        # Create a temporary file for the music with adjusted volume
        with temp_file(suffix='.mp3') as temp_music_path:
            # First, create a version of the music with constant volume
            music_vol_cmd = [
                "ffmpeg",
                "-i", music_file,
                "-af", f"{music_filter}volume={MUSIC_VOLUME}",
                "-y",
                temp_music_path
            ]
            run_command(music_vol_cmd)
            
            # Now mix the adjusted music with the original video
            cmd = [
                "ffmpeg",
                "-i", input_video,
                "-i", temp_music_path,
                "-filter_complex", "[0:a][1:a]amix=duration=longest:normalize=0",
                "-c:v", "copy",  # Copy video stream
                "-shortest",     # End when shortest input ends
                "-y",
                output_path
            ]
            
            logger.info(f"Adding background music with constant volume")
            run_command(cmd)
        
        return output_path
    except Exception as e:
        logger.error(f"Failed to add background music: {e}")
        # Try to salvage by using the input video if it exists
        if os.path.exists(input_video) and not os.path.exists(output_path):
            logger.info(f"Salvaging by copying input video to output")
            safe_rename(input_video, output_path)
        return output_path

def process_video():
    """Main function to process video into captioned reels clips with background music"""
    try:
        if not os.path.exists(INPUT_VIDEO):
            logger.error(f"Input video not found: {INPUT_VIDEO}")
            return False
            
        logger.info(f"Starting video processing: {INPUT_VIDEO}")
        video_duration = get_video_duration(INPUT_VIDEO)
        if video_duration <= 0:
            logger.error("Could not determine video duration")
            return False
        
        # Extract full audio for transcription
        logger.info("Extracting audio from video for transcription...")
        with temp_file(suffix='.mp3') as temp_audio_path:
            extract_audio(INPUT_VIDEO, temp_audio_path)
            
            # Transcribe full audio
            logger.info("Transcribing audio...")
            all_segments, full_transcript = transcribe_audio(temp_audio_path)
        
        # Analyze content to select appropriate music
        music_track = None
        if full_transcript:
            mood = analyze_transcript_mood(full_transcript)
            
            if all_segments:
                tempo = analyze_speech_pattern(all_segments)
            else:
                tempo = "medium"
                
            # Create audio features object for music selection
            audio_features = AudioFeatures(mood=mood, tempo=tempo, genre="")
            
            # Select appropriate music
            music_track = select_appropriate_music(audio_features)
        
        if not all_segments:
            logger.warning("No transcription available. Processing will continue without captions.")
        
        # Process video in clips
        clip_num = 1
        processed_clips = []
        
        for start_time in range(0, int(video_duration), CLIP_DURATION):
            end_time = min(start_time + CLIP_DURATION, int(video_duration))
            clip_duration = end_time - start_time
            
            logger.info(f"\nProcessing clip {clip_num} ({start_time}-{end_time} seconds)...")
            
            # Create temporary filenames
            temp_clip_path = f"temp_clip_{clip_num}.mp4"
            temp_reels_path = f"temp_reels_{clip_num}.mp4"
            temp_subtitled_path = f"temp_subtitled_{clip_num}.mp4"
            temp_srt_path = f"temp_subtitles_{clip_num}.srt"
            final_output_path = os.path.join(OUTPUT_FOLDER, f"reel_{clip_num:02d}.mp4")
            
            # Make sure any existing temporary files are removed
            for temp_filepath in [temp_clip_path, temp_reels_path, temp_subtitled_path, temp_srt_path]:
                safe_remove(temp_filepath)
            
            try:
                # Step 1: Extract clip without modifications
                extracted_clip = extract_clip_without_subtitles(INPUT_VIDEO, temp_clip_path, start_time, clip_duration)
                if not extracted_clip or not os.path.exists(temp_clip_path):
                    logger.error(f"Failed to extract clip {clip_num}. Skipping.")
                    continue
                
                # Step 2: Convert to reels format with padding
                converted_clip = convert_to_reels_format(temp_clip_path, temp_reels_path)
                if not converted_clip or not os.path.exists(temp_reels_path):
                    logger.error(f"Failed to convert clip {clip_num} to reels format. Skipping.")
                    safe_remove(temp_clip_path)
                    continue
                
                # Clean up intermediate file
                safe_remove(temp_clip_path)
                
                # Step 3: Add subtitles if available
                volume_points = None
                using_reels_as_subtitled = False
                
                if all_segments:
                    # Filter segments for this clip
                    clip_segments = [
                        segment for segment in all_segments
                        if segment.end > start_time and segment.start < end_time
                    ]
                    
                    # Adjust segment times to be relative to the clip
                    clip_segments_adjusted = []
                    for segment in clip_segments:
                        adjusted = Segment(
                            start=max(0, segment.start - start_time),
                            end=min(clip_duration, segment.end - start_time),
                            text=segment.text
                        )
                        clip_segments_adjusted.append(adjusted)
                    
                    # Generate volume ducking points for background music
                    # volume_points = generate_volume_automation(clip_segments_adjusted, clip_duration)
                    volume_points = generate_volume_automation(clip_segments_adjusted, clip_duration, max_points=5)

                    
                    if clip_segments:
                        # Generate SRT with time offset
                        srt_generated = generate_srt_file(clip_segments, temp_srt_path, time_offset=start_time)
                        
                        if srt_generated and os.path.exists(temp_srt_path):
                            # Add subtitles
                            logger.info(f"Adding subtitles to clip {clip_num}...")
                            subtitled_clip = add_subtitles_to_video(temp_reels_path, temp_srt_path, temp_subtitled_path)
                            
                            if subtitled_clip and os.path.exists(temp_subtitled_path):
                                # Successfully added subtitles
                                safe_remove(temp_reels_path)
                            else:
                                # Failed to add subtitles, use non-subtitled version
                                logger.warning(f"Failed to add subtitles to clip {clip_num}. Using non-subtitled version.")
                                temp_subtitled_path = temp_reels_path
                                using_reels_as_subtitled = True
                            
                            # Clean up temporary SRT file
                            safe_remove(temp_srt_path)
                        else:
                            # SRT generation failed
                            logger.warning(f"Failed to generate SRT for clip {clip_num}. Using non-subtitled version.")
                            temp_subtitled_path = temp_reels_path
                            using_reels_as_subtitled = True
                    else:
                        # No segments in this clip
                        logger.info(f"No speech segments in clip {clip_num}. No subtitles needed.")
                        temp_subtitled_path = temp_reels_path
                        using_reels_as_subtitled = True
                else:
                    # No transcription available
                    temp_subtitled_path = temp_reels_path
                    using_reels_as_subtitled = True
                
                # Step 4: Add background music if available
                # Make sure final_output_path doesn't exist before attempting to write to it
                if os.path.exists(final_output_path):
                    safe_remove(final_output_path)
                
                if music_track:
                    logger.info(f"Adding background music to clip {clip_num}...")
                    final_clip = add_background_music(
                        temp_subtitled_path, 
                        music_track, 
                        final_output_path, 
                        volume_points, 
                        clip_duration
                    )
                else:
                    # No music to add, just rename
                    final_clip = temp_subtitled_path
                    safe_rename(temp_subtitled_path, final_output_path)
                
                # Verify final output exists
                if os.path.exists(final_output_path):
                    logger.info(f"Successfully created: {final_output_path}")
                    processed_clips.append(final_output_path)
                else:
                    logger.error(f"Failed to create final output for clip {clip_num}")
                
                # Clean up remaining temp files
                if not using_reels_as_subtitled:
                    safe_remove(temp_subtitled_path)
                if os.path.exists(temp_reels_path) and not using_reels_as_subtitled:
                    safe_remove(temp_reels_path)
                
            except Exception as e:
                logger.error(f"Error processing clip {clip_num}: {e}")
                # Clean up any temp files
                for temp_filepath in [temp_clip_path, temp_reels_path, temp_subtitled_path, temp_srt_path]:
                    safe_remove(temp_filepath)
            
            clip_num += 1
        
        if processed_clips:
            logger.info(f"\nSuccessfully processed {len(processed_clips)} clips:")
            for clip in processed_clips:
                logger.info(f"  - {clip}")
            return True
        else:
            logger.warning("No clips were successfully processed")
            return False
            
    except Exception as e:
        logger.error(f"Critical error during processing: {e}")
        return False

def check_dependencies():
    """Check for required dependencies"""
    try:
        # Check if ffmpeg is available
        result = run_command(["ffmpeg", "-version"], check=False)
        if result.returncode != 0:
            logger.error("FFmpeg not installed or not in PATH. Please install ffmpeg first.")
            return False
        else:
            logger.info(f"FFmpeg found: {result.stdout.splitlines()[0] if result.stdout else 'version unknown'}")
        
        # Check for whisper
        try:
            import whisper
            logger.info("Whisper library found")
            return True
        except ImportError:
            logger.error("Whisper not installed. Please install it with:")
            logger.error("pip install git+https://github.com/openai/whisper.git")
            return False
    except Exception as e:
        logger.error(f"Error checking dependencies: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting video clipper script")
    
    if check_dependencies():
        logger.info("All dependencies found, starting video processing")
        success = process_video()
        if success:
            logger.info("Video processing completed successfully")
        else:
            logger.error("Video processing failed")
    else:
        logger.error("Missing dependencies, cannot continue")