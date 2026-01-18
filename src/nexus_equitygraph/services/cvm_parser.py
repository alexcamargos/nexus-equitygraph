"""Module for parsing CVM raw data (CSV/ZIP) into structured DataFrames."""

import io
import re
import zipfile
from typing import Dict, List, Optional

import pandas as pd
from bs4 import BeautifulSoup
from loguru import logger


# Regular expressions for finding ITR ZIP years.
RE_ITR_ZIP_YEAR = re.compile(r"itr_cia_aberta_(\d{4})\.zip")


def _read_csv_robust(file_handle) -> pd.DataFrame:
    """Reads CSV handling encoding issues.

    Args:
        file_handle: File-like object to read CSV from.
    Returns:
        pd.DataFrame: Parsed DataFrame.

    Raises:
        UnicodeDecodeError: If both encoding attempts fail.
    """

    try:
        return pd.read_csv(
            file_handle,
            sep=";",
            encoding="ISO-8859-1",
            dtype=str,
        )
    except UnicodeDecodeError:
        file_handle.seek(0)
        return pd.read_csv(file_handle, sep=";", encoding="latin1", dtype=str)


def _filter_company_data(
    df: pd.DataFrame,
    cvm_code: str,
    target_cnpj: Optional[str],
    filename: str,
    source_tag: str,
) -> pd.DataFrame:
    """Filters the DataFrame for the specific company.

    Args:
        df (pd.DataFrame): The DataFrame to filter.
        cvm_code (str): The CVM code of the company.
        target_cnpj (Optional[str]): The CNPJ of the company.
        filename (str): The name of the file being processed.
        source_tag (str): Tag indicating the source type (e.g., 'ITR', 'DFP').

    Returns:
        pd.DataFrame: Filtered DataFrame.
    """

    if "CD_CVM" in df.columns:
        try:
            target_cvm = str(int(cvm_code))
            # Creates a temporary CVM column for robust comparison.
            temp_cvm = (
                pd.to_numeric(df["CD_CVM"], errors="coerce")
                .fillna(0)
                .astype(int)
                .astype(str)
            )
            filtered = df[temp_cvm == target_cvm].copy()
            if not filtered.empty:
                return filtered
        except (ValueError, TypeError):
            pass

    if "CNPJ_CIA" in df.columns and target_cnpj:
        filtered = df[df["CNPJ_CIA"] == target_cnpj].copy()
        if not filtered.empty:
            return filtered

    logger.warning(
        f"Could not filter company in {filename} ({source_tag}). Missing or non-matching ID columns."
    )

    return pd.DataFrame()


def _process_numeric_columns(df: pd.DataFrame, filename: str) -> None:
    """Normalizes numeric columns and handles currency scaling.

    Args:
        df (pd.DataFrame): The DataFrame to process.
        filename (str): The name of the file being processed.
    """

    if "VL_CONTA" in df.columns:
        try:
            val_series = df["VL_CONTA"].astype(str)
            # Heuristic: if there's a comma anywhere, it's likely Brazilian format.
            if val_series.str.contains(",").any():
                df["VL_CONTA"] = pd.to_numeric(
                    val_series.str.replace(".", "", regex=False).str.replace(
                        ",", ".", regex=False
                    ),
                    errors="coerce",
                )
            else:
                df["VL_CONTA"] = pd.to_numeric(val_series, errors="coerce")
        except (ValueError, TypeError) as error:
            logger.error(f"Error processing numeric values in {filename}: {error}")

    if "ESCALA_MOEDA" in df.columns and "VL_CONTA" in df.columns:
        try:
            mask_mil = df["ESCALA_MOEDA"].astype(str).str.upper().str.strip() == "MIL"
            if mask_mil.any():
                df.loc[mask_mil, "VL_CONTA"] *= 1_000
        except (ValueError, TypeError) as error:
            logger.error(f"Error scaling currency values in {filename}: {error}")


def parse_cadastral_csv(content: bytes | None) -> pd.DataFrame:
    """Parses the cadastral CSV file.

    Args:
        content (bytes | None): Raw bytes of the cadastral CSV file.
    Returns:
        pd.DataFrame: Parsed DataFrame.
    """

    if not content:
        logger.warning("Empty content received for cadastral CSV.")
        return pd.DataFrame()

    # Created in-memory buffer with error handling.
    try:
        buffer = io.BytesIO(content)
    except TypeError:
        logger.opt(lazy=True).error(
            "Invalid content type for cadastral CSV: {type_content}. Expected bytes.",
            type_content=lambda: type(content),
        )
        raise
    except MemoryError:
        logger.critical("Insufficient memory to create buffer for cadastral CSV.")
        raise

    # Parse CSV with error handling.
    try:
        return pd.read_csv(buffer, sep=";", encoding="ISO-8859-1", dtype=str)
    except pd.errors.EmptyDataError:
        logger.warning("Cadastral CSV is valid but empty.")
        return pd.DataFrame()
    except pd.errors.ParserError as parser_error:
        logger.error(f"Parser error in cadastral CSV: {parser_error}")
        raise parser_error
    except Exception as error:
        logger.error(f"Unexpected error parsing cadastral CSV: {error}")
        raise


def parse_report_zip(
    content: bytes,
    cvm_code: str,
    target_cnpj: Optional[str],
    year: int,
    report_types: List[str],
    *,
    file_prefix: str,
    source_tag: str,
    consolidated: bool,
) -> Dict[str, pd.DataFrame]:
    """Parses a ZIP file containing ITR or DFP reports.

    Args:
        content (bytes): Raw bytes of the ZIP file.
        cvm_code (str): The CVM code of the company.
        target_cnpj (Optional[str]): The CNPJ of the company.
        year (int): The reporting year.
        report_types (List[str]): List of report types to extract.
        file_prefix (str): Prefix for the filenames in the ZIP.
        source_tag (str): Tag indicating the source type (e.g., 'ITR', 'DFP').
        consolidated (bool): Whether to look for consolidated reports.

    Returns:
        Dict[str, pd.DataFrame]: Dictionary mapping report types to DataFrames.

    Raises:
        zipfile.BadZipFile: If the ZIP file is corrupted.
        Exception: For other unexpected errors during parsing.
    """

    results = {}
    suffix = "con" if consolidated else "ind"

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            all_files = z.namelist()

            for r_type in report_types:
                # Determine expected filename pattern
                if r_type in ["composicao_capital", "parecer"]:
                    expected_pattern = f"{file_prefix}_{r_type}_{year}.csv".lower()
                else:
                    expected_pattern = (
                        f"{file_prefix}_{r_type}_{suffix}_{year}.csv".lower()
                    )

                found_file = next(
                    (f for f in all_files if f.lower() == expected_pattern), None
                )

                if not found_file:
                    continue

                with z.open(found_file) as csv_file:
                    df = _read_csv_robust(csv_file)

                    # Filter by Company
                    company_df = _filter_company_data(
                        df, cvm_code, target_cnpj, found_file, source_tag
                    )

                    if company_df.empty:
                        continue

                    # Clean Numeric Data
                    _process_numeric_columns(company_df, found_file)

                    company_df["SOURCE_TYPE"] = source_tag
                    results[r_type] = company_df

        return results

    except zipfile.BadZipFile:
        logger.error(f"Corrupted ZIP file for {source_tag} {year}")
        return {}
    except Exception as error:
        logger.error(f"Error parsing {source_tag} {year}: {error}")
        raise


def extract_years_from_html(content: bytes) -> List[int]:
    """Extracts available years for ITR reports from HTML content.

    Args:
        content (bytes): HTML content from CVM portal.

    Returns:
        List[int]: Sorted list of years found.
    """

    soup = BeautifulSoup(content, "html.parser")
    years = set()

    for link in soup.find_all("a"):
        href = link.get("href")
        # Check if href is a string before processing.
        if isinstance(href, str):
            match = RE_ITR_ZIP_YEAR.search(href)
            if match:
                years.add(int(match.group(1)))

    return sorted(list(years), reverse=True)


def append_report_data(
    consolidated: Dict[str, pd.DataFrame],
    new_data: Dict[str, pd.DataFrame],
) -> None:
    """Helper to concatenate new report data into the consolidated structure.

    Args:
        consolidated (Dict[str, pd.DataFrame]): Existing consolidated data.
        new_data (Dict[str, pd.DataFrame]): New data to append.
    """

    for report_type, df in new_data.items():
        if report_type in consolidated and not df.empty:
            consolidated[report_type] = pd.concat(
                [consolidated[report_type], df], ignore_index=True
            )
