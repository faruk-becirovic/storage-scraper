import csv
import json
from pathlib import Path
from typing import List
import pandas as pd
from loguru import logger
from .models import ScrapingResult, StorageUnit

class DataExporter:
    """Handles exporting scraped data to various formats."""

    @staticmethod
    def export_to_csv(results: List[ScrapingResult], output_path: str):
        """Export results to CSV file."""

        logger.info(f"Exporting data to {output_path}")

        # Flatten all units from all results
        all_units = []
        for result in results:
            if result.success:
                all_units.extend(result.units)

        if not all_units:
            logger.warning("No data to export")
            # Create empty CSV with headers
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['url', 'size', 'price', 'raw_size', 'raw_price'])
            return

        try:
            # Convert to pandas DataFrame for easy CSV export
            data = []
            for unit in all_units:
                data.append({
                    'url': unit.url,
                    'size': unit.size,
                    'price': unit.price,
                    'raw_size': unit.raw_size,
                    'raw_price': unit.raw_price
                })

            df = pd.DataFrame(data)
            df.to_csv(output_path, index=False, encoding='utf-8')

            logger.success(f"Exported {len(all_units)} units to {output_path}")

        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            raise

    @staticmethod
    def export_to_json(results: List[ScrapingResult], output_path: str):
        """Export results to JSON file."""

        logger.info(f"Exporting data to {output_path}")

        try:
            # Convert results to JSON-serializable format
            json_data = []
            for result in results:
                result_dict = {
                    'url': result.url,
                    'success': result.success,
                    'error': result.error,
                    'units': []
                }

                for unit in result.units:
                    result_dict['units'].append({
                        'url': unit.url,
                        'size': unit.size,
                        'price': unit.price,
                        'raw_size': unit.raw_size,
                        'raw_price': unit.raw_price
                    })

                json_data.append(result_dict)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            total_units = sum(len(r.units) for r in results if r.success)
            logger.success(f"Exported {total_units} units to {output_path}")

        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            raise
