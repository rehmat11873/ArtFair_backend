import os
import csv
from io import StringIO, BytesIO
import tempfile
from django.core.files import File
import torchaudio
from ..models import MediaFile
import pandas as pd
from pydub import AudioSegment as PydubAudioSegment  # Renamed to avoid conflict
from torchaudio.transforms import Resample


'''
This homemade module takes the waveform of an audio file along with a row from the caption_data dataframe and outputs a clip starting/ending at the given timestamp.
You can use it over parallel processing threads for extra efficiency, since the audio conversion process can be slow. 
'''
def create_audio_clips(audio_file, csv_file): # Input the audio file (.wav) from the Full_Audio folder, and the caption file (.csv) from the Caption_CSVs folder.
    '''
    This method (timecode_to_milliseconds) will convert the string timecodes in the "Start" and "End" fields to millisecond values. Pydub and FFMPEG need the timestamps entered this way to trim the audio files.
    '''
    def timecode_to_milliseconds(timecode):
        still_timecode = ':' in str(timecode)
        
        if still_timecode:
            # Split the timecode into hours, minutes, seconds, and hundredths of a second
            hours, minutes, seconds = map(float, timecode.split(':'))
            
            # Convert the timecode to total milliseconds
            total_milliseconds = hours * 3600000 + minutes * 60000 + seconds * 1000
            return total_milliseconds
            
        else:
            return timecode
    
    # Load Caption File as Pandas DataFrame
    csv_file_content = csv_file.file.read() # Read the file content
    csv_file_like_object = BytesIO(csv_file_content) # Converts file content into a file-like object that can load into a pandas dataframe
    
    csv_string_content = csv_file.file.read().decode('utf-8')
    csv_reader = csv.DictReader(StringIO(csv_string_content))
    rows = list(csv_reader)
    
    print(f"Loading {len(rows)+1} entries to dataframe . . .")

    caption_data = pd.read_csv(csv_file_like_object) # Retrieves the newly cleaned up Caption CSV file and reads it into a pandas dataframe
    caption_data.columns = caption_data.columns.str.strip() # Removes leading spaces from header columns

    caption_data['start_time'] = caption_data['start_time'].apply(timecode_to_milliseconds)
    caption_data['end_time'] = caption_data['end_time'].apply(timecode_to_milliseconds)

    caption_data['index'] = range(1, len(caption_data) +1) # Adds an index field to each row. This helps in joining wav clip audio to specific captions later. Will be used in the "segment_audio" method.
  
    print(f"Entries loaded successfully. Displaying top 5 rows:")
    print(caption_data.head())

    # Segment wav File by Caption Timecodes
    '''
    This method uses torchaudio to maniupulate audio files. It splits the work over multiple threads for speed. 
    There are other ways to do it, like pymad as a wrapper on top of mad. However, I had trouble getting those to work, and support seems to be old.

    Note: The following method expects input_audio to come in as an wav.
    '''
    audio_file.file.seek(0)
    audio_file_content = audio_file.file.read()
        
    print("Loading audio for segmentation . . . ")
    
    # Save the audio content to a temporary file
    with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as tmp_file:
        tmp_file.write(audio_file_content)
        tmp_file.flush()  # Flush internal buffer
        tmp_file.seek(0)  # Seek back to start of file (may not be needed)

        waveform, sample_rate = torchaudio.load(tmp_file.name)
    
    # Resample audio to 16kHz for Whisper compatibility
    new_sample_rate = 16000 # 16kHz is the default input rate for Whisper. Matching the input sample rate of the clips to what the model expects is important.
    
    resampler = Resample(sample_rate, new_sample_rate)
    resampled_waveform = resampler(waveform)
    waveform = resampled_waveform
    
    print("Audio loaded. Ready to segment.")
    
    # Create a shell process that can divide the work to parallel jobs on different GPU threads
    def process_row(index, row):
        audio_path = create_segment(waveform, new_sample_rate, row, audio_file)
        caption_data.at[index, 'AudioPath'] = audio_path
        caption_data.at[index, 'clip_number'] = index

    print("Segmenting audio into caption-level clips")
    '''
    # Execute the clip segment creation process, parallelized across GPU or CPU threads.
    ## Adjust the number of workers based on your hardware's capability and the task's requirements
    with ThreadPoolExecutor(max_workers=12) as executor:
        executor.map(lambda x: process_row(*x), enumerate(caption_data.to_dict('records')))
    '''
    # Execute the clip segment creation process serially (no multithreading)
    caption_data.apply(lambda row: process_row(row.name, row), axis=1)
    
    # Update CSV Files to include audio file paths for later use as Training Data
    buffer = StringIO()
    caption_data.to_csv(buffer, index=False, quoting=csv.QUOTE_ALL)
    buffer.seek(0)

    # Convert to bytes for Django File object
    csv_bytes = buffer.getvalue().encode('utf-8')
    buffer_bytes = BytesIO(csv_bytes)

    # Save and overwrite the original file
    csv_file.file.save(csv_file.file.name, File(buffer_bytes), save=True)


def convert_aac_to_wav(audio_file):
    audio_file.file.seek(0)
    audio_file_content = audio_file.file.read()
    with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as tmp_file:
        audio = PydubAudioSegment.from_file(BytesIO(audio_file_content), format="aac")
        audio.export(tmp_file.name, format="wav")
        new_filename = os.path.splitext(audio_file.file.name)[0] + '.wav'
        with open(tmp_file.name, 'rb') as f:
            audio_file.file.save(new_filename, File(f), save=True)

def create_segment(input_waveform, input_sample_rate, row, audio_file): # The row parameter is a row from the pandas dataframe: caption_data.
    # device = torch.device("cuda" if torch.cuda.is_available() else "cpu") # Enable this line instead to experiment with using GPU for processing. Will also need to edit lines in the create_segment method
    # Move the input audio to GPU if available
    # input_waveform = input_waveform.to(device)

    # Convert start & end timestamps to frames based on sample rate. By this point, the timestamp should be in milliseconds (i.e., ':' separators not present)
    start_timestamp = int(row['start_time'])
    end_timestamp = int(row['end_time'])
    index_value = row['index']

    start_frame = int(start_timestamp / 1000 * input_sample_rate)
    end_frame = int(end_timestamp / 1000 * input_sample_rate)

    # Extract the specific audio segment
    # Assuming the input_audio is already loaded and in the correct format
    segment = input_waveform[:, start_frame:end_frame]

    # Optional: Additional audio processing can go here

    # Move audio back to CPU for saving files.
    # segment = segment.to("cpu") # Audio is transferred back to CPU here to save the clip files if it was being processed on GPU.
    buffer = BytesIO()
    torchaudio.save(buffer, segment, input_sample_rate, format="wav")
    buffer.seek(0)

    # TODO(absterr08): Confirm name convention
    file_name = f"{audio_file.original_filename}_Clip_{index_value}.wav"
    audio_clip_file = MediaFile.objects.create(
        owner=audio_file.owner,
        file_type='audio',
        original_filename=file_name
    )

    audio_clip_file.file.save(
        file_name,
        buffer,
        save=True
    )

    # return the full filepath that will be used in the AudioPath column
    return audio_clip_file.file.path

