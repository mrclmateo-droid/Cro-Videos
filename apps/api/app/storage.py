"""Acceso a S3/MinIO. Dos clientes: uno interno (red docker) y uno público (URLs firmadas para el navegador)."""
import time
from typing import BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from .config import get_settings

_s = get_settings()
BUCKET = _s.s3_bucket


def _client(endpoint: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=_s.s3_access_key,
        aws_secret_access_key=_s.s3_secret_key,
        region_name=_s.s3_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


_internal = _client(_s.s3_endpoint_internal)
_public = _client(_s.s3_endpoint_public)


def ensure_bucket(retries: int = 30, delay: float = 2.0) -> None:
    for attempt in range(retries):
        try:
            try:
                _internal.head_bucket(Bucket=BUCKET)
            except ClientError:
                _internal.create_bucket(Bucket=BUCKET)
            return
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(delay)


# --- multipart (subida directa desde el navegador) ---
def create_multipart(key: str, content_type: str) -> str:
    return _internal.create_multipart_upload(Bucket=BUCKET, Key=key, ContentType=content_type)["UploadId"]


def presign_part(key: str, upload_id: str, part_number: int, expires: int = 3600) -> str:
    return _public.generate_presigned_url(
        "upload_part",
        Params={"Bucket": BUCKET, "Key": key, "UploadId": upload_id, "PartNumber": part_number},
        ExpiresIn=expires,
    )


def complete_multipart(key: str, upload_id: str, parts: list[dict]) -> None:
    _internal.complete_multipart_upload(
        Bucket=BUCKET, Key=key, UploadId=upload_id, MultipartUpload={"Parts": parts}
    )


def abort_multipart(key: str, upload_id: str) -> None:
    try:
        _internal.abort_multipart_upload(Bucket=BUCKET, Key=key, UploadId=upload_id)
    except ClientError:
        pass


# --- objetos ---
def object_size(key: str) -> int | None:
    try:
        return int(_internal.head_object(Bucket=BUCKET, Key=key)["ContentLength"])
    except ClientError:
        return None


def upload_fileobj(fileobj: BinaryIO, key: str, content_type: str) -> None:
    _internal.upload_fileobj(fileobj, BUCKET, key, ExtraArgs={"ContentType": content_type})


def upload_file(path: str, key: str, content_type: str) -> None:
    _internal.upload_file(path, BUCKET, key, ExtraArgs={"ContentType": content_type})


def download_file(key: str, path: str) -> None:
    _internal.download_file(BUCKET, key, path)


def delete_object(key: str) -> None:
    _internal.delete_object(Bucket=BUCKET, Key=key)


# --- URLs firmadas ---
def presign_internal(key: str, expires: int = 6 * 3600) -> str:
    """Para que FFmpeg/ffprobe lean el archivo por HTTP dentro de la red, sin descargarlo entero."""
    return _internal.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": key}, ExpiresIn=expires)


def presign_download(key: str, expires: int = 900, filename: str | None = None) -> str:
    """Para el navegador del usuario (endpoint público)."""
    params = {"Bucket": BUCKET, "Key": key}
    if filename:
        params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
    return _public.generate_presigned_url("get_object", Params=params, ExpiresIn=expires)
