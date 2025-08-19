import json
import boto3
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """
    AWS Lambda handler for BLS data ingestion
    """
    try:
        logger.info("Starting BLS data ingestion process")
        
        # Configuration
        bucket_name = "dataquest-gov-bls-timeseries"
        api_key = "5ee32fa6e7da4ce490d27e198e912f08"
        
        # BLS series to collect
        series_list = get_bls_series_list()
        
        # Process each series
        results = []
        for series_id in series_list:
            try:
                logger.info(f"Processing series: {series_id}")
                
                # Fetch data from BLS API
                data = fetch_bls_data(series_id, api_key)
                
                if data:
                    # Store in S3
                    s3_key = f"bls-data/{series_id}/{datetime.now().strftime('%Y-%m-%d')}.json"
                    store_data_in_s3(bucket_name, s3_key, data)
                    results.append({
                        'series_id': series_id,
                        'status': 'success',
                        'records': len(data.get('Results', {}).get('series', [{}])[0].get('data', []))
                    })
                    logger.info(f"Successfully processed {series_id}")
                else:
                    results.append({
                        'series_id': series_id,
                        'status': 'no_data',
                        'error': 'No data returned from API'
                    })
                    
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing series {series_id}: {str(e)}")
                results.append({
                    'series_id': series_id,
                    'status': 'error',
                    'error': str(e)
                })
        
        # Summary
        successful = len([r for r in results if r['status'] == 'success'])
        total = len(results)
        
        logger.info(f"Processing complete: {successful}/{total} series successful")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'BLS data ingestion completed: {successful}/{total} successful',
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

def get_bls_series_list() -> List[str]:
    """
    Return list of BLS series IDs to collect
    Comprehensive coverage of key economic indicators
    """
    return [
        # Employment & Unemployment (Current Population Survey)
        'LNS14000000',  # Unemployment Rate
        'LNS12000000',  # Employment Level
        'LNS11000000',  # Labor Force Level
        'LNS13000000',  # Unemployed Level
        'LNS12300000',  # Employment-Population Ratio
        'LNS11300000',  # Labor Force Participation Rate
        
        # Nonfarm Payrolls (Current Employment Statistics)
        'CES0000000001',  # Total Nonfarm Employment
        'CES0500000001',  # Total Private Employment
        'CES9000000001',  # Government Employment
        'CES0600000001',  # Goods-Producing Employment
        'CES0800000001',  # Service-Providing Employment
        
        # Manufacturing Employment
        'CES3000000001',  # Total Manufacturing
        'CES3100000001',  # Durable Goods Manufacturing
        'CES3200000001',  # Nondurable Goods Manufacturing
        
        # Service Sector Employment
        'CES4000000001',  # Trade, Transportation & Utilities
        'CES4142000001',  # Retail Trade
        'CES5000000001',  # Information
        'CES5500000001',  # Financial Activities
        'CES6000000001',  # Professional & Business Services
        'CES6500000001',  # Education & Health Services
        'CES7000000001',  # Leisure & Hospitality
        
        # Hours & Earnings
        'CES0500000002',  # Average Weekly Hours - Private
        'CES0500000003',  # Average Hourly Earnings - Private
        'CES0500000011',  # Average Weekly Earnings - Private
        'CES3000000002',  # Average Weekly Hours - Manufacturing
        'CES3000000003',  # Average Hourly Earnings - Manufacturing
        
        # Consumer Price Index (CPI)
        'CUUR0000SA0',    # CPI-U All Items
        'CUUR0000SA0L1E', # CPI-U All Items Less Food & Energy (Core CPI)
        'CUUR0000SAF1',   # CPI-U Food
        'CUUR0000SAH1',   # CPI-U Housing
        'CUUR0000SETB01', # CPI-U Gasoline
        'CUUR0000SAM',    # CPI-U Medical Care
        'CUUR0000SAE1',   # CPI-U Energy
        'CUUR0000SAT1',   # CPI-U Transportation
        
        # Producer Price Index (PPI)
        'WPUFD49207',     # PPI Final Demand
        'WPUFD49104',     # PPI Final Demand Less Food & Energy
        'WPSSOP61',       # PPI Services
        'WPU101',         # PPI Crude Materials
        
        # Productivity & Costs
        'PRS85006092',    # Nonfarm Business Labor Productivity
        'PRS85006112',    # Nonfarm Business Unit Labor Costs
        'PRS85006152',    # Nonfarm Business Real Hourly Compensation
        'PRS85006062',    # Nonfarm Business Output
        'PRS85006032',    # Nonfarm Business Hours
        
        # Job Openings & Labor Turnover (JOLTS)
        'JTS1000JOL',     # Total Job Openings
        'JTS1000HIL',     # Total Hires
        'JTS1000TSL',     # Total Separations
        'JTS1000QUL',     # Total Quits
        'JTS1000LDL',     # Total Layoffs & Discharges
        
        # Regional Employment
        'LAUMT064974000000003',  # California Unemployment Rate
        'LAUMT121470000000003',  # Florida Unemployment Rate
        'LAUMT173574000000003',  # Illinois Unemployment Rate
        'LAUMT362034000000003',  # New York Unemployment Rate
        'LAUMT484274000000003',  # Texas Unemployment Rate
        
        # Industry-Specific Data
        'CES1021000001',  # Mining & Logging Employment
        'CES2000000001',  # Construction Employment
        'CES4300000001',  # Transportation & Warehousing
        'CES5552000001',  # Finance & Insurance
        'CES6054000001',  # Computer Systems Design
        'CES6562000001',  # Healthcare
        'CES7072000001',  # Accommodation & Food Services
        
        # Seasonal Adjustments & Demographics
        'LNS14000003',    # Unemployment Rate - White
        'LNS14000006',    # Unemployment Rate - Black or African American
        'LNS14000009',    # Unemployment Rate - Hispanic or Latino
        'LNS14000012',    # Unemployment Rate - Asian
        'LNS14000024',    # Unemployment Rate - 16-19 years
        'LNS14000025',    # Unemployment Rate - 20-24 years
        'LNS14000089',    # Unemployment Rate - 25+ years, Bachelor's degree+
        
        # Additional Economic Indicators
        'CUUS0000SA0',    # CPI-U All Urban Consumers (Alternative)
        'PRS88003092',    # Manufacturing Labor Productivity
        'JTS3000HIL',     # Manufacturing Hires
        'CES0500000007',  # Average Weekly Hours - Production Workers
    ]

def fetch_bls_data(series_id: str, api_key: str, start_year: int = None, end_year: int = None) -> Dict[str, Any]:
    """
    Fetch data from BLS API for a specific series
    """
    if start_year is None:
        start_year = (datetime.now() - timedelta(days=365*2)).year
    if end_year is None:
        end_year = datetime.now().year
    
    url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    
    payload = {
        'seriesid': [series_id],
        'startyear': str(start_year),
        'endyear': str(end_year),
        'registrationkey': api_key
    }
    
    headers = {'Content-type': 'application/json'}
    
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') == 'REQUEST_SUCCEEDED':
            logger.info(f"Successfully fetched data for {series_id}")
            return data
        else:
            logger.warning(f"BLS API returned status: {data.get('status')} for {series_id}")
            logger.warning(f"Messages: {data.get('message', [])}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request failed for {series_id}: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for {series_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching {series_id}: {str(e)}")
        return None

def store_data_in_s3(bucket_name: str, key: str, data: Dict[str, Any]) -> bool:
    """
    Store data in S3 bucket
    """
    try:
        # Add metadata
        enhanced_data = {
            'ingestion_timestamp': datetime.now().isoformat(),
            'source': 'BLS_API',
            'data': data
        }
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=json.dumps(enhanced_data, indent=2),
            ContentType='application/json'
        )
        
        logger.info(f"Data stored successfully: s3://{bucket_name}/{key}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store data in S3: {str(e)}")
        return False
