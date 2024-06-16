#!/usr/bin/env python
# coding: utf-8
import pickle
import pandas as pd
import argparse
import logging
import boto3
from botocore.exceptions import ClientError
import os
import pyarrow as pa
import pyarrow.parquet as pq

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/app/personal-gcp.json'

with open('model.bin', 'rb') as f_in:
    dv, model = pickle.load(f_in)

categorical = ['PULocationID', 'DOLocationID']

def read_data(filename):
    df = pd.read_parquet(filename)
    
    df['duration'] = df.tpep_dropoff_datetime - df.tpep_pickup_datetime
    df['duration'] = df.duration.dt.total_seconds() / 60

    df = df[(df.duration >= 1) & (df.duration <= 60)].copy()

    df[categorical] = df[categorical].fillna(-1).astype('int').astype('str')
    
    return df

def main(year: str, month: str, dataset: str = "yellow"):
    year = int(year)
    month = int(month)
    url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/{dataset}_tripdata_{year:04d}-{month:02d}.parquet"
    print(url)
    df = read_data(url)

    dicts = df[categorical].to_dict(orient='records')
    X_val = dv.transform(dicts)
    y_pred = model.predict(X_val)

    # Desviacion Estandard
    print("STD = %.2f" % y_pred.std())
    print("MEAN = %.2f" % y_pred.mean())

    # Output
    output_file = f'{dataset}_tripdata_{year:04d}-{month:02d}_predicted.parquet'
    # RideID & PRedictionDuration
    df['ride_id'] = f'{year:04d}/{month:02d}_' + df.index.astype('str')
    df['predicted_duration'] = y_pred
    # Select 2 columns
    df_result = df[['ride_id', 'predicted_duration']]
    # Save output
    df_result.to_parquet(
        output_file,
        engine='pyarrow',
        compression=None,
        index=False
    )
    # Upload to AWS S3
    s3_client = boto3.client('s3')
    bucket_name = 'output_models'
    object_name=None
    try:
        response = s3_client.upload_file(output_file, bucket_name, object_name)
    except ClientError as e:
        logging.error(e)

    # GCS
    project_id = os.getenv('project_id')
    root_path = f'{bucket_name}'

    table = pa.Table.from_pandas(df_result)

    gcs = pa.fs.GcsFileSystem()

    pq.write_to_dataset(
        table,
        root_path=root_path,
        filesystem=gcs
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Score model")

    parser.add_argument('--year', required=True, default='2023', help='Año de los datos')
    parser.add_argument('--month', required=True, default='5', help='Mes de los datos')
    parser.add_argument('--dataset', required=True, default='yellow', help='Dataset de los taxis')

    args = parser.parse_args()
    year = args.year
    month = args.month
    dataset = args.dataset
    main(year, month, dataset)