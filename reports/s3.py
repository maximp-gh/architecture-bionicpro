import aiobotocore.session
from botocore.exceptions import ClientError
from botocore.config import Config

class S3Client:
    async def __aenter__(self):
        session = aiobotocore.session.get_session()
        #config = Config(s3_addressing_style='path')

        config = Config(
            s3={'addressing_style': 'path'},  # ← В таком формате!
            signature_version='s3v4',
            parameter_validation=False
        )


        self.client = await session.create_client(
            's3',
            endpoint_url='http://minio:9000',
            aws_access_key_id='minio_user',
            aws_secret_access_key='minio_password',
            config=config).__aenter__()
        return self
    
    async def __aexit__(self, *args):
        await self.client.__aexit__(*args)

    async def CheckBucket (self, bucket_name = 'reports-bucket'):
        # 1. Проверяем существует ли бакет
        try:
            await self.client.head_bucket(Bucket=bucket_name)
            print(f"✅ Bucket '{bucket_name}' already exists")
            # Реально смотрим какие бакеты есть
            response = await self.client.list_buckets()
            print("📦 Real buckets in this MinIO instance:")
            for bucket in response.get('Buckets', []):
                print(f"  - {bucket['Name']}")
        except ClientError as e:
            print (e)
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # 2. Создаем бакет
                print(f"📦 Creating bucket '{bucket_name}'...")
                try:
                    await self.client.create_bucket(Bucket=bucket_name)
                    print(f"✅ Bucket '{bucket_name}' created successfully")
                except ClientError as create_error:
                    print(f"❌ Failed to create bucket: {create_error}")
                    exit(1)
            else:
                print(f"❌ Error checking bucket: {e}")
                exit(1)
    

    async def get_cdn_url(self, key: str) -> str:
        bucket_name = 'reports-bucket'
        await self.CheckBucket(bucket_name)

        try:
            await self.client.head_object(Bucket=bucket_name, Key=key)
            #Хранилище файлов - см. nginx
            return f"http://localhost:8090/reports/{key}"
        except:
            return None