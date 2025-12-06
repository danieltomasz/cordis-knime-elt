# FILE: cordis_parser.py
import polars as pl
from lxml import etree
import os
import glob
import pyarrow as pa
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

def parse_single_xml(file_path: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Parses a single CORDIS XML file. Returns a tuple: (Project Dict, Participants List).
    """
    try:
        tree = etree.parse(file_path)
        root = tree.getroot()
        
        def get_text(elem, query):
            return elem.findtext(query) if elem is not None else None

        rcn_str = root.findtext('rcn')
        if not rcn_str:
            return None, []
        project_rcn = int(rcn_str)

        project = {
            'rcn': project_rcn,
            'acronym': get_text(root, 'acronym'),
            'title': get_text(root, 'title'),
            'start_date': get_text(root, 'startDate'),
            'end_date': get_text(root, 'endDate'),
            'total_cost': float(get_text(root, 'totalCost') or 0),
            'ec_max_contribution': float(get_text(root, 'ecMaxContribution') or 0),
            'objective': get_text(root, 'objective')
        }

        participants = []
        for org in root.findall(".//relations/associations/organization"):
            ec_contrib = org.get('ecContribution')
            participants.append({
                'project_rcn': project_rcn,
                'org_id': org.findtext('id'),
                'legal_name': org.findtext('legalName'),
                'country_code': org.findtext('address/country'),
                'role': org.get('type'),
                'ec_contribution': float(ec_contrib) if ec_contrib else 0.0
            })
            
        return project, participants
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None, []

def process_folder(folder_path: str, max_files: int = 0) -> Tuple[pl.DataFrame, pl.DataFrame]:
    """
    Orchestrator: Scans folder, loops files, returns Polars DataFrames.
    """
    abs_path = os.path.abspath(os.path.expanduser(folder_path))
    files = glob.glob(os.path.join(abs_path, "*.xml"))
    
    if max_files > 0 and files:
        files = files[:max_files]

    all_proj, all_part = [], []
    for f in files:
        p, parts = parse_single_xml(f)
        if p:
            all_proj.append(p)
            all_part.extend(parts)

    df_proj = pl.DataFrame(all_proj)
    df_part = pl.DataFrame(all_part)

    # Business Logic: Data Type Enforcement
    if not df_proj.is_empty():
        df_proj = df_proj.with_columns([
            pl.col("start_date").str.to_date("%Y-%m-%d", strict=False),
            pl.col("end_date").str.to_date("%Y-%m-%d", strict=False),
            pl.lit(datetime.now()).alias("last_updated")
        ])

    return df_proj, df_part

def convert_to_arrow(df: pl.DataFrame) -> pa.Table:
    """
    Converts Polars DF to PyArrow Table and fixes LargeString types.
    Returns a raw PyArrow table (KNIME-agnostic).
    """
    if df.is_empty():
        return df.to_arrow()
        
    arrow_table = df.to_arrow()
    new_schema = []
    for field in arrow_table.schema:
        if field.type == pa.large_string():
            new_schema.append(field.with_type(pa.string()))
        else:
            new_schema.append(field)
    return arrow_table.cast(pa.schema(new_schema))