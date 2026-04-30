from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from integration.google_oauth import get_oauth_credentials

def build_drive_service(credentials_file="credentials.json", token_file="token.json"):
    creds = get_oauth_credentials(credentials_file, token_file)
    return build("drive", "v3", credentials=creds)

def upload_to_drive(drive_service, file_path: str, folder_id: str | None = None):
    file_metadata = {"name": file_path.split("/")[-1]}
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaFileUpload(file_path, resumable=True)

    created = (
        drive_service.files()
        .create(body=file_metadata, media_body=media, fields="id, webViewLink")
        .execute()
    )
    return created["id"], created.get("webViewLink", "")
