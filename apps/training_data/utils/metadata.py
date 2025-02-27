
import os
import csv
import re
from io import StringIO, BytesIO
from ..models import MediaFile
import pandas as pd

def convert_subtitles_to_metadata(subtitle_file):
    """Convert subtitle file to Metadata CSV file"""
    try:
        metadata_content = get_metadata_content(subtitle_file)

        # Create Metadata CSV file from subtitle file
        metadata_file = MediaFile.objects.create(
            # client=subtitle_file.client,
            owner=subtitle_file.owner,
            file_type='csv',
            original_filename=f"{os.path.splitext(subtitle_file.original_filename)[0]}.csv"
        )
        metadata_file.file.save(
            metadata_file.original_filename,
            BytesIO(metadata_content.getvalue().encode()),
            save=True
        )

        # Clean and update metadata file
        cleaned_metadata = clean_csv_data(metadata_file)
        metadata_file.file.save(
            metadata_file.original_filename,
            BytesIO(cleaned_metadata.getvalue().encode()),
            save=True
        )

        return metadata_file

    except Exception as e:
        raise Exception(f"Error converting subtitles to CSV: {str(e)}")

def get_metadata_content(subtitle_file):
    # Read subtitle file
    subtitle_file.file.seek(0)
    content = subtitle_file.file.read().decode('utf-8')

    # Find [Events] section
    events_start = content.find('[Events]')
    if events_start == -1:
        raise ValueError("Invalid subtitle file format: [Events] section not found")

    # Extract events data
    events_data = content[events_start:].split('\n')

    # Parse header and data
    header = None
    rows = []
    for line in events_data:
        if line.startswith('Format:'):
            header = [col.strip() for col in line.replace('Format:', '').split(',')]
        elif line.startswith('Dialogue:'):
            row = line.replace('Dialogue:', '').split(',', len(header) - 1)
            rows.append(row)

    # Create CSV content
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(header)
    writer.writerows(rows)

    return output

'''
  The speaker name can either be in the Name column, Style column,
  or at the beginning of the caption text in brackets.
'''
def normalize_name_field(row):
    if pd.notna(row['Name']) and row['Name'].strip():
        return row['Name'].strip()

    if (pd.notna(row['Style']) and
        row['Style'].lower() != 'default' and
        row['Style'].strip()):
        return row['Style'].strip()

    if pd.notna(row['Text']):
        if match := re.match(r'\[([^\]]+)\]', row['Text']):
            return match.group(1).strip()

    return ''

def clean_csv_data(csv_file):
    """Clean up CSV data"""
    try:
        # Read CSV content
        csv_file.file.seek(0)  # Reset file pointer to start
        content = csv_file.file.read().decode('utf-8')

        # Parse CSV with specific headers
        expected_headers = ['Layer', 'Start', 'End', 'Style', 'Name', 'MarginL', 'MarginR', 'MarginV', 'Effect', 'Text']
        df = pd.read_csv(
            StringIO(content),
            encoding='utf-8',
            names=expected_headers if 'Layer' not in content.split('\n')[0] else None
        )

        # Clean text field
        if 'Text' in df.columns:
            df['Text'] = df['Text'].fillna('')  # Replace NaN with empty string
            df['Text'] = df['Text'].astype(str)  # Ensure text is string type
            df['Text'] = df['Text'].str.replace(r'\[.*?\]|\(.*?\)', '', regex=True)  # Remove brackets/parentheses
            df['Text'] = df['Text'].str.replace(r'^"?(\w+: )', '', regex=True)  # Remove speaker indicators
            df['Text'] = df['Text'].str.replace(r'\N', '')  # Remove line breaks
            df['Text'] = df['Text'].str.replace(r'♫', '')  # Remove music notes
            df['Text'] = df['Text'].str.strip()  # Remove leading/trailing whitespace

            # Remove empty rows
            df = df.dropna(subset=['Text'])
            df = df[df['Text'].str.strip() != '']
            df = df[~df['Text'].isin(['""', '" "', '"'])]

        df['speaker_name'] = df.apply(normalize_name_field, axis=1)

        df = df.rename(columns={
          'Start': 'start_time',
          'End': 'end_time',
          'Text': 'caption_text',
        })

        columns_to_keep = ['speaker_name', 'start_time', 'end_time', 'caption_text']
        df = df[columns_to_keep]

       # Save cleaned data
        output = StringIO()
        df.to_csv(output, index=False)
        return output

    except Exception as e:
        import traceback
        raise Exception(f"Error cleaning CSV data: {str(e)}\n{traceback.format_exc()}")
