import re
import io
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def extract_inline_data(message: str) -> tuple[str, pd.DataFrame | None, bool]:
    """
    Detects and extracts tabular data (Markdown or Pipe-separated) from a user message.
    Returns:
        clean_question (str): The user's prompt without the tabular data.
        dataframe (pd.DataFrame | None): The parsed tabular data.
        detected (bool): True if data was detected and parsed.
    """
    lines = message.split('\n')
    table_lines = []
    other_lines = []
    
    # We will collect contiguous blocks of lines containing '|'
    current_block = []
    blocks = []
    
    for line in lines:
        stripped = line.strip()
        # A very naive check: if it contains '|', we consider it part of a table candidate
        if '|' in stripped:
            current_block.append(stripped)
        else:
            if current_block:
                blocks.append(current_block)
                current_block = []
            other_lines.append(line)
            
    if current_block:
        blocks.append(current_block)
        
    if not blocks:
        return message, None, False
        
    # Find the largest block that looks like a table (at least 2 lines)
    best_block = max(blocks, key=len)
    
    if len(best_block) >= 2:
        try:
            clean_table_lines = []
            for tline in best_block:
                tline = tline.strip()
                if tline.startswith('|'):
                    tline = tline[1:]
                if tline.endswith('|'):
                    tline = tline[:-1]
                clean_table_lines.append(tline)
                
            csv_str = '\n'.join(clean_table_lines)
            
            # Use Pandas to parse the pipe-separated values
            df = pd.read_csv(io.StringIO(csv_str), sep='|', skipinitialspace=True)
            
            # Clean up column names
            df.columns = df.columns.str.strip()
            
            # Clean up string values and attempt numeric conversion
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].str.strip()
                    # Try to convert to numeric, ignore errors to keep as string if it fails.
                    # This ensures "$450,000" or " 120 " becomes a float/int so SQLite can SUM() it.
                    df[col] = pd.to_numeric(df[col].str.replace(r'[\$,]', '', regex=True), errors='ignore')
            
            # Filter out the Markdown separator row (e.g. ---|---|---)
            # If the first row is completely made of hyphens and colons
            if not df.empty:
                first_row = df.iloc[0].astype(str)
                if first_row.str.match(r'^[\-\s:]+$').all():
                    df = df.iloc[1:]
                    
            # Re-infer types since the separator might have forced everything to string
            df = df.convert_dtypes()
            
            clean_question = '\n'.join(other_lines).strip()
            
            logger.info("Extracted inline data with %d rows and %d columns", len(df), len(df.columns))
            return clean_question, df, True
            
        except Exception as e:
            logger.warning("Failed to parse detected inline data: %s", e)
            
    return message, None, False
