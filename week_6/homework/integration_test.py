import pandas as pd
from datetime import datetime
from batch import get_input_path, get_output_path, read_data
import os

def dt(hour, minute, second=0):
    return datetime(2023, 1, 1, hour, minute, second)

data = [
    (None, None, dt(1, 1), dt(1, 10)),
    (1, 1, dt(1, 2), dt(1, 10)),
    (1, None, dt(1, 2, 0), dt(1, 2, 59)),
    (3, 4, dt(1, 2, 0), dt(2, 2, 1)),
]

columns = ['PULocationID', 'DOLocationID', 'tpep_pickup_datetime', 'tpep_dropoff_datetime']
df = pd.DataFrame(data, columns=columns)

categorical = ['PULocationID', 'DOLocationID']

year = 2023
month = 1
input_file = get_input_path(year, month)

S3_ENDPOINT_URL = os.getenv('S3_ENDPOINT_URL')

options = None

if S3_ENDPOINT_URL is not None:
    options = {
        'client_kwargs': {
            'endpoint_url': S3_ENDPOINT_URL
        }
    }
print(options)

df.to_parquet(
    input_file,
    engine='pyarrow',
    compression=None,
    index=False,
    storage_options=options
)

os.system('python batch.py 2023 1')

output_file = get_output_path(year, month)
df_output = read_data(output_file)

# calculate total duration
total_duration_actual= df_output['predicted_duration'].sum()
print(f"predicted duration total: {total_duration_actual:.2f}")