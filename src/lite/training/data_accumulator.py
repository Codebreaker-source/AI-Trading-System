"""
Live Data Accumulator - Collects real-time market data from Azure File Share
Reads from: csv-exchange/market_data/latest_features.csv
Writes to: csv-exchange/training_data/accumulated_features.csv
"""

import os
import time
import logging
import pandas as pd
from datetime import datetime
from azure.storage.fileshare import ShareFileClient, ShareDirectoryClient
from io import BytesIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DataAccumulator:
    def __init__(self):
        # Azure configuration
        self.connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        if not self.connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable not set")
        
        self.share_name = "csv-exchange"
        self.input_path = "market_data/latest_features.csv"
        self.output_path = "training_data/accumulated_features.csv"
        
        # Collection settings
        self.collection_interval = 2  # seconds
        self.target_samples = 50000
        
        # Statistics
        self.total_samples = 0
        self.collection_start_time = datetime.now()
        
        # Required columns for validation
        self.required_columns = ['Symbol', 'Timestamp', 'Open', 'High', 'Low', 'Close']
        
        logging.info("=" * 60)
        logging.info("LIVE DATA ACCUMULATOR - Starting")
        logging.info("=" * 60)
        logging.info(f"Target samples: {self.target_samples:,}")
        logging.info(f"Collection interval: {self.collection_interval}s")
        logging.info("")
    
    def ensure_directory_exists(self):
        """Create training_data directory if it doesn't exist"""
        try:
            directory_client = ShareDirectoryClient.from_connection_string(
                self.connection_string,
                self.share_name,
                "training_data"
            )
            
            # Try to get directory properties
            try:
                directory_client.get_directory_properties()
                logging.info("training_data directory already exists")
            except Exception:
                # Directory doesn't exist, create it
                directory_client.create_directory()
                logging.info("Created training_data directory in Azure")
        except Exception as e:
            logging.error(f"Error ensuring directory exists: {e}")
            raise
    
    def read_from_azure(self, file_path):
        """Read CSV file from Azure File Share"""
        try:
            file_client = ShareFileClient.from_connection_string(
                self.connection_string,
                self.share_name,
                file_path
            )
            
            # Download file content
            download = file_client.download_file()
            content = download.readall()
            
            # Parse CSV
            df = pd.read_csv(BytesIO(content))
            return df
            
        except Exception as e:
            logging.error(f"Error reading from Azure ({file_path}): {e}")
            return None
    
    def write_to_azure(self, df, file_path):
        """Write CSV file to Azure File Share"""
        try:
            file_client = ShareFileClient.from_connection_string(
                self.connection_string,
                self.share_name,
                file_path
            )
            
            # Convert DataFrame to CSV bytes
            csv_buffer = BytesIO()
            df.to_csv(csv_buffer, index=False)
            csv_bytes = csv_buffer.getvalue()
            
            # Create or overwrite file
            file_client.create_file(len(csv_bytes))
            file_client.upload_range(csv_bytes, 0, len(csv_bytes))
            
            return True
            
        except Exception as e:
            logging.error(f"Error writing to Azure ({file_path}): {e}")
            return False
    
    def validate_data(self, df):
        """Validate that data has required columns"""
        if df is None or df.empty:
            return False
        
        missing_columns = [col for col in self.required_columns if col not in df.columns]
        if missing_columns:
            logging.error(f"Missing required columns: {missing_columns}")
            return False
        
        return True
    
    def append_to_accumulated(self, new_data):
        """Append new data to accumulated training data"""
        try:
            # Try to read existing accumulated data
            accumulated_df = self.read_from_azure(self.output_path)
            
            if accumulated_df is None:
                # File doesn't exist, create new
                accumulated_df = new_data
                logging.info("Creating new accumulated data file")
            else:
                # Append new data
                accumulated_df = pd.concat([accumulated_df, new_data], ignore_index=True)
            
            # Write back to Azure
            if self.write_to_azure(accumulated_df, self.output_path):
                self.total_samples = len(accumulated_df)
                return True
            else:
                return False
                
        except Exception as e:
            logging.error(f"Error appending to accumulated data: {e}")
            return False
    
    def print_progress(self):
        """Print collection progress statistics"""
        elapsed_time = (datetime.now() - self.collection_start_time).total_seconds()
        samples_per_hour = (self.total_samples / elapsed_time * 3600) if elapsed_time > 0 else 0
        progress_percent = (self.total_samples / self.target_samples * 100) if self.target_samples > 0 else 0
        
        remaining_samples = max(0, self.target_samples - self.total_samples)
        eta_hours = (remaining_samples / samples_per_hour) if samples_per_hour > 0 else 0
        
        logging.info("")
        logging.info("=" * 60)
        logging.info(f"Total samples: {self.total_samples:,} / {self.target_samples:,} ({progress_percent:.1f}%)")
        logging.info(f"Collection rate: {samples_per_hour:.0f} samples/hour")
        logging.info(f"Estimated time remaining: {eta_hours:.1f} hours")
        logging.info("=" * 60)
        logging.info("")
    
    def collect_data(self):
        """Single iteration of data collection"""
        # Read latest features from Azure
        latest_df = self.read_from_azure(self.input_path)
        
        if latest_df is None:
            logging.warning("Could not read latest features file")
            return False
        
        # Validate data
        if not self.validate_data(latest_df):
            logging.warning("Data validation failed")
            return False
        
        # Check file age
        try:
            file_client = ShareFileClient.from_connection_string(
                self.connection_string,
                self.share_name,
                self.input_path
            )
            properties = file_client.get_file_properties()
            file_age = datetime.now(properties.last_modified.tzinfo) - properties.last_modified
            
            if file_age.total_seconds() > 10:
                logging.warning(f"File is {file_age.total_seconds():.0f} seconds old - may not be updating")
        except Exception as e:
            logging.warning(f"Could not check file age: {e}")
        
        # Append to accumulated data
        if self.append_to_accumulated(latest_df):
            logging.info(f"Collected {len(latest_df)} new samples")
            logging.info(f"Accumulated data updated: {self.total_samples:,} total samples")
            return True
        else:
            logging.error("Failed to append data")
            return False
    
    def run(self):
        """Main collection loop"""
        # Ensure directory exists before starting
        self.ensure_directory_exists()
        
        # Check initial accumulated data count
        accumulated_df = self.read_from_azure(self.output_path)
        if accumulated_df is not None:
            self.total_samples = len(accumulated_df)
            logging.info(f"Resuming collection from {self.total_samples:,} existing samples")
        else:
            logging.info("Starting new data collection")
        
        logging.info("")
        logging.info("Starting continuous data collection...")
        logging.info("Press Ctrl+C to stop")
        logging.info("")
        
        iteration_count = 0
        
        try:
            while True:
                # Collect data
                self.collect_data()
                
                # Print progress every 50 iterations (100 seconds)
                iteration_count += 1
                if iteration_count % 50 == 0:
                    self.print_progress()
                
                # Wait before next collection
                time.sleep(self.collection_interval)
                
        except KeyboardInterrupt:
            logging.info("")
            logging.info("Collection stopped by user")
            self.print_progress()
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            raise

def main():
    """Main entry point"""
    try:
        accumulator = DataAccumulator()
        accumulator.run()
        return 0
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())